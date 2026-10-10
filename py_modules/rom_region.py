"""Read the region and internal id straight from a ROM header.

Filenames in this collection carry no region tag, so it has to come from the
file itself. Every format here is uncompressed (WBFS aside), so this only reads
a few bytes -- except PS1, which scans the start of the data track.
"""
import os
import re
import sys

GC_REGION = {'E': 'USA', 'P': 'Europe', 'J': 'Japan', 'U': 'Australia', 'F': 'France',
             'D': 'Germany', 'S': 'Spain', 'I': 'Italy'}
N64_REGION = {'E': 'USA', 'P': 'Europe', 'J': 'Japan', 'F': 'France', 'D': 'Germany',
              'I': 'Italy', 'S': 'Spain', 'U': 'Australia', 'X': 'Europe', 'Y': 'Europe'}
PSX_PREFIX = {'SLES': 'Europe', 'SCES': 'Europe', 'SLUS': 'USA', 'SCUS': 'USA',
              'SLPS': 'Japan', 'SCPS': 'Japan', 'SLPM': 'Japan'}


def _nintendo_disc(head):
    """GameCube and Wii share the disc header layout."""
    code = head[0:4].decode('ascii', 'replace')
    return {'id': code,
            'id6': head[0:6].decode('ascii', 'replace'),   # what Dolphin names states after
            'region': GC_REGION.get(code[3:4], '?'),
            'title': head[0x20:0x60].split(b'\x00')[0].decode('ascii', 'replace').strip()}


def gamecube(path):
    with open(path, 'rb') as f:
        return _nintendo_disc(f.read(0x60))


def wii(path):
    from rahash import Disc, WbfsDisc
    disc = WbfsDisc(path) if path.lower().endswith('.wbfs') else Disc(path)
    try:
        return _nintendo_disc(disc.read_at(0, 0x60))
    finally:
        disc.close()


def n64(path):
    with open(path, 'rb') as f:
        head = f.read(0x40)
    if head[0:4] == b'\x37\x80\x40\x12':    # byteswapped (.v64)
        head = bytes(b for pair in zip(head[1::2], head[0::2]) for b in pair)
    title = head[0x20:0x34].decode('ascii', 'replace').strip()
    return {'id': head[0x3B:0x3E].decode('ascii', 'replace'),
            'region': N64_REGION.get(chr(head[0x3E]), '?'), 'title': title}


def genesis(path):
    with open(path, 'rb') as f:
        head = f.read(0x200)
    if b'SEGA' not in head[0x100:0x110]:
        return {'region': '?', 'title': '(unrecognized header)'}
    title = head[0x120:0x150].decode('ascii', 'replace').strip()
    raw = head[0x1F0:0x1F3].decode('ascii', 'replace').strip('\x00 ')
    regions = {'J': 'Japan', 'U': 'USA', 'E': 'Europe'}
    label = '+'.join(regions.get(c, c) for c in raw if c in regions) or raw
    return {'id': raw, 'region': label, 'title': title}


def psx(path):
    # the serial lives in the data track; scan the first few MB
    with open(path, 'rb') as f:
        chunk = f.read(8 * 1024 * 1024)
    m = re.search(rb'(S[LC][EUP][SM])[_-](\d{3})\.?(\d{2})', chunk)
    if not m:
        return {'region': '?', 'title': '(serial not found)'}
    prefix = m.group(1).decode()
    # same form as DuckStation's save state names: SLES-03324
    serial = '%s-%s%s' % (prefix, m.group(2).decode(), m.group(3).decode())
    return {'id': serial, 'region': PSX_PREFIX.get(prefix, '?'), 'title': ''}


READERS = {'.iso': gamecube, '.gcm': gamecube, '.wbfs': wii,
           '.z64': n64, '.v64': n64, '.n64': n64,
           '.md': genesis, '.gen': genesis, '.smd': genesis}


def read(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.cue':
        with open(path, errors='replace') as f:
            m = re.search(r'FILE\s+"([^"]+)"', f.read())
        target = os.path.join(os.path.dirname(path), m.group(1)) if m else None
        if not target or not os.path.exists(target):
            # cue sheets here sometimes keep a stale name; fall back to the
            # track sitting next to them under the cue's own basename
            target = os.path.splitext(path)[0] + '.bin'
        path, ext = target, '.bin'
    if ext == '.bin':
        # Mega Drive dumps also use .bin; sniff the Sega header first
        with open(path, 'rb') as f:
            probe = f.read(0x200)
        return genesis(path) if b'SEGA' in probe[0x100:0x110] else psx(path)
    if ext == '.iso' and os.path.basename(os.path.dirname(path)).lower() == 'wii':
        return wii(path)
    fn = READERS.get(ext)
    if not fn:
        return {'region': '?', 'title': '(unsupported format)'}
    return fn(path)


if __name__ == '__main__':
    for p in sys.argv[1:]:
        try:
            info = read(p)
            print('%-46s -> region=%-10s id=%-12s %s' % (
                os.path.basename(p)[:46], info.get('region'), info.get('id', ''), info.get('title', '')[:30]))
        except Exception as e:
            print('%-46s -> ERROR %s' % (os.path.basename(p)[:46], e))
