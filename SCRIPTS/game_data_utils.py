"""Load large GameData JSON files once per Python process."""

import json
import os

_GAME_DATA_CACHE = {}


def load_game_data(filename):
    """Return the parsed GameData object cached for this absolute filename."""
    cache_key = os.path.realpath(filename)

    if cache_key not in _GAME_DATA_CACHE:
        print("Loading GameData file: {}".format(filename))
        with open(filename, "r") as source_file:
            _GAME_DATA_CACHE[cache_key] = json.load(source_file)

    return _GAME_DATA_CACHE[cache_key]
