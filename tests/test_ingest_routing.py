"""Tests für die Eingabe-Klassifikation (Quellen-Routing)."""

from __future__ import annotations

import pytest

from txtsong.ingest.base import classify_input


@pytest.mark.parametrize(
    "value,expected",
    [
        ("https://open.spotify.com/track/abc", "spotify"),
        ("spotify:track:abc", "spotify"),
        ("https://www.youtube.com/watch?v=abc", "url"),
        ("https://youtu.be/abc", "url"),
        ("https://soundcloud.com/artist/track", "url"),
        ("https://artist.bandcamp.com/track/song", "url"),
        ("/home/user/song.mp3", "local"),
        ("song.wav", "local"),
    ],
)
def test_classify_input(value: str, expected: str):
    assert classify_input(value) == expected
