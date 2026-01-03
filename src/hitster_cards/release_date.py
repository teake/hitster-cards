import re
import time
from collections.abc import Iterable
from dataclasses import asdict
from textwrap import dedent

import requests
from google import genai

from .models import Song, DatedSong
from .spotify import get_release_dates as get_release_dates_spotify


def date_song(song: Song) -> DatedSong | None:
    if not (release_date := get_release_date(song)):
        return None
    return DatedSong(**asdict(song), release_date=release_date)

def get_release_date(song: Song) -> str | None:
    if not (release_dates := list(get_release_dates_musicbrainz(song.isrc))):
        release_dates += list(get_release_dates_gemini(song.name, ", ".join(song.artists)))
    release_dates += list(get_release_dates_spotify(song.isrc))
    if release_dates:
        return sorted(release_dates)[0]
    else:
        return None

def get_release_dates_gemini(song_title, artist) -> Iterable[str]:
    client = genai.Client()
    query = f"""
        What is the original first release date of the song '{song_title}' by the artist {artist}? 
        Respond with only the year in the format YYYY. If you are not 100% sure, respond with 'I dont know'.
    """
    response = client.models.generate_content(model="gemini-3-flash-preview", contents=dedent(query).strip())
    if re.match(r"^\d{4}$", response.text):
        return [response.text]
    else:
        return []

def get_release_dates_musicbrainz(isrc: str, offset: int = 0, retries: int = 0) -> Iterable[str]:
    if retries > 3:
        return
    time.sleep(retries)
    user_agent = "hitster-cards/0.1.0 ( teake.nutma@gmail.com )"
    headers = {"User-Agent": user_agent}
    mb_url = f"https://musicbrainz.org/ws/2/recording/?query=isrc:{isrc}&fmt=json&limit=100&offset={100*offset}"
    try:
        r = requests.get(mb_url, headers=headers)
    except requests.exceptions.RequestException:
        yield from get_release_dates_musicbrainz(isrc, offset=offset, retries=retries + 1)
        return
    if r.status_code == 503:
        yield from get_release_dates_musicbrainz(isrc, offset=offset, retries=retries + 1)
        return
    if not r.ok:
        return
    data = r.json()
    recordings = data["recordings"]
    for recording in recordings:
        if "first-release-date" in recording:
            yield recording["first-release-date"]
    if data["count"] > (offset + 1) * 100:
        yield from get_release_dates_musicbrainz(isrc, offset=offset + 1, retries=0)
