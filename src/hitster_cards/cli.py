import json
import logging
import pathlib
import random
import dataclasses

import click
import typst
from tqdm import tqdm

from .utils import generate_year_distribution_pdf
from .spotify import get_playlist_songs
from .release_date import date_song


@click.command()
@click.argument("playlist_id", envvar="PLAYLIST_ID")
@click.option("--cards-pdf", default="hitster-cards.pdf", help="Output PDF filename for cards")
@click.option("--overview-pdf", default="year-distribution.pdf", help="Output PDF filename for year distribution bar chart")
def main(playlist_id: str, cards_pdf: str, overview_pdf: str) -> None:
    """Generate Hitster game cards from a Spotify playlist with id PLAYLIST_ID"""
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    logger.info(f"Starting Spotify song retrieval for playlist {playlist_id}.")
    songs = list(get_playlist_songs(playlist_id))
    logger.info(f"Found {len(songs)} songs.")
    logger.info(f"Querying MusicBrainz and Gemini for the original release date.")
    songs = [dated_song for song in tqdm(songs) if (dated_song := date_song(song))]
    logger.info(f"Dated {len(songs)} songs.")

    random.seed("hitster")
    random.shuffle(songs)

    logger.info("Compiling cards PDF.")
    sys_inputs = {"songs": json.dumps([dataclasses.asdict(song) for song in songs])}
    typ_file = pathlib.Path(__file__).parent / "hitster_cards.typ"
    typst.compile(typ_file, output=cards_pdf, sys_inputs=sys_inputs)

    logger.info("Compiling year distribution PDF.")
    generate_year_distribution_pdf(songs, overview_pdf)

    logger.info("Done.")
