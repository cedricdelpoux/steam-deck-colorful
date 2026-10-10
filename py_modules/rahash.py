"""RetroAchievements ROM hashes, ported from rcheevos (src/rhash) for the
systems in this collection.

RA identifies a ROM by an exact MD5, so this reproduces the reference
byte for byte -- quirks included.
"""
import array
import hashlib
import os
import struct

CONSOLE_IDS = {'genesis': 1, 'megadrive': 1, 'n64': 2, 'psx': 12,
               'gc': 16, 'gamecube': 16, 'wii': 19}
CHUNK = 1024 * 1024


# ---------------------------------------------------------------- disc access

class Disc:
    """Random access over a plain disc image."""

    def __init__(self, path):
        self.f = open(path, 'rb')

    def read_at(self, offset, size):
        self.f.seek(offset)
        data = self.f.read(size)
        return data + bytes(size - len(data))

    def close(self):
        self.f.close()


class WbfsDisc(Disc):
    """Virtual Wii disc over a single-disc .wbfs container (libwbfs layout)."""

    WII_SECTORS_PER_DISC = 143432 * 2   # dual layer, 0x8000-byte Wii sectors

    def __init__(self, path):
        super().__init__(path)
        head = self.f.read(12)
        if head[:4] != b'WBFS':
            raise ValueError('not a WBFS file')
        hd_sec_sz = 1 << head[8]
        self.shift = head[9]
        self.sec_sz = 1 << self.shift
        count = self.WII_SECTORS_PER_DISC >> (self.shift - 15)
        # disc slot 0: a 0x100-byte header copy, then one big-endian u16 per wbfs sector
        self.f.seek(hd_sec_sz + 0x100)
        self.wlba = struct.unpack('>%dH' % count, self.f.read(count * 2))

    def read_at(self, offset, size):
        out = bytearray()
        while size > 0:
            idx = offset >> self.shift
            within = offset & (self.sec_sz - 1)
            n = min(size, self.sec_sz - within)
            lba = self.wlba[idx] if idx < len(self.wlba) else 0
            if lba:
                self.f.seek((lba << self.shift) + within)
                chunk = self.f.read(n)
                out += chunk + bytes(n - len(chunk))
            else:
                out += bytes(n)   # sector not stored in the container
            offset += n
            size -= n
        return bytes(out)


def _append(md5, disc, offset, size):
    while size > 0:
        n = min(size, CHUNK)
        md5.update(disc.read_at(offset, n))
        offset += n
        size -= n


# ---------------------------------------------------------------- cartridges

def _whole_file(path):
    md5 = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(CHUNK), b''):
            md5.update(chunk)
    return md5.hexdigest()


def _n64(path):
    with open(path, 'rb') as f:
        buf = bytearray(f.read())
    magic = bytes(buf[:4])
    if magic == b'\x37\x80\x40\x12':        # .v64, 16-bit byteswapped
        buf[0::2], buf[1::2] = buf[1::2], buf[0::2]
    elif magic == b'\x40\x12\x37\x80':      # .n64, little-endian words
        words = array.array('I', bytes(buf))
        words.byteswap()
        buf = bytearray(words.tobytes())
    return hashlib.md5(buf).hexdigest()


# ---------------------------------------------------------------- Nintendo discs

def _nintendo_partition(md5, disc, part_offset, shift):
    """Header + apploader, then the 18 main.dol segments (rc_hash_nintendo_disc_partition)."""
    body, trailer = struct.unpack('>II', disc.read_at(part_offset + 0x2440 + 0x14, 8))
    header_size = min(0x2440 + 0x20 + body + trailer, 1024 * 1024)
    header = disc.read_at(part_offset, header_size)
    md5.update(header)

    dol_offset = struct.unpack_from('>I', header, 0x420)[0] << shift
    table = disc.read_at(part_offset + dol_offset, 0xD8)
    for ix in range(18):
        off = struct.unpack_from('>I', table, ix * 4)[0] << shift
        size = struct.unpack_from('>I', table, 0x90 + ix * 4)[0] << shift
        if size:
            _append(md5, disc, part_offset + off, size)


def _gamecube(path):
    disc = Disc(path)
    try:
        if disc.read_at(0x1C, 4) != b'\xC2\x33\x9F\x3D':
            raise ValueError('not a GameCube disc')
        md5 = hashlib.md5()
        _nintendo_partition(md5, disc, 0, 0)
        return md5.hexdigest()
    finally:
        disc.close()


def _wii(path):
    disc = WbfsDisc(path) if path.lower().endswith('.wbfs') else Disc(path)
    try:
        if disc.read_at(0x18, 4) != b'\x5D\x1C\x9E\xA3':
            raise ValueError('not a Wii disc (WiiWare is not supported)')
        md5 = hashlib.md5()
        encrypted = disc.read_at(0x61, 1)[0] == 0

        md5.update(disc.read_at(0, 0x80))        # main header
        md5.update(disc.read_at(0x4E000, 4))     # region code

        info = struct.unpack('>8I', disc.read_at(0x40000, 32))
        parts = []
        for jx in range(0, 8, 2):
            count, table = info[jx], info[jx + 1] << 2
            raw = disc.read_at(table, count * 8)
            parts += [struct.unpack_from('>II', raw, i * 8) for i in range(count)]
        if not parts:
            raise ValueError('no partitions found')

        for poff, ptype in parts:
            if ptype == 1:                        # update partition
                continue
            base = poff << 2
            tmd_size, tmd_off = struct.unpack('>II', disc.read_at(base + 0x2A4, 8))
            md5.update(disc.read_at(base + (tmd_off << 2), min(tmd_size, 0x7C00)))

            data_off, data_size = struct.unpack('>II', disc.read_at(base + 0x2B8, 8))
            data_off <<= 2
            data_size <<= 2
            # rcheevos uses this data offset as absolute, without adding the
            # partition base. Kept as is: RA's hash database was built that way.
            if encrypted:
                for ix in range(min(data_size // 0x8000, 1024)):
                    md5.update(disc.read_at(data_off + ix * 0x8000 + 0x400, 0x7C00))
            else:
                _nintendo_partition(md5, disc, data_off & 0xFFFFFFFF, 2)
        return md5.hexdigest()
    finally:
        disc.close()


# ---------------------------------------------------------------- PlayStation

def _psx(path):
    from psx import hash_psx  # the CD / ISO9660 reader lives in its own module
    return hash_psx(path)


# ---------------------------------------------------------------- entry point

def system_of(path):
    """EmuDeck keeps one folder per system; the folder name tells which one."""
    return os.path.basename(os.path.dirname(os.path.abspath(path))).lower()


def hash_rom(path, system=None):
    """Return (ra_console_id, md5 hex) for a ROM."""
    system = system or system_of(path)
    console = CONSOLE_IDS.get(system)
    if console is None:
        raise ValueError('unsupported system: %s' % system)
    fn = {1: _whole_file, 2: _n64, 12: _psx, 16: _gamecube, 19: _wii}[console]
    return console, fn(path)
