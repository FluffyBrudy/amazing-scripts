import os
import json
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

CLIENT_SECRETS_FILE = "<credentials.json>" # find it on console.google.com
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

JSON_INPUT_FILE = "playlists.json" # playlist you wanna populate, look at bottom for schema


def get_authenticated_service():
    credentials = None

    if os.path.exists("token.json"):
        credentials = google.oauth2.credentials.Credentials.from_authorized_user_file(
            "token.json", SCOPES
        )

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(google.auth.transport.requests.Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES
            )
            credentials = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(credentials.to_json())

    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


def create_public_playlist(youtube, playlist_name, description=""):
    request_body = {
        "snippet": {"title": playlist_name, "description": description},
        "status": {"privacyStatus": "public"},
    }
    try:
        print(f"Attempting to create playlist: '{playlist_name}'")
        response = (
            youtube.playlists()
            .insert(part="snippet,status", body=request_body)
            .execute()
        )
        print(f"Playlist '{playlist_name}' created with ID: {response['id']}")
        return response["id"]
    except HttpError as e:
        print(
            f"An HTTP error {e.resp.status} occurred while creating playlist '{playlist_name}': {e.content}"
        )
        return None


def search_youtube_video(youtube, query):
    try:
        search_response = (
            youtube.search()
            .list(
                q=query,
                part="id,snippet",
                maxResults=1,
                type="video",
            )
            .execute()
        )

        for search_result in search_response.get("items", []):
            if search_result["id"]["kind"] == "youtube#video":
                print(
                    f"Found video '{search_result['snippet']['title']}' for query '{query}' with ID: {search_result['id']['videoId']}"
                )
                return search_result["id"]["videoId"]
        print(f"No video found for query: {query}")
        return None
    except HttpError as e:
        print(
            f"An HTTP error {e.resp.status} occurred during search for '{query}': {e.content}"
        )
        return None


def add_video_to_playlist(youtube, playlist_id, video_id):
    request_body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
        }
    }
    try:
        youtube.playlistItems().insert(part="snippet", body=request_body).execute()
        print(f"Added video '{video_id}' to playlist '{playlist_id}'")
    except HttpError as e:
        print(
            f"An HTTP error {e.resp.status} occurred when adding video '{video_id}' to playlist '{playlist_id}': {e.content}"
        )


if __name__ == "__main__":
    youtube = get_authenticated_service()

    try:
        with open(JSON_INPUT_FILE, "r") as f:
            json_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{JSON_INPUT_FILE}' was not found.")
        exit()
    except json.JSONDecodeError:
        print(
            f"Error: Could not decode JSON from '{JSON_INPUT_FILE}'. Please check the file format."
        )
        exit()

    for block_key, playlist_info in json_data.items():
        playlist_name = playlist_info.get("playlist_name")
        songs = playlist_info.get("songs", [])

        if not playlist_name:
            print(f"Skipping block '{block_key}': 'playlist_name' is missing.")
            continue
        if not songs:
            print(f"Skipping block '{block_key}': No songs found.")
            continue

        new_playlist_id = create_public_playlist(youtube, playlist_name)

        if new_playlist_id:
            for song in songs:
                artist = song.get("artist")
                title = song.get("title")

                if not artist or not title:
                    print(
                        f"Skipping song in playlist '{playlist_name}': Missing 'artist' or 'title'. Song data: {song}"
                    )
                    continue

                query = f"{artist} - {title}"
                video_id = search_youtube_video(youtube, query)
                if video_id:
                    add_video_to_playlist(youtube, new_playlist_id, video_id)
                else:
                    print(
                        f"Could not find a video for: {query} (Playlist: '{playlist_name}')"
                    )
        else:
            print(f"Failed to create playlist: {playlist_name}")

"""
SCHEMA:
SCHEMA:
{
  "B0": {
    "playlist_name": "string",
    "songs": [
      {
        "artist": "string",
        "title": "string"
      }
    ]
  },
  "B1": {
    "playlist_name": "string",
    "songs": [
      {
        "artist": "string",
        "title": "string"
      }
    ]
  }
}
"""
