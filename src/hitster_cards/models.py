from dataclasses import dataclass

@dataclass
class Song:
    name: str
    artists: list[str]
    isrc: str
    url: str
    id: str
    svg: str

@dataclass
class DatedSong(Song):
    release_date: str  # YYYY-MM-DD
    year: str
    month: str
    day: str
