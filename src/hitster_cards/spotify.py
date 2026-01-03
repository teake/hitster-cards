from collections.abc import Iterable
from functools import cache

import spotipy

from .models import Song


@cache
def spotify_client():
    return spotipy.Spotify(auth_manager=spotipy.SpotifyClientCredentials())

def get_playlist_songs(playlist_id: str) -> Iterable[Song]:
    sp = spotify_client()
    results = sp.playlist_items(playlist_id, additional_types=('track',))
    while results:
        for item in results["items"]:
            track = item["track"]
            song = Song(
                name=track["name"],
                artists=[artist["name"] for artist in track["artists"]],
                isrc=track["external_ids"]["isrc"],
                url=track["external_urls"]["spotify"]
            )
            yield song
        results = sp.next(results) if results["next"] else None


def get_release_dates(isrc: str) -> Iterable[str]:
    sp = spotify_client()
    results = sp.search(q=f"isrc:{isrc}", type="track", limit=50)
    while results:
        for item in results["tracks"]["items"]:
            yield item["album"]["release_date"]
        results = sp.next(results["tracks"]) if results["tracks"]["next"] else None