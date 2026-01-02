import calendar
import re
import time
from dataclasses import asdict
from textwrap import dedent

import requests
from google import genai

from .models import Song, DatedSong


def date_song(song: Song) -> DatedSong | None:
    release_date = get_release_date(song)
    if not release_date:
        return None
    year, month, day = resolve_date_parts(release_date)
    return DatedSong(
        **asdict(song),
        release_date=release_date,
        year=year,
        month=month,
        day=day
    )

def resolve_date_parts(date_str: str) -> tuple[str, str, str]:
    date_parts = date_str.split("-")
    year, month, day = date_parts + [""] * (3 - len(date_parts))
    day = f"{int(day)}." if day else ""
    month = calendar.month_name[int(month)] if month else ""
    return year, month, day

def get_release_date(song: Song) -> str | None:
    if release_date := get_release_date_musicbrainz(song.isrc):
        return release_date
    else:
        return get_release_date_gemini(song.name, ", ".join(song.artists))

def get_release_date_gemini(song_title, artist) -> str | None:
    client = genai.Client()
    query = f"""
        What is the original first release date of the song '{song_title}' by the artist {artist}? 
        Respond with only the year in the format YYYY. If you are not 100% sure, respond with 'I dont know'.
    """
    response = client.models.generate_content(model="gemini-2.5-flash", contents=dedent(query).strip())
    if re.match(r"^\d{4}$", response.text):
        return response.text
    else:
        return None

def get_release_date_musicbrainz(isrc: str, retries=0) -> str | None:
    user_agent = "hitster-cards/0.1.0"
    headers = {"User-Agent": user_agent}
    mb_url = f"https://musicbrainz.org/ws/2/recording/?query=isrc:{isrc}&fmt=json&limit=50"
    failed = False
    try:
        r = requests.get(mb_url, headers=headers)
    except requests.exceptions.RequestException:
        failed = True
    if failed or r.status_code == 503:
        if retries < 3:
            time.sleep(1 + retries)
            return get_release_date_musicbrainz(isrc, retries=retries + 1)
        else:
            return None
    if not r.ok:
        return None
    recordings = r.json()["recordings"]
    first_release_dates = [r["first-release-date"] for r in recordings if "first-release-date" in r]
    if first_release_dates:
        return list(sorted(first_release_dates))[0]
    return None
