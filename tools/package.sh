#!/usr/bin/env bash
# Build the plugin and package it the way Decky expects:
# out/<name>/ (what gets installed) and out/<name>.zip (what gets released).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$ROOT/plugin.json")"
OUT="$ROOT/out"

cd "$ROOT"
npm run build --silent

rm -rf "$OUT"
mkdir -p "$OUT/$NAME/py_modules"
# package.json is read at runtime: its "type": "module" picks Decky's ES module loader.
cp -R dist assets main.py plugin.json package.json LICENSE README.md "$OUT/$NAME/"
cp py_modules/*.py "$OUT/$NAME/py_modules/"
rm -f "$OUT/$NAME/dist/"*.map

(cd "$OUT" && zip -qr "$NAME.zip" "$NAME" -x '*.DS_Store')
echo "$OUT/$NAME.zip"
