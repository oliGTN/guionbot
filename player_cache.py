# -*- coding: utf-8 -*-
"""Read, write and delete the on-disk SWGOH player cache.

New cache entries are stored as compact gzip-compressed JSON. Reads remain
backwards-compatible with the legacy uncompressed .json files.
"""

import gzip
import json
import os
import tempfile


PLAYER_CACHE_DIR = "PLAYERS"


def _cache_paths(player_id):
    """Return the compressed and legacy paths for a player cache."""
    basename = str(player_id)
    return (
        os.path.join(PLAYER_CACHE_DIR, basename + ".json.gz"),
        os.path.join(PLAYER_CACHE_DIR, basename + ".json"),
    )


def load_player_cache(player_id):
    """Load a player cache, preferring gzip and falling back to legacy JSON.

    Returns None when no cache exists or when the selected cache is empty.
    Invalid JSON or gzip data is allowed to raise so callers can detect
    cache corruption rather than silently treating it as a cache miss.
    """
    compressed_path, legacy_path = _cache_paths(player_id)

    if os.path.isfile(compressed_path):
        cache_path = compressed_path
        opener = gzip.open
    elif os.path.isfile(legacy_path):
        cache_path = legacy_path
        opener = open
    else:
        return None

    if os.path.getsize(cache_path) == 0:
        # Do not delete a valid legacy cache just because a compressed file
        # is empty or incomplete.
        os.remove(cache_path)
        if cache_path == compressed_path and os.path.isfile(legacy_path):
            cache_path = legacy_path
            opener = open
        else:
            return None

    with opener(cache_path, "rt", encoding="utf-8") as cache_file:
        return json.load(cache_file)


def save_player_cache(player_id, player_data):
    """Atomically save compact gzip JSON, then remove the legacy JSON file."""
    compressed_path, legacy_path = _cache_paths(player_id)
    cache_dir = os.path.dirname(compressed_path) or "."
    os.makedirs(cache_dir, exist_ok=True)

    fd, temporary_path = tempfile.mkstemp(
        prefix="." + str(player_id) + ".",
        suffix=".json.gz.tmp",
        dir=cache_dir,
    )
    os.close(fd)

    try:
        with gzip.open(
            temporary_path, "wt", encoding="utf-8", compresslevel=6
        ) as cache_file:
            json.dump(
                player_data,
                cache_file,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        # Verify that the temporary gzip stream is readable JSON before
        # replacing the current cache or deleting the legacy file.
        with gzip.open(temporary_path, "rt", encoding="utf-8") as check_file:
            json.load(check_file)

        # Install atomically only after successful verification.
        os.replace(temporary_path, compressed_path)

        if os.path.exists(legacy_path):
            os.remove(legacy_path)
    except Exception:
        try:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)
        except OSError:
            pass
        raise


def delete_player_cache(player_id):
    """Delete both compressed and legacy cache formats for a player."""
    compressed_path, legacy_path = _cache_paths(player_id)
    for cache_path in (compressed_path, legacy_path):
        if os.path.exists(cache_path):
            os.remove(cache_path)
