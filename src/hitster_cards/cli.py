import argparse
import json
import logging
import os
import pathlib
import random

import typst
from dotenv import load_dotenv

from .hitster_cards import get_playlist_songs, generate_qr_codes, generate_year_distribution_pdf

load_dotenv()

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

def main():
    random.seed("hitster")
    parser = argparse.ArgumentParser(description="Generate Hitster game cards from a Spotify playlist")
    parser.add_argument("playlist_id", type=str, nargs="?", help="Spotify playlist ID to generate cards from (overrides PLAYLIST_ID env var)", default=None)
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output (show each song)")
    parser.add_argument("--cards-pdf", default="hitster-cards.pdf", help="Output PDF filename for cards")
    parser.add_argument("--overview-pdf", default="year-distribution.pdf", help="Output PDF filename for year distribution bar chart")
    parser.add_argument("--month-lang", choices=["de", "en"], default=None, help="Language for month names in release dates (default: system locale)")
    parser.add_argument("--no-day", action="store_true", help="Omit day from release date (set day to empty string)")
    parser.add_argument("--qr-type", choices=["url", "id"], default="url", help="QR code content: url (default) or id")
    parser.add_argument("--added-after", type=str, help="Only include songs added after this date (YYYY-MM-DD)")
    parser.add_argument("--edition", type=str, default=None, help="Edition label to display on the cards (e.g., 'Summer 2025')")
    parser.add_argument("--font", type=str, default=None, help="Font family to use in the Typst document (e.g., 'Libertinus Serif', 'Ubuntu'). The font family must be installed on the system!")
    parser.add_argument(
        "-c", "--custom-card",
        action="append",
        default=[],
        metavar="QR,TITLE,YEAR,ARTIST,MONTH",
        help="Add a custom card: qr-string,title,year,artist,month. Can be used multiple times."
    )
    args = parser.parse_args()

    playlist_id = args.playlist_id or os.getenv("PLAYLIST_ID")
    if not playlist_id:
        parser.error("No playlist_id provided and PLAYLIST_ID env var not set.")

    # Set logging level for this module only
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Overview of used arguments
    logger.info("""
========== Hitster Cards - Argument Overview ==========
Playlist ID:         %s
Month Language:      %s
Day in Release Date: %s
QR Code Content:     %s
Cards PDF Output:    %s
Year Distribution:   %s
Added After:         %s
Edition:             %s
Font:                %s
=======================================================
""" % (
        playlist_id,
        args.month_lang if args.month_lang else 'default system locale',
        'omitted' if args.no_day else 'included',
        args.qr_type,
        args.cards_pdf,
        args.overview_pdf,
        args.added_after if args.added_after else 'not set',
        args.edition if args.edition else 'not set',
        args.font if args.font else 'default font (New Computer Modern)'
    ))

    logger.info(f"Starting Spotify song retrieval for playlist: {playlist_id}")
    songs = get_playlist_songs(playlist_id, verbose=args.verbose, month_lang=args.month_lang, no_day=args.no_day, added_after=args.added_after)

    logger.info(f"Number of songs (after filtering): {len(songs)}")

    # Add custom cards to songs list
    for custom in args.custom_card:
        # Split by comma, allow empty month
        parts = [x.strip() for x in custom.split(",")]
        if len(parts) != 5:
            logger.error(f"Custom card must have 5 fields: qr-string,title,year,artist,month. Got {len(parts)}: {custom}")
            continue
        qr_string, title, year, artist, month = parts
        # Use a unique id for custom cards
        custom_id = f"custom_{len(songs)+1}"
        songs.append({
            "id": custom_id,
            "url": qr_string,
            "name": title,
            "year": year,
            "artists": [artist],
            "month": month,
            "day": "",
            "release_date": "",
            "custom": "true"
        })
        logger.info(f"Added custom card '{custom_id}': Title: '{title}', Year: '{year}', Artist: '{artist}', Month: '{month}'")

    logger.info("Generating QR codes")
    songs = generate_qr_codes(songs, qr_type=args.qr_type)

    logger.info("Compiling Cards PDF")
    sys_inputs = {"songs": json.dumps(songs)}
    if args.edition:
        sys_inputs["edition"] = args.edition
    if args.font:
        sys_inputs["font"] = args.font
    typ_file = pathlib.Path(__file__).parent / "hitster_cards.typ"
    typst.compile(typ_file, output=args.cards_pdf, sys_inputs=sys_inputs)

    logger.info("Compiling Year Distribution PDF")
    generate_year_distribution_pdf(songs, args.overview_pdf)

    logger.info("Done")
