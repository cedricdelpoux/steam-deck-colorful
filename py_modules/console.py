"""Decide which artwork and which color a library tab should get.

The two are resolved independently, both from the tab's own title/collection
name: the source color table can give what's otherwise the same hardware two
different colors depending on the regional name used (e.g. Genesis's red vs.
Mega Drive's blue), regardless of which artwork file that name matched. So
the color is resolved from what the user calls the tab, and only falls back
to the artwork's own color when that name means nothing to the table.
"""
import json
import os

import tabmaster
import vendor_names

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(HERE, 'assets')
ART_DIR = os.path.join(ASSETS, 'consoles')

_cache = {}


def _load(name):
    if name not in _cache:
        try:
            with open(os.path.join(ASSETS, name)) as f:
                _cache[name] = json.load(f)
        except (OSError, ValueError):
            _cache[name] = {}
    return _cache[name]


def catalog():
    """Artwork name -> {'file', 'color'} for everything the plugin ships."""
    return _load('console-map.json')


def _canonical(name):
    """Colors.json's short key ("genesis") a name resolves to, or None."""
    table = _load('colors.json')
    colors, aliases = table.get('colors', {}), table.get('aliases', {})
    for variant in vendor_names.variants(name):
        if variant in colors:
            return variant
        if variant in aliases and aliases[variant] in colors:
            return aliases[variant]
    return None


def color_for(name):
    """Color the source table gives this name, or None."""
    key = _canonical(name)
    return _load('colors.json').get('colors', {}).get(key) if key else None


def meta_for(name):
    """{'vendor', 'year'} the source theme gives this name, or {}.

    Used for the panel's "no game selected" fallback -- purely cosmetic, so a
    miss (name doesn't resolve, or the theme had no vendor/year for it) just
    means those two lines don't show, nothing else depends on it.
    """
    key = _canonical(name)
    return _load('colors.json').get('meta', {}).get(key, {}) if key else {}


def resolve(overrides=None):
    """Every placed tab with the artwork file and color it should display.

    overrides: tab id -> {'artwork': <name|''>, 'color': '#rrggbb'}; '' for
    artwork means "no panel on this tab".
    """
    overrides = overrides or {}
    art = catalog()
    out = []

    for tab in tabmaster.resolve(ART_DIR, {
        tab_id: o.get('artwork') for tab_id, o in overrides.items() if 'artwork' in o
    }):
        override = overrides.get(tab['id'], {})
        entry = None
        if tab['artwork']:
            name = os.path.splitext(tab['artwork'])[0]
            entry = art.get(name)

        # The user's own wording decides the color -- tried before the
        # auto-generated collection name, since that can itself resolve to a
        # color (e.g. "Sega Genesis/Mega Drive" aliases to Genesis's red) that
        # overrides a title the user deliberately chose to read differently.
        color = override.get('color')
        if not color:
            for candidate in [tab['title']] + tab['collections']:
                color = color_for(candidate)
                if color:
                    break
        if not color and entry:
            color = entry.get('color')

        out.append({
            'id': tab['id'],
            'title': tab['title'],
            'position': tab['position'],
            'artwork': tab['artwork'],
            'color': color,
            'source': 'manual' if override else tab['source'],
            # Steam collection name(s) this tab is built from -- lets the
            # panel script pull live playtime/last-played straight from
            # collectionStore for the "no game selected" fallback view.
            'collections': tab['collections'],
        })
    return out
