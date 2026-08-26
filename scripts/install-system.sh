#!/usr/bin/env sh

set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this script with sudo: sudo ./scripts/install-system" >&2
    exit 1
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)
SOURCE="$PROJECT_ROOT/.venv/bin/container2vm"
TARGET="/usr/local/bin/container2vm"

if [ ! -x "$SOURCE" ]; then
    echo "Executable not found: $SOURCE" >&2
    echo "Create the virtual environment and install the project first:" >&2
    echo "  python3 -m venv .venv" >&2
    echo "  .venv/bin/pip install -e ." >&2
    exit 1
fi

if [ -e "$TARGET" ] && [ ! -L "$TARGET" ]; then
    echo "Refusing to replace existing non-symlink: $TARGET" >&2
    exit 1
fi

ln -sfn "$SOURCE" "$TARGET"

echo "Installed $TARGET -> $SOURCE"
echo "You can now run: sudo container2vm --help"
