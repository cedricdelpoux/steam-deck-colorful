"""Per-game data for the info panel, keyed by Steam's library appid.

Covers the emulated shortcuts only: region and RetroAchievements status come
from the ROM itself, saves from the emulators' folders, playtime from Steam's
own records. Native Steam games are handled in the frontend instead, since
their achievements only exist behind the live client API.

ROM hashing is the expensive part -- reading whole GameCube ISOs -- so results
are cached against the file's size and mtime and only recomputed when the file
actually changes.
"""
import json
import os

import playtime
import rahash
import rom_region
import saves
import shortcuts
from ra_api import RA


class Cache:
    """Hash results that survive restarts, invalidated by size/mtime."""

    def __init__(self, path):
        self.path = path
        self.data = {}
        try:
            with open(path) as f:
                self.data = json.load(f)
        except (OSError, ValueError):
            pass

    @staticmethod
    def _stamp(rom):
        info = os.stat(rom)
        return '%d:%d' % (info.st_size, int(info.st_mtime))

    def hash_rom(self, rom, system):
        """(console id, md5) for a ROM, hashing only when the file changed."""
        stamp = self._stamp(rom)
        entry = self.data.get(rom)
        if entry and entry.get('stamp') == stamp:
            return entry['console'], entry['md5']
        console, md5 = rahash.hash_rom(rom, system)
        self.data[rom] = {'stamp': stamp, 'console': console, 'md5': md5}
        return console, md5

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump(self.data, f)
        except OSError:
            pass


def _ra_status(ra, progress, console, md5):
    game = ra.hash_index(console).get(md5)
    if not game:
        return {'status': 'unsupported'}
    count = game.get('NumAchievements') or 0
    entry = progress.get(game['ID']) or {}
    return {'status': 'ok' if count else 'pending',
            'id': game['ID'], 'title': game['Title'],
            'awarded': entry.get('NumAwarded', 0), 'total': count}


def build(cache_path, ra_key=None, ra_user=None, ra_cache_dir=None):
    """Everything the panel needs: {appid: {...}}.

    Missing or failing RetroAchievements credentials only drop the achievement
    part; region, saves and playtime are local and always present.
    """
    cache = Cache(cache_path)
    ra_cache_dir = ra_cache_dir or os.path.join(os.path.dirname(cache_path), 'ra')
    ra = RA(ra_key, ra_user, ra_cache_dir) if ra_key and ra_user else None
    progress = {}
    if ra:
        try:
            progress = ra.user_progress()
        except Exception:
            ra = None

    minutes = playtime.load()
    out = {}

    for shortcut in shortcuts.load():
        rom = shortcut['rom']
        if not rom or not os.path.isfile(rom):
            continue
        system = rahash.system_of(rom)
        try:
            info = rom_region.read(rom)
        except Exception:
            info = {}

        # system/rom/romId only steer the lookups below -- the panel itself
        # never reads them back, so they don't need to ride along in entry.
        entry = {
            'region': info.get('region'),
            'playtime': minutes.get(shortcut['appid'], 0),
            'saves': saves.find(system, rom, info),
        }

        if ra and system in rahash.CONSOLE_IDS:
            try:
                console, md5 = cache.hash_rom(rom, system)
                entry['ra'] = _ra_status(ra, progress, console, md5)
            except Exception as e:
                entry['ra'] = {'status': 'error', 'error': str(e)}

        out[str(shortcut['appid'])] = entry

    cache.save()
    return out
