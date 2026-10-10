#!/usr/bin/env bash
# Deploy the plugin to the Steam Deck from a checkout.
#
#   DECK=deck@<ip> SSH_KEY=~/.ssh/<key> ./install.sh
#
# ~/homebrew/plugins is root-owned (the loader runs as root), so the files go
# through a staging folder in the deck user's home and are moved into place with
# sudo. The loader is restarted at the end; the panel comes back on its own once
# Big Picture is up again.
set -euo pipefail

DECK="${DECK:?set DECK to the Deck's ssh address, e.g. DECK=deck@192.168.1.10}"
KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
NAME="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$(dirname "$0")/plugin.json")"
HERE="$(cd "$(dirname "$0")" && pwd)"
SSH=(ssh -i "$KEY" -o ConnectTimeout=10 "$DECK")

if [ ! -f "$HERE/dist/index.js" ]; then
  echo "dist/index.js missing -- run: npm install && npm run build" >&2
  exit 1
fi

# Only what Decky reads at runtime: package.json is needed (its "type": "module"
# picks the ES module loader), the rest of the tooling is not.
echo "==> copying to $DECK"
rsync -az --delete --delete-excluded \
  -e "ssh -i $KEY -o ConnectTimeout=10" \
  --include dist/ --include 'dist/**' \
  --include assets/ --include 'assets/**' \
  --include py_modules/ --include 'py_modules/*.py' \
  --include main.py --include plugin.json --include package.json \
  --include LICENSE --include README.md \
  --exclude '*' \
  "$HERE/" "$DECK:~/decky-colorful/"

echo "==> installing"
"${SSH[@]}" "sudo -n true 2>/dev/null || { echo 'passwordless sudo unavailable -- run the install block by hand on the Deck' >&2; exit 2; }
  sudo rm -rf '/home/deck/homebrew/plugins/$NAME'
  sudo cp -r /home/deck/decky-colorful '/home/deck/homebrew/plugins/$NAME'
  sudo chown -R root:root '/home/deck/homebrew/plugins/$NAME'
  sudo systemctl restart plugin_loader.service"

echo "==> done; give the loader a few seconds, then open the Decky menu"
