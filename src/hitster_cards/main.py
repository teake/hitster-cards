import json
import logging
import pathlib
import random
import dataclasses

import click
import typst
from tqdm import tqdm

from .utils import generate_year_distribution_pdf, generate_qr_code
from .spotify import get_playlist_songs, get_playlist_name
from .release_date import date_song, correct_release_dates_gemini, correct_release_dates


@click.command()
@click.argument("playlist_id", envvar="PLAYLIST_ID")
@click.option("--edition")
@click.option("--font")
def main(playlist_id: str, edition: str | None = None, font: str | None = None) -> None:
    """Generate Hitster game cards from a Spotify playlist with id PLAYLIST_ID"""
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    if not edition:
        edition = get_playlist_name(playlist_id)

    data_file = pathlib.Path(f"hitster-data-{playlist_id}.json")
    if data_file.exists():
        logger.info(f"Reading data from {data_file}.")
        song_data = json.loads(data_file.read_text())
        logger.info(f"Found {len(song_data)} songs.")
    else:
        logger.info(f"Starting Spotify song retrieval for playlist {playlist_id}.")
        songs = list(get_playlist_songs(playlist_id))
        logger.info(f"Found {len(songs)} songs.")
        logger.info("Querying Spotify and MusicBrainz for the original release date.")
        songs = [dated_song for song in tqdm(songs) if (dated_song := date_song(song))]
        logger.info(f"Dated {len(songs)} songs.")
        logger.info("Correcting release dates with Gemini.")
        corrected_songs = list(correct_release_dates_gemini(songs))
        songs = correct_release_dates(songs, corrected_songs)
        logger.info(f"Corrected {len(corrected_songs)} release dates.")

        song_data = [dataclasses.asdict(song) for song in songs]
        data_file = f"hitster-data-{playlist_id}.json"
        with open(data_file, "w") as f:
            json.dump(song_data, f, indent=4)
        logger.info(f"Song data written to {data_file}.")

    random.seed("hitster")
    random.shuffle(song_data)

    logger.info("Generating QR codes.")
    song_data = [
        {**song, **generate_qr_code(song["url"])}
        for song in tqdm(song_data)
    ]

    sys_inputs = {
        "songs": json.dumps(song_data),
        "edition": edition if edition else "",
        "font": font if font else "",
    }
    typ_file = pathlib.Path(__file__).parent / "hitster_cards.typ"
    out_file = f"hitster-cards-{playlist_id}.pdf"
    typst.compile(typ_file, output=out_file, sys_inputs=sys_inputs)
    logger.info(f"Cards written to {out_file}.")

    out_file = f"hitster-years-{playlist_id}.pdf"
    generate_year_distribution_pdf([song["release_date"] for song in song_data], out_file)
    logger.info(f"Year distribution written to {out_file}.")

    logger.info("Done.")
