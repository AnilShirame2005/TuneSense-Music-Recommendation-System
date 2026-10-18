

import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load .env from the main project folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE, override=True)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def normalize_text(text: str) -> str:
    """Normalize text for song and artist matching."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def find_youtube_video(song_name: str, artist: str = ""):
    """Find a YouTube video matching the song title and artist."""

    if not YOUTUBE_API_KEY:
        raise RuntimeError(
            f"YouTube API key missing. Check this file: {ENV_FILE}"
        )

    if not song_name or not song_name.strip():
        raise ValueError("Song name cannot be empty.")

    query = f"{song_name} {artist} official audio"

    try:
        response = requests.get(
            YOUTUBE_SEARCH_URL,
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": 10,
                "key": YOUTUBE_API_KEY,
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not connect to YouTube: {exc}") from exc

    # Show useful error information without printing the API key.
    if response.status_code != 200:
        try:
            error_data = response.json().get("error", {})
            error_message = error_data.get("message", response.text)
            error_reason = (
                error_data.get("errors", [{}])[0].get("reason", "unknown")
            )
        except (ValueError, IndexError, AttributeError):
            error_message = response.text
            error_reason = "unknown"

        raise RuntimeError(
            f"YouTube API error {response.status_code} "
            f"({error_reason}): {error_message}"
        )

    items = response.json().get("items", [])

    wanted_song = normalize_text(song_name)
    wanted_artist = normalize_text(artist)

    song_words = set(wanted_song.split())
    artist_words = set(wanted_artist.split())

    for item in items:
        snippet = item.get("snippet", {})
        title = snippet.get("title", "")
        channel = snippet.get("channelTitle", "")

        normalized_title = normalize_text(title)
        normalized_channel = normalize_text(channel)
        title_words = set(normalized_title.split())

        # Require every song-name word to appear in the video title.
        if song_words and not song_words.issubset(title_words):
            continue

        # When an artist is supplied, require artist evidence
        # in the video title or channel name.
        if artist_words:
            artist_matches = (
                artist_words.issubset(title_words)
                or artist_words.issubset(set(normalized_channel.split()))
            )
            if not artist_matches:
                continue

        video_id = item.get("id", {}).get("videoId")
        if not video_id:
            continue

        return {
            "video_id": video_id,
            "title": title,
            "channel": channel,
            "embed_url": f"https://www.youtube.com/embed/{video_id}",
        }

    return None