from collections.abc import Iterable

import spotipy

from .models import Song
from .utils import generate_qr_code


def get_playlist_songs(playlist_id: str) -> Iterable[Song]:
    sp = spotipy.Spotify(auth_manager=spotipy.SpotifyClientCredentials())
    results = sp.playlist_items(playlist_id, additional_types=('track',))
    while results:
        for item in results["items"]:
            track = item["track"]
            song = Song(
                name=track["name"],
                artists=[artist["name"] for artist in track["artists"]],
                isrc=track["external_ids"]["isrc"],
                id=track["id"],
                url=track["external_urls"]["spotify"],
                svg=generate_qr_code(track["external_urls"]["spotify"])
            )
            yield song
        results = sp.next(results) if results["next"] else None

