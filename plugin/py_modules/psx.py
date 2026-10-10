"""PlayStation hash for RetroAchievements (rc_hash_psx), over bin/cue images.

Hashes the boot executable's name followed by its contents, locating it via
SYSTEM.CNF in the ISO9660 filesystem of track 1 -- same lookup rules as
rcheevos' rc_cd_find_file_sector.
"""
import hashlib
import os
import re
import struct

MAX_BUFFER_SIZE = 64 * 1024 * 1024
MODES = {  # cue track mode -> (bytes per sector on disk, header before the 2048-byte payload)
    'MODE1/2048': (2048, 0),
    'MODE1/2352': (2352, 16),
    'MODE2/2336': (2336, 8),
    'MODE2/2352': (2352, 24),
}


class Track:
    def __init__(self, path, sector_size, header, base=0):
        self.f = open(path, 'rb')
        self.sector_size = sector_size
        self.header = header
        self.base = base

    def read_sector(self, lba, size=2048):
        self.f.seek(self.base + lba * self.sector_size + self.header)
        return self.f.read(min(size, 2048))

    def close(self):
        self.f.close()


def _frames(msf):
    m, s, f = (int(x) for x in msf.split(':'))
    return (m * 60 + s) * 75 + f


def open_track1(path):
    if os.path.splitext(path)[1].lower() != '.cue':
        size = os.path.getsize(path)
        if size % 2352 == 0:
            with open(path, 'rb') as f:
                f.seek(16 * 2352)
                raw = f.read(16)
            return Track(path, 2352, 24 if len(raw) == 16 and raw[15] == 2 else 16)
        return Track(path, 2048, 0)

    current = track_file = track_mode = None
    index01 = 0
    in_track1 = False
    with open(path, errors='replace') as f:
        for line in f:
            line = line.strip()
            m = re.match(r'FILE\s+"([^"]+)"', line) or re.match(r'FILE\s+(\S+)', line)
            if m:
                current = m.group(1)
                continue
            m = re.match(r'TRACK\s+(\d+)\s+(\S+)', line)
            if m:
                in_track1 = int(m.group(1)) == 1
                if in_track1:
                    track_file, track_mode = current, m.group(2).upper()
                continue
            m = re.match(r'INDEX\s+01\s+(\d+:\d+:\d+)', line)
            if m and in_track1:
                index01 = _frames(m.group(1))

    target = os.path.join(os.path.dirname(path), track_file) if track_file else None
    if not target or not os.path.exists(target):
        # some cue sheets in this collection keep a stale filename;
        # the track sits next to them under the cue's own basename
        target = os.path.splitext(path)[0] + '.bin'
    sector_size, header = MODES.get(track_mode, (2352, 24))
    return Track(target, sector_size, header, index01 * sector_size)


def find_file_sector(track, path):
    """(sector, size) of a file on the disc, or (0, None)."""
    if path.startswith('\\'):
        path = path[1:]
    num_sectors = 0
    if '\\' in path:
        directory, _, path = path.rpartition('\\')
        sector, _ = find_file_sector(track, directory)
        if not sector:
            return 0, None
    else:
        pvd = track.read_sector(16, 256)
        if len(pvd) < 256:
            return 0, None
        sector = pvd[158] | (pvd[159] << 8) | (pvd[160] << 16)
        block = pvd[128] | (pvd[129] << 8)
        num_sectors = 1 if block == 0 else struct.unpack_from('<I', pvd, 166)[0] // block

    name = path.encode('latin-1')
    n = len(name)
    buf = track.read_sector(sector)
    if not buf:
        return 0, None
    buf = buf.ljust(2048, b'\x00')
    i = 0
    while True:
        if i >= 2048 or buf[i] == 0:
            if num_sectors > 1:
                num_sectors -= 1
                sector += 1
                nxt = track.read_sector(sector)
                if nxt:
                    buf, i = nxt.ljust(2048, b'\x00'), 0
                    continue
            return 0, None
        # record name sits 33 bytes in: "FILENAME;version" or "DIRECTORY"
        name_len = buf[i + 32] if i + 32 < 2048 else 0
        after = buf[i + 33 + n] if i + 33 + n < 2048 else 0
        if (name_len == n or after == ord(';')) and buf[i + 33:i + 33 + n].lower() == name.lower():
            found = buf[i + 2] | (buf[i + 3] << 8) | (buf[i + 4] << 16)
            return found, struct.unpack_from('<I', buf, i + 10)[0]
        i += buf[i]


def _boot_name(cnf):
    for line in cnf.split('\n'):
        if not line.startswith('BOOT'):
            continue
        rest = line[4:].lstrip()
        if not rest.startswith('='):
            continue
        rest = rest[1:].lstrip()
        if rest.startswith('cdrom:'):
            rest = rest[6:]
        rest = rest.lstrip('\\')
        return re.match(r'[^\s;]*', rest).group(0)[:63]
    return None


def hash_psx(path):
    track = open_track1(path)
    try:
        exe_name, sector, size = None, 0, None
        cnf_sector, _ = find_file_sector(track, 'SYSTEM.CNF')
        if cnf_sector:
            cnf = track.read_sector(cnf_sector, 2047).split(b'\x00')[0].decode('latin-1')
            boot = _boot_name(cnf)
            if boot:
                exe_name = boot
                sector, size = find_file_sector(track, boot)
        if not sector:
            sector, size = find_file_sector(track, 'PSX.EXE')
            if sector:
                exe_name = 'PSX.EXE'
        if not sector:
            raise ValueError('boot executable not found')

        head = track.read_sector(sector, 32)
        if len(head) < 32:
            raise ValueError('could not read boot executable')
        if head[:7] == b'PS-X EX':
            # header size field excludes the 2048-byte header itself, which RA hashes too
            size = struct.unpack_from('<I', head, 28)[0] + 2048

        md5 = hashlib.md5(exe_name.encode('latin-1'))
        size = min(size, MAX_BUFFER_SIZE)
        while size > 0:
            data = track.read_sector(sector, min(size, 2048))
            if not data:
                break
            md5.update(data[:size])
            size -= len(data)
            sector += 1
        return md5.hexdigest()
    finally:
        track.close()
