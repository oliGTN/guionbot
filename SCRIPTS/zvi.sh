#!/bin/bash

# Edit a compressed or legacy player cache with vi, then recompress it.
# Usage:
#   ./zvi.sh <player_id>
#   ./zvi.sh <player_id>.json
#   ./zvi.sh <player_id>.json.gz
#   ./zvi.sh PLAYERS/<player_id>.json.gz

set -u
umask 077

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <player_id|file.json|file.json.gz>"
    exit 1
fi

arg="$1"

# Resolve the input path.
case "$arg" in
    */*) base="$arg" ;;
    *)   base="PLAYERS/$arg" ;;
esac

case "$base" in
    *.json.gz)
        source="$base"
        compressed="$base"
        legacy="${base%.gz}"
        ;;
    *.json)
        source="$base"
        legacy="$base"
        compressed="$base.gz"
        ;;
    *)
        if [ -f "$base.json.gz" ]; then
            source="$base.json.gz"
            compressed="$source"
            legacy="$base.json"
        elif [ -f "$base.json" ]; then
            source="$base.json"
            legacy="$source"
            compressed="$base.json.gz"
        else
            echo "ERROR: Cache file not found: $base"
            exit 1
        fi
        ;;
esac

if [ ! -f "$source" ]; then
    echo "ERROR: File not found: $source"
    exit 1
fi

dir=$(dirname "$source")
work=$(mktemp "$dir/.zvi.XXXXXX") || exit 1
packed=$(mktemp "$dir/.zvi.XXXXXX.gz") || {
    rm -f "$work"
    exit 1
}

# Preserve the temporary edited file on errors or interruption.
keep_work=1

cleanup() {
    rm -f "$packed"
    if [ "$keep_work" -eq 0 ]; then
        rm -f "$work"
    else
        echo "Edited file preserved at: $work"
    fi
}
trap cleanup EXIT

echo "Opening: $source"

# Decompress or copy the legacy JSON into the working file.
case "$source" in
    *.json.gz)
        if ! gzip -cd -- "$source" > "$work"; then
            echo "ERROR: Cannot decompress $source"
            exit 1
        fi
        ;;
    *)
        if ! cp -- "$source" "$work"; then
            echo "ERROR: Cannot copy $source"
            exit 1
        fi
        ;;
esac

# Open the file in the selected editor.
editor="${VISUAL:-${EDITOR:-vi}}"
$editor "$work"
editor_status=$?

if [ "$editor_status" -ne 0 ]; then
    echo "ERROR: Editor exited with status $editor_status."
    exit 1
fi

# Validate JSON before replacing anything.
if ! python3 -m json.tool "$work" > /dev/null; then
    echo "ERROR: Invalid JSON. Original cache was not changed."
    exit 1
fi

# Compress into a temporary file.
if ! gzip -c "$work" > "$packed"; then
    echo "ERROR: Compression failed. Original cache was not changed."
    exit 1
fi

if ! gzip -t "$packed"; then
    echo "ERROR: Compressed file verification failed."
    exit 1
fi

# Preserve original permissions.
chmod --reference="$source" "$packed" || exit 1

# Atomic replacement of the compressed cache.
if ! mv -f -- "$packed" "$compressed"; then
    echo "ERROR: Cannot install compressed cache."
    exit 1
fi

# Remove legacy JSON only after successful compression.
if [ "$source" != "$compressed" ]; then
    rm -f -- "$source"
fi

keep_work=0

echo "Successfully saved: $compressed"
