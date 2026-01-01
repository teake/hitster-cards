import calendar
import datetime
import locale
import logging
import os
from collections import Counter
from xml.etree import ElementTree

import matplotlib.pyplot as plt
import qrcode
import qrcode.image.svg
import spotipy
from matplotlib.backends.backend_pdf import PdfPages
from spotipy import SpotifyClientCredentials


logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


def get_env_var(key):
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Environment variable {key} is required but not set.")
    return value


def resolve_date(date_str: str, month_lang=None, no_day=False) -> tuple[str, str, str]:
    date_parts = date_str.split("-")[::-1]
    parts = [""] * (3 - len(date_parts)) + date_parts

    day = "" if no_day else (f"{int(parts[0])}." if parts[0] else "")
    if parts[1]:
        if month_lang == "de":
            try:
                locale.setlocale(locale.LC_TIME, "de_DE.UTF-8")
            except locale.Error:
                pass
        elif month_lang == "en":
            try:
                locale.setlocale(locale.LC_TIME, "en_US.UTF-8")
            except locale.Error:
                pass
        month = calendar.month_name[int(parts[1])]
    else:
        month = ""
    year = parts[2]

    return day, month, year


def get_playlist_songs(playlist_id, verbose=False, month_lang=None, no_day=False, added_after=None) -> list[dict]:

    sp = spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=get_env_var("CLIENT_ID"),
            client_secret=get_env_var("CLIENT_SECRET"),
        )
    )

    songs = []
    results = sp.playlist_tracks(playlist_id)

    while results:
        # with open("results.json", "w") as f:
        #     json.dump(results, f, indent=4)
        for item in results["items"]:
            track = item["track"]
            if track:
                day, month, year = resolve_date(track["album"]["release_date"], month_lang=month_lang, no_day=no_day)
                added_at = item["added_at"]  # format: "YYYY-MM-DDTHH:MM:SSZ"
                # Only add if added_after is not set or added_at > added_after
                add_song = True
                if added_after:
                    try:
                        added_after_dt = datetime.datetime.strptime(added_after, "%Y-%m-%d")
                        added_at_dt = datetime.datetime.strptime(added_at[:10], "%Y-%m-%d")
                        add_song = added_at_dt > added_after_dt
                    except Exception as e:
                        logger.warning(f"Could not filter by added_after: {e}")
                        add_song = True
                if add_song:
                    song = {
                        "name": track["name"],
                        "artists": [artist["name"] for artist in track["artists"]],
                        "day": day,
                        "month": month,
                        "year": year,
                        "release_date": track["album"]["release_date"],
                        "url": track["external_urls"]["spotify"],
                        "id": track["id"],
                    }
                    songs.append(song)
                    if verbose:
                        artists_str = ', '.join(song['artists'])
                        if len(artists_str) > 24:
                            artists_str = artists_str[:23] + '…'
                        logger.debug(f"Song: {song['name']:<28} | Artists: {artists_str:<24} | Release Date: {song['release_date']}")
        results = sp.next(results) if results["next"] else None

    # Sort songs by release_date (YYYY-MM-DD)
    songs.sort(key=lambda song: song.get("release_date") or "0000-00-00")
    return songs


def generate_qr_codes(songs: list[dict], qr_type: str = "url") -> list[dict]:
    for song in songs:
        if qr_type == "id":
            qr_content = song["id"]
        else: # default to "url"
            qr_content = song["url"]
        img = qrcode.make(qr_content, image_factory=qrcode.image.svg.SvgPathImage)
        svg = ElementTree.tostring(img.get_image()).decode()
        song["svg"] = svg
    return songs

def generate_year_distribution_pdf(songs: list[dict], output_pdf: str) -> None:
    year_counts = Counter(int(song["year"]) for song in songs if "year" in song and song["year"].isdigit())

    if not year_counts:
        logger.warning("No valid year data found in songs. Skipping year distribution PDF generation.")
        return

    min_year = min(year_counts.keys())
    max_year = max(year_counts.keys())
    all_years = list(range(min_year, max_year + 1))
    counts = [year_counts.get(year, 0) for year in all_years]

    plt.figure()
    plt.bar(all_years, counts, color="black")
    plt.ylabel("number of songs released")
    plt.xticks()

    with PdfPages(output_pdf) as pdf:
        pdf.savefig()
        plt.close()


