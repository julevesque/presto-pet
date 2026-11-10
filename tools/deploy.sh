#!/bin/sh
# Copies Presto-Pet to a Pimoroni Presto connected by USB, with mpremote.
#
#   tools/deploy.sh try       # copy the prestopet/ folder only and run the game once; nothing
#                             # else on the device changes, and a reset brings back its main.py
#   tools/deploy.sh install   # back up the device's main.py, then make Presto-Pet start at boot
#
# Requires: pip install mpremote. The save file (prestopet_save.json) is never touched.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# Only the sources, without the caches left by the tests.
mkdir -p "$STAGE/prestopet/pets"
cp "$ROOT"/src/prestopet/*.py "$STAGE/prestopet/"
cp "$ROOT"/src/prestopet/pets/*.py "$STAGE/prestopet/pets/"

MPREMOTE="${MPREMOTE:-mpremote}"

copy_package() {
    $MPREMOTE cp -r "$STAGE/prestopet" :
}

copy_game() {
    copy_package
    # The settings file is copied only when the device has none, so that it never replaces
    # a config.py of another program.
    if $MPREMOTE fs ls :config.py >/dev/null 2>&1; then
        echo "The device already has a config.py: left as is, default settings apply."
    else
        $MPREMOTE cp "$ROOT/src/config.py" :config.py
    fi
}

case "$1" in
    try)
        copy_package
        # Runs without waiting for the end: the game keeps going after mpremote exits.
        $MPREMOTE run --no-follow "$ROOT/src/main.py"
        ;;
    install)
        backup="$ROOT/main.py.device-$(date +%Y%m%d-%H%M%S).bak"
        if $MPREMOTE cp :main.py "$backup"; then
            echo "The previous main.py of the device is saved in $backup"
        fi
        copy_game
        $MPREMOTE cp "$ROOT/src/main.py" :main.py + reset
        ;;
    *)
        echo "usage: $0 try|install"
        exit 1
        ;;
esac
