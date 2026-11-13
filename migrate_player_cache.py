#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migrate legacy PLAYERS/*.json files to verified .json.gz cache files.

Dry-run is the default. Use --apply to perform the migration.
Stop the bot before applying the migration to avoid racing live cache writes.
"""

import argparse
import json
import os
import shutil
import sys

import player_cache


def human_size(size):
    return "{:.2f} GB".format(size / (1024 ** 3))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually migrate files (default: report only)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="maximum number of files to migrate; 0 means no limit",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=100,
        help="print progress every N processed files (default: 100)",
    )
    args = parser.parse_args()

    cache_dir = player_cache.PLAYER_CACHE_DIR
    if not os.path.isdir(cache_dir):
        print("ERROR: directory not found: {}".format(cache_dir))
        return 1

    legacy_files = []
    already_compressed = 0
    total_bytes = 0

    for filename in sorted(os.listdir(cache_dir)):
        if not filename.endswith(".json"):
            continue

        legacy_path = os.path.join(cache_dir, filename)
        if not os.path.isfile(legacy_path):
            continue

        player_id = filename[:-5]
        compressed_path = os.path.join(cache_dir, filename + ".gz")

        if os.path.exists(compressed_path):
            already_compressed += 1
            continue

        size = os.path.getsize(legacy_path)
        legacy_files.append((player_id, legacy_path, size))
        total_bytes += size

    print("PLAYERS cache migration")
    print("Mode: {}".format("APPLY" if args.apply else "DRY RUN"))
    print("Legacy JSON files to consider: {:,}".format(len(legacy_files)))
    print("Already have a .json.gz file: {:,}".format(already_compressed))
    print("Legacy data size: {}".format(human_size(total_bytes)))

    if not args.apply:
        print("\nNo files changed. Run with --apply to migrate.")
        print("For a small first batch, use: python3 migrate_player_cache.py --apply --limit 20")
        return 0

    if args.limit < 0:
        print("ERROR: --limit cannot be negative")
        return 1

    if args.progress_every < 1:
        print("ERROR: --progress-every must be at least 1")
        return 1

    files_to_process = legacy_files
    if args.limit:
        files_to_process = files_to_process[:args.limit]

    migrated = 0
    skipped_empty = 0
    errors = 0
    bytes_before = 0
    bytes_after = 0

    for index, (player_id, legacy_path, original_size) in enumerate(files_to_process, 1):
        try:
            # Parse before saving: malformed legacy JSON is left untouched.
            with open(legacy_path, "r", encoding="utf-8") as source_file:
                player_data = json.load(source_file)

            # save_player_cache writes a temporary gzip file, verifies that
            # it can be decompressed and parsed, installs it atomically, and
            # only then removes the original .json file.
            player_cache.save_player_cache(player_id, player_data)

            compressed_path = legacy_path + ".gz"
            compressed_size = os.path.getsize(compressed_path)
            migrated += 1
            bytes_before += original_size
            bytes_after += compressed_size

        except Exception as exc:
            errors += 1
            print("ERROR {}: {}".format(os.path.basename(legacy_path), exc))

        if index % args.progress_every == 0 or index == len(files_to_process):
            print(
                "Progress: {}/{} | migrated={} | errors={}".format(
                    index, len(files_to_process), migrated, errors
                )
            )

    print("\nMigration result")
    print("Migrated: {:,}".format(migrated))
    print("Errors (original files preserved): {:,}".format(errors))
    print("Uncompressed size migrated: {}".format(human_size(bytes_before)))
    print("Compressed size: {}".format(human_size(bytes_after)))
    if bytes_before:
        saved = bytes_before - bytes_after
        print("Space saved: {} ({:.1f}%)".format(
            human_size(saved), 100.0 * saved / bytes_before
        ))

    remaining = sum(
        1 for filename in os.listdir(cache_dir)
        if filename.endswith(".json")
        and os.path.isfile(os.path.join(cache_dir, filename))
    )
    print("Legacy .json files remaining: {:,}".format(remaining))

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
