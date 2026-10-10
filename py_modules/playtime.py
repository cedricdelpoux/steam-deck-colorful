"""Playtime Steam records for non-Steam shortcuts.

The library overview reports 0 minutes for shortcuts; the real counter lives in
localconfig.vdf, keyed by the shortcut's appid written as a signed int32.
"""
import glob
import os
import re

VDF_GLOB = os.path.expanduser('~/.local/share/Steam/userdata/*/config/localconfig.vdf')


def path():
    """The resolved localconfig.vdf path, or None if Steam has no userdata yet.

    Steam rewrites this file's Playtime fields right as a non-Steam shortcut's
    process exits -- watching it is a reliable "a game session just ended"
    signal, cheaper and far more precise than polling on a timer.
    """
    matches = sorted(glob.glob(VDF_GLOB))
    return matches[0] if matches else None


def load(vdf_path=None):
    """appid (unsigned, as the library uses it) -> minutes played; empty when
    Steam has no userdata yet (fresh install)."""
    vdf_path = vdf_path or path()
    if not vdf_path:
        return {}
    with open(vdf_path, encoding='utf-8', errors='replace') as f:
        text = f.read()
    out = {}
    for m in re.finditer(r'"(-?\d+)"\s*\{([^{}]*)\}', text):
        pt = re.search(r'"Playtime"\s*"(\d+)"', m.group(2))
        if pt:
            out[int(m.group(1)) & 0xFFFFFFFF] = int(pt.group(1))
    return out
