#!/usr/bin/env bash
# Deploy the plugin to the Steam Deck.
#
#   ./install.sh [user@host]
#
# ~/homebrew/plugins is root-owned (the loader runs as root), so the files go
# through a staging folder in the deck user's home and are moved into place with
# sudo. The loader is restarted at the end; the panel comes back on its own once
# Big Picture is up again.
set -euo pipefail

DECK="${1:-deck@192.168.1.153}"
KEY="${SSH_KEY:-$HOME/.ssh/cedric}"
NAME="Colorful"
HERE="$(cd "$(dirname "$0")" && pwd)"
SSH=(ssh -i "$KEY" -o ConnectTimeout=10 "$DECK")

if [ ! -f "$HERE/plugin/dist/index.js" ]; then
  echo "dist/index.js missing -- run: cd plugin && npm install && npm run build" >&2
  exit 1
fi

echo "==> copying to $DECK"
rsync -az --delete \
  -e "ssh -i $KEY -o ConnectTimeout=10" \
  --exclude node_modules --exclude src --exclude tools --exclude __pycache__ \
  --exclude '.*' --exclude package-lock.json --exclude rollup.config.js --exclude tsconfig.json \
  "$HERE/plugin/" "$DECK:~/decky-colorful/"

echo "==> installing"
"${SSH[@]}" "sudo -n true 2>/dev/null || { echo 'passwordless sudo unavailable -- run the install block by hand on the Deck' >&2; exit 2; }
  sudo rm -rf '/home/deck/homebrew/plugins/$NAME'
  sudo cp -r /home/deck/decky-colorful '/home/deck/homebrew/plugins/$NAME'
  sudo chown -R root:root '/home/deck/homebrew/plugins/$NAME'
  sudo systemctl restart plugin_loader.service"

echo "==> done; give the loader a few seconds, then open the Decky menu"
