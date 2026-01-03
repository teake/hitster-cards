from dataclasses import dataclass

@dataclass
class Song:
    name: str
    artists: list[str]
    isrc: str
    url: str

@dataclass
class DatedSong(Song):
    release_date: str  # YYYY-MM-DD
