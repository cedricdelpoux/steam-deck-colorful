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

"$HERE/tools/package.sh" >/dev/null

echo "==> copying to $DECK"
rsync -az --delete -e "ssh -i $KEY -o ConnectTimeout=10" \
  "$HERE/out/$NAME/" "$DECK:~/decky-colorful/"

echo "==> installing"
"${SSH[@]}" "sudo -n true 2>/dev/null || { echo 'passwordless sudo unavailable -- run the install block by hand on the Deck' >&2; exit 2; }
  sudo rm -rf '/home/deck/homebrew/plugins/$NAME'
  sudo cp -r /home/deck/decky-colorful '/home/deck/homebrew/plugins/$NAME'
  sudo chown -R root:root '/home/deck/homebrew/plugins/$NAME'
  sudo systemctl restart plugin_loader.service"

echo "==> done; give the loader a few seconds, then open the Decky menu"
