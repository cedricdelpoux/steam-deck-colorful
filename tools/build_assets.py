"""Prepare the console artwork and its color table for shipping.

Run at packaging time on a machine with Pillow, not on the Deck:

    python3 tools/build_assets.py <source dir>... [--max 800]

Sources are the hardware-set renders (see README.md for where those come from)
plus our own additions for hardware they don't cover; later dirs win on a name
clash.

The source renders are 2160x2160 but the panel shows them around 400 physical
pixels wide, so they are downscaled -- that is the difference between a ~300 MB
plugin and a ~30 MB one.

Each artwork also gets a panel color: the hand-picked one from the source
color table when its name resolves there, otherwise the dominant saturated
color of the render itself, which keeps consoles the table never covered
(Xbox, PS3, Switch...) from all falling back to the same blue.
"""
import colorsys
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART_OUT = os.path.join(HERE, 'assets', 'consoles')
COLORS_IN = os.path.join(HERE, 'assets', 'colors.json')
MAP_OUT = os.path.join(HERE, 'assets', 'console-map.json')

# vendor_names.variants() (vendor-prefix stripping) is shared with console.py,
# which resolves the same names at runtime -- only the code that resolves the
# *style* of a console lives twice, by necessity (Pillow at packaging time vs.
# the stylesheet generator on the Deck).
sys.path.insert(0, os.path.join(HERE, 'py_modules'))
import vendor_names

# Hardware the source table never covered, so its color is ours to pick.
# Steam deliberately neutral (dark grey) rather than its own brand blue --
# it sits next to real console colors in the tab strip, and a saturated blue
# read as "just another console" instead of "this is the Steam library itself".
EXTRA_COLORS = {'Steam': '#33363b'}

# Just under the tightest of the source set's own device-and-TV renders (the
# Wii, at ~1.38), so a narrower image still pads out close to what the others
# already look like instead of standing out as an exception.
#
# Only matters for a plain near-square logo/badge now (panel.js sizes each
# tab's artwork independently at a fixed height -- see ensureArt() -- so
# there's no shared width left for a square image to drag down). Steam's own
# render crops to ~1.03 (its own natural framing, not a badge); padding it up
# to MIN_ASPECT would only add dead transparent margin around the same
# content, making it look smaller within its own box for no benefit anymore
# -- excluded here so it keeps its tight crop.
MIN_ASPECT = 1.3
ASPECT_OVERRIDE = {'Steam': 1.0}


def curated_color(name, colors, aliases):
    for variant in vendor_names.variants(name):
        if variant in colors:
            return colors[variant]
        if variant in aliases and aliases[variant] in colors:
            return colors[aliases[variant]]
    return None


def dominant_color(image, min_saturation=0.35, min_value=0.25):
    """Most common vivid color, ignoring the transparent background and grey plastic."""
    small = image.copy()
    small.thumbnail((160, 160))
    buckets = {}
    for r, g, b, a in small.convert('RGBA').getdata():
        if a < 200:
            continue
        _h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s < min_saturation or v < min_value:
            continue
        key = (round(_h * 18), round(s * 4), round(v * 4))
        acc = buckets.setdefault(key, [0, 0, 0, 0])
        acc[0] += r
        acc[1] += g
        acc[2] += b
        acc[3] += 1
    if not buckets:
        return None
    r, g, b, n = max(buckets.values(), key=lambda acc: acc[3])
    return '#%02x%02x%02x' % (r // n, g // n, b // n)


def main():
    args = sys.argv[1:]
    max_size = 800
    if '--max' in args:
        i = args.index('--max')
        max_size = int(args[i + 1])
        del args[i:i + 2]
    sources = [d for d in args if os.path.isdir(d)]
    if not sources:
        print('usage: build_assets.py <source dir>... [--max 800]')
        return 1

    with open(COLORS_IN) as f:
        table = json.load(f)
    colors, aliases, fallback = table['colors'], table['aliases'], table['default']

    os.makedirs(ART_OUT, exist_ok=True)
    mapping = {}
    curated_count = 0

    found = {}
    for source in sources:
        for filename in sorted(os.listdir(source)):
            if filename.lower().endswith('.png'):
                found[filename] = os.path.join(source, filename)

    for filename, path in sorted(found.items()):
        name = filename[:-4]
        image = Image.open(path).convert('RGBA')

        color = EXTRA_COLORS.get(name) or curated_color(name, colors, aliases)
        if color:
            curated_count += 1
        else:
            color = dominant_color(image) or fallback

        # The renders are square with a wide transparent margin; cropping it
        # off first means css.py's width-based sizing reflects the actual
        # console art instead of mostly empty canvas.
        box = image.getbbox()
        if box:
            image = image.crop(box)
        # css.py sizes every tab's artwork by one shared width, set narrow
        # enough that even the tallest-relative-to-width image among the
        # current tabs still fits -- so a single near-square image (a flat
        # logo, say, next to wide device-and-TV renders) would shrink all of
        # them. Padding it back out sideways keeps that one image's own
        # influence in check without touching how any of the others render.
        width, height = image.size
        target_aspect = ASPECT_OVERRIDE.get(name, MIN_ASPECT)
        if width / height < target_aspect:
            padded = Image.new('RGBA', (round(height * target_aspect), height), (0, 0, 0, 0))
            padded.paste(image, ((padded.width - width) // 2, 0), image)
            image = padded
        image.thumbnail((max_size, max_size), Image.LANCZOS)
        image.save(os.path.join(ART_OUT, filename), optimize=True)
        # The panel sizes artwork from its aspect ratio alone (css.py), to keep
        # every console's render clear of the info box regardless of shape.
        mapping[name] = {'file': filename, 'color': color,
                          'width': image.width, 'height': image.height}

    with open(MAP_OUT, 'w') as f:
        json.dump(mapping, f, indent=1, sort_keys=True)

    # A source renamed or removed since the last run otherwise leaves its old
    # output behind forever -- shipped, but unreachable through console-map.json.
    shipped = {entry['file'] for entry in mapping.values()}
    orphans = [f for f in os.listdir(ART_OUT) if f not in shipped and f.lower().endswith('.png')]
    for f in orphans:
        os.remove(os.path.join(ART_OUT, f))

    print('%d images -> %s (max %dpx)' % (len(mapping), ART_OUT, max_size))
    print('%d colors from the source table, %d extracted from the image'
          % (curated_count, len(mapping) - curated_count))
    if orphans:
        print('removed %d orphaned file(s): %s' % (len(orphans), ', '.join(orphans)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
