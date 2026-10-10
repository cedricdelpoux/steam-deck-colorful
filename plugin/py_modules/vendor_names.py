"""Shared vendor-prefix stripping for console names.

Used by both console.py (resolving a TabMaster tab's name to a color at
runtime) and tools/build_assets.py (resolving an artwork file's name to a
color at packaging time), so the matching rules can't drift between the two.
"""
import re

# Names are "<vendor> <model>" (tab titles and artwork filenames alike) while
# colors.json is keyed by model alone, so the vendor word gets stripped when
# looking a name up.
VENDORS = {
    'nintendo', 'sony', 'sega', 'microsoft', 'nec', 'atari', 'commodore', 'apple',
    'sharp', 'fujitsu', 'epoch', 'casio', 'bally', 'fairchild', 'amstrad', 'taito',
    'namco', 'sammy', 'snk', 'panasonic', 'philips', 'coleco', 'magnavox', 'mattel',
    'tiger', 'watara', 'gce', 'emerson', 'arcade', 'category', 'valve',
}


def variants(name):
    """Name forms to try against colors.json, loosest to most specific."""
    key = re.sub(r'\s*\([^)]*\)', '', (name or '').strip().lower())
    if not key:
        return
    yield key
    parts = key.split()
    without_vendor = ' '.join(parts[1:]) if len(parts) > 1 and parts[0] in VENDORS else None
    if without_vendor:
        yield without_vendor
    yield re.sub(r'[^a-z0-9]', '', key)
    if without_vendor:
        yield re.sub(r'[^a-z0-9]', '', without_vendor)
