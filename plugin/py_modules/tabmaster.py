"""Map TabMaster library tabs to console artwork.

A TabMaster tab is usually built from a single Steam collection filter, and that
collection is the one Steam ROM Manager created per system ("Nintendo GameCube",
"Sega Genesis/Mega Drive"...). Those names line up with the artwork filenames,
which makes the mapping automatic; anything ambiguous can still be pinned by
hand from the plugin settings.
"""
import json
import os
import re

SETTINGS = os.path.expanduser('~/homebrew/settings/TabMaster/settings.json')


def tabs():
    """Tabs in bar order: [{'id', 'title', 'collections': [...]}, ...].

    Only tabs with a real position are returned -- TabMaster stores hidden or
    unplaced ones with position -1.
    """
    try:
        with open(SETTINGS) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []

    out = []
    for user in data.get('usersDict', {}).values():
        for tab_id, tab in user.get('tabs', {}).items():
            position = tab.get('position', -1)
            if position is None or position < 0:
                continue
            collections = [
                f.get('params', {}).get('name')
                for f in tab.get('filters', []) or []
                if f.get('type') == 'collection' and f.get('params', {}).get('name')
            ]
            out.append({'id': tab_id, 'title': tab.get('title', ''),
                        'position': position, 'collections': collections})
    out.sort(key=lambda t: t['position'])
    return out


def _index(art_dir):
    """Lowercased artwork name -> actual filename."""
    try:
        names = os.listdir(art_dir)
    except OSError:
        return {}
    return {os.path.splitext(n)[0].lower(): n for n in names if n.lower().endswith('.png')}


# Tab names that mean a console the artwork spells differently. Deliberately
# short: anything else is one dropdown away in the plugin settings.
ALIASES = {
    'deck': 'steam',
    'steam deck': 'steam',
}


def match(name, art_dir):
    """Artwork filename for a collection or tab name, or None.

    Compound names are also tried piece by piece: Steam ROM Manager writes
    "Sega Genesis/Mega Drive" where the artwork is just "Sega Genesis", and
    "Nintendo SNES (Super Nintendo)" where it's just "Nintendo SNES".
    """
    if not name:
        return None
    index = _index(art_dir)
    bare = re.sub(r'\s*\([^)]*\)', '', name).strip()
    candidates = [name, bare] + name.split('/') + bare.split('/')
    for part in candidates:
        key = part.strip().lower()
        key = ALIASES.get(key, key)
        if key in index:
            return index[key]
    return None


def resolve(art_dir, overrides=None):
    """Tabs in bar order, each with the artwork it should use.

    `overrides` maps a tab id to an artwork filename (or '' to show no panel),
    and always wins over the automatic match.
    """
    overrides = overrides or {}
    resolved = []
    for tab in tabs():
        if tab['id'] in overrides:
            artwork = overrides[tab['id']] or None
            source = 'manual'
        else:
            artwork = None
            for candidate in tab['collections'] + [tab['title']]:
                artwork = match(candidate, art_dir)
                if artwork:
                    break
            source = 'auto' if artwork else 'none'
        resolved.append(dict(tab, artwork=artwork, source=source))
    return resolved
