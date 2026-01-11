import json
import re
import time
from collections.abc import Iterable
from dataclasses import asdict

import requests
from google import genai

from .models import Song, DatedSong
from .spotify import get_release_dates as get_release_dates_spotify


def date_song(song: Song) -> DatedSong | None:
    if not (release_date := get_release_date(song)):
        return None
    return DatedSong(**asdict(song), release_date=release_date)

def get_release_date(song: Song) -> str | None:
    release_dates = list(get_release_dates_musicbrainz(song.isrc))
    release_dates += list(get_release_dates_spotify(song.isrc))
    if release_dates:
        return sorted(release_dates)[0]
    else:
        return None


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


def correct_release_dates_gemini(songs: Iterable[DatedSong]) -> Iterable[DatedSong]:
    songs = [DatedSong(**asdict(song)) for song in songs]
    client = genai.Client()
    payload = [
        {
            "artists": song.artists,
            "name": song.name,
            "release_date": song.release_date[:4]
        }
        for song in songs
    ]
    query = f"""
        Check if the original release dates of the following songs are correct. 
        Return only those songs if whose release date is incorrect, and only the year,
        not the full date. Return in JSON and no other text, and omit the triple Markdown quotes.
        If you are unsure about a song, skip it.
        ```
        {json.dumps(payload, indent=2)}
        ```
    """
    response = client.models.generate_content(model="gemini-3-flash-preview", contents=query.strip())
    try:
        response_data = json.loads(response.text)
    except json.decoder.JSONDecodeError:
        return
    if not isinstance(response_data, list):
        return
    for response_song in response_data:
        if not isinstance(response_song, dict):
            continue
        if not "artists" in response_song or not "name" in response_song or not "release_date" in response_song:
            continue
        if not re.match(r"^\d{4}$", response_song["release_date"]):
            continue
        for song in songs:
            if song.name == response_song["name"] and song.artists == response_song["artists"]:
                song.release_date = response_song["release_date"]
                yield song


def correct_release_dates(songs: Iterable[DatedSong], corrections: Iterable[DatedSong]) -> Iterable[DatedSong]:
    for song in songs:
        to_yield = song
        for corrected_song in corrections:
            if song.name == corrected_song.name and song.artists == corrected_song.artists:
                to_yield = corrected_song
                break
        yield to_yield

