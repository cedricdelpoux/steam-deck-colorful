"""Non-Steam shortcuts from Steam's shortcuts.vdf: library appid -> ROM file.

The appid stored in the file (a signed int32) is the one the library UI uses,
which is what ties a highlighted tile back to its ROM.
"""
import glob
import os
import re
import struct

VDF_GLOB = os.path.expanduser('~/.local/share/Steam/userdata/*/config/shortcuts.vdf')
ROM_EXT = 'iso|gcm|rvz|wbfs|ciso|chd|cue|bin|zip|7z|z64|v64|n64|md|gen|smd|sfc|smc|nes|gba|gbc|gb|pbp|m3u'


def _cstr(buf, i):
    end = buf.index(b'\x00', i)
    return buf[i:end].decode('utf-8', 'replace'), end + 1


def _map(buf, i):
    """Binary VDF: 0x00 nested map, 0x01 string, 0x02 int32, 0x08 end of map."""
    out = {}
    while i < len(buf):
        t = buf[i]
        if t == 0x08:
            return out, i + 1
        key, i = _cstr(buf, i + 1)
        if t == 0x00:
            val, i = _map(buf, i)
        elif t == 0x01:
            val, i = _cstr(buf, i)
        elif t == 0x02:
            val = struct.unpack_from('<i', buf, i)[0]
            i += 4
        else:
            return out, i
        out[key.lower()] = val
    return out, i


def load(path=None):
    """Empty when Steam has no userdata yet (fresh install)."""
    if not path:
        matches = sorted(glob.glob(VDF_GLOB))
        if not matches:
            return []
        path = matches[0]
    with open(path, 'rb') as f:
        root, _ = _map(f.read(), 0)
    out = []
    for sc in root.get('shortcuts', {}).values():
        cmd = sc.get('exe', '') + ' ' + sc.get('launchoptions', '')
        roms = re.findall(r'"([^"]+\.(?:%s))"' % ROM_EXT, cmd, re.I)
        out.append({'appid': sc.get('appid', 0) & 0xFFFFFFFF,
                    'name': sc.get('appname', ''),
                    'rom': roms[-1] if roms else None})
    return out


if __name__ == '__main__':
    for sc in load():
        print('%10d  %-40s %s' % (sc['appid'], sc['name'][:40], sc['rom'] or '-'))
