"""Date of the most recent save or save state of a ROM, following each
emulator's naming.

Paths are EmuDeck's; on this Deck they are symlinks into Dropbox. Why each
emulator names things its own way is documented in Dropbox/Games/README.md.
"""
import glob
import os

EMU_SAVES = os.path.expanduser('~/Emulation/saves')
DOLPHIN = os.path.expanduser('~/.var/app/org.DolphinEmu.dolphin-emu/data/dolphin-emu')
# Dolphin picks the memory card folder from the disc's region letter
GC_CARD = {'P': 'EUR', 'E': 'USA', 'J': 'JAP'}


def _mtimes(pattern):
    return [os.path.getmtime(p) for p in glob.glob(pattern)
            if os.path.isfile(p) and not p.endswith('.png')]   # RetroArch state thumbnails


def find(system, rom, info):
    """{'latest': {'mtime': ...} | None} -- only the date is ever needed by
    the panel, not which file it came from or how many others exist."""
    base = glob.escape(os.path.splitext(os.path.basename(rom))[0])
    gid = info.get('id') or ''
    mtimes = []

    if system in ('genesis', 'megadrive', 'n64'):
        # RetroArch: one folder per core, files named after the ROM
        mtimes += _mtimes(os.path.join(EMU_SAVES, 'retroarch', 'states', '*', base + '.state*'))
        mtimes += _mtimes(os.path.join(EMU_SAVES, 'retroarch', 'saves', '*', base + '.srm'))

    elif system == 'psx':
        # DuckStation: states named after the serial, memory cards after the ROM
        if gid:
            mtimes += _mtimes(os.path.join(EMU_SAVES, 'duckstation', 'states', glob.escape(gid) + '_*.sav'))
        mtimes += _mtimes(os.path.join(EMU_SAVES, 'duckstation', 'saves', base + '_*.mcd'))

    elif system in ('gc', 'gamecube', 'wii'):
        if system == 'wii':
            # a Wii save is a folder of files in the NAND; any of them dates it
            if gid:
                mtimes += _mtimes(os.path.join(DOLPHIN, 'Wii', 'title', '00010000',
                                               gid.encode().hex(), 'data', '*'))
        else:
            card = GC_CARD.get(gid[3:4])
            if card:
                mtimes += _mtimes(os.path.join(DOLPHIN, 'GC', card, 'Card A',
                                               '*-%s-*.gci' % glob.escape(gid)))
        if info.get('id6'):
            mtimes += _mtimes(os.path.join(DOLPHIN, 'StateSaves',
                                           glob.escape(info['id6']) + '.s[0-9]*'))

    return {'latest': {'mtime': int(max(mtimes))} if mtimes else None}
