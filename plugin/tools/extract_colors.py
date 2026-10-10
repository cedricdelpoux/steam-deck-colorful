"""Build assets/colors.json from the source theme's CollectionData.qml (see
README.md for which theme and where to get it).

Run once at packaging time, not on the Deck: the plugin ships the resulting
JSON so it never needs that theme at runtime.

    python3 tools/extract_colors.py "<path to CollectionData.qml>"

The QML holds two tables we need: per-system colors keyed by short name
("gamecube"), and aliases that map spoken-out names ("nintendo 3ds") onto those
short names -- which is what lets the full artwork filenames resolve. Each
system's entry also carries a vendor and a release year, pulled along as
`meta` for the panel's "no game selected" fallback view.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, 'assets', 'colors.json')


def parse(qml):
    text = open(qml, encoding='utf-8', errors='replace').read()

    colors, meta = {}, {}
    for key, body in re.findall(r"'([^']+)'\s*:\s*\{([^{}]*)\}", text):
        color_m = re.search(r"color:\s*'(#[0-9a-fA-F]{3,8})'", body)
        if not color_m:
            continue
        key = key.strip().lower()
        colors[key] = color_m.group(1).lower()

        entry = {}
        vendor_m = re.search(r"vendor:\s*'([^']*)'", body)
        year_m = re.search(r"year:\s*'([^']*)'", body)
        if vendor_m and vendor_m.group(1):
            entry['vendor'] = vendor_m.group(1)
        if year_m and year_m.group(1):
            entry['year'] = year_m.group(1)
        if entry:
            meta[key] = entry

    aliases = {}
    block = re.search(r'property var aliases:\s*\{(.*?)\n\s*\}', text, re.S)
    if block:
        for name, target in re.findall(r"'([^']+)'\s*:\s*'([^']+)'", block.group(1)):
            aliases[name.strip().lower()] = target.strip().lower()

    return colors, aliases, meta


def main():
    qml = sys.argv[1] if len(sys.argv) > 1 else None
    if not qml or not os.path.isfile(qml):
        print('usage: extract_colors.py <CollectionData.qml>')
        return 1

    colors, aliases, meta = parse(qml)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump({'colors': colors, 'aliases': aliases, 'meta': meta,
                   'default': colors.get('default', '#194492')}, f, indent=1, sort_keys=True)

    print('%d colors, %d aliases, %d with vendor/year -> %s' %
          (len(colors), len(aliases), len(meta), OUT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
