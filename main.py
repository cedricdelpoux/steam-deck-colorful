"""Colorful -- console artwork and per-game info beside the library grid.

Everything visible lives in Steam's Big Picture page, which this plugin cannot
touch from its own frontend (that runs in SharedJSContext). So the backend owns
the whole look: it resolves the tabs, builds a stylesheet and the info panel
script, and pushes both in over the CEF debugger.

That injection dies with every Steam restart, so a watchdog keeps checking it is
still there and puts it back. The frontend is only a settings sheet.
"""
import asyncio
import base64
import json
import os
from urllib.parse import quote

import decky

import cdp
import console
import css
import gamedata
import playtime
import steamui
import tabmaster
from ra_api import RA
import watchfile

SETTINGS_FILE = os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, 'settings.json')
HASH_CACHE = os.path.join(decky.DECKY_PLUGIN_RUNTIME_DIR, 'rom-hashes.json')
RA_CACHE = os.path.join(decky.DECKY_PLUGIN_RUNTIME_DIR, 'ra')
PANEL_JS = os.path.join(decky.DECKY_PLUGIN_DIR, 'assets', 'panel.js')

DEFAULTS = {
    'enabled': True,
    'show_counts': True,
    'inline_images': False,   # data: URIs instead of steamloopback.host URLs
    'theme': 'dark',          # 'dark' veils the console color with black, 'light' with white
    'ra_key': '',
    'ra_user': '',
    'overrides': {},          # tab id -> {'artwork': name|'', 'color': '#rrggbb'}
}

WATCHDOG_SECONDS = 15   # a CEF round trip, so kept coarse
# A session ending refreshes instantly (see playtime_watch_task below), so
# this is only the fallback for whatever that watch doesn't cover -- the
# inotify setup failing, or a still-running game's mid-session save.
REFRESH_SECONDS = 1800


class Plugin:

    # ---------- lifecycle ----------

    async def _main(self):
        self.settings = _load_settings()
        self.data = {}
        self.tabs = []
        self.art_base_url = None
        self.last_error = None
        self.rebuilding = asyncio.Lock()   # the settings sheet and the watchdog share it
        try:
            with open(PANEL_JS) as f:
                self.script = f.read()
        except OSError as e:
            self.script, self.last_error = None, str(e)
            decky.logger.error('panel.js unreadable: %s', e)

        self.loop_task = asyncio.create_task(self._watch())
        # Real-time instead of polled: a tab added/renamed/reordered in
        # TabMaster shows up within milliseconds, not on the next 15s tick.
        self.tabs_watch_task = asyncio.create_task(
            watchfile.watch(tabmaster.SETTINGS, self._restyle))

        # Same idea for playtime: Steam (re)writes localconfig.vdf right as a
        # shortcut's process exits, which is exactly when a game's playtime,
        # saves and achievement progress are worth re-reading -- instead of
        # waiting on REFRESH_SECONDS. None when Steam has no userdata yet
        # (fresh install); the periodic fallback still covers that case.
        playtime_path = playtime.path()
        self.playtime_watch_task = (
            asyncio.create_task(watchfile.watch(playtime_path, self._on_playtime_change))
            if playtime_path else None)

    async def _unload(self):
        tasks = [self.loop_task, self.tabs_watch_task]
        if self.playtime_watch_task:
            tasks.append(self.playtime_watch_task)
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await asyncio.wait_for(task, timeout=0.5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        try:
            # Best-effort, and kept well under the loader's ~5s SIGKILL patience
            # (1+2=3s): the next load's injection overwrites the same element
            # ids anyway, so a slow CEF round trip here need not hold things up.
            await asyncio.wait_for(self._teardown(), timeout=2)
        except asyncio.TimeoutError:
            decky.logger.warning('teardown timed out, leaving injection in place')

    async def _uninstall(self):
        steamui.unpublish()

    # ---------- the loop ----------

    async def _watch(self):
        """Keep the injection alive and the data reasonably fresh.

        TabMaster changes are handled separately (see tabs_watch_task in
        _main) -- this loop only covers what has no event to listen for:
        Steam restarting, and the slow ROM/RA data going stale.
        """
        await self._rebuild(rehash=False)
        since_refresh = 0
        while True:
            try:
                await asyncio.sleep(WATCHDOG_SECONDS)
                since_refresh += WATCHDOG_SECONDS
                if not self.settings['enabled']:
                    continue
                if since_refresh >= REFRESH_SECONDS:
                    since_refresh = 0
                    await self._rebuild(rehash=False)
                elif not await cdp.is_panel_alive():
                    # Steam restarted (or we never landed): put everything back.
                    await self._inject()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.last_error = str(e)
                decky.logger.exception('console panel loop: %s', e)

    async def _restyle(self):
        """Re-resolve tabs and push new CSS, without touching game data.

        Called from watchfile.watch() the instant TabMaster's settings.json
        changes -- positions and colors are cheap to recompute, so this
        doesn't wait for the slow (ROM-hashing, RA API) cycle above.
        """
        if not self.settings['enabled']:
            return
        async with self.rebuilding:
            self.tabs = console.resolve(self.settings['overrides'])
            await self._inject(with_script=False)

    async def _on_playtime_change(self):
        """Called from watchfile.watch() the instant Steam rewrites
        localconfig.vdf -- almost always a shortcut's process just exited, so
        the info box's playtime/saves/achievements are worth re-reading now
        rather than on the next periodic tick."""
        if not self.settings['enabled']:
            return
        await self._rebuild(rehash=False)

    async def _rebuild(self, rehash=False):
        """Re-read tabs and game data, then push the result to the UI."""
        async with self.rebuilding:
            if rehash:
                _remove(HASH_CACHE)

            self.tabs = console.resolve(self.settings['overrides'])
            self.art_base_url = None
            if not self.settings['inline_images']:
                published = steamui.publish(console.ASSETS)
                if published:
                    self.art_base_url = published + '/consoles'

            # Styling is cheap and gives the panel straight away; the data behind
            # the info box needs ROM hashes and the RA API, so it comes after.
            await self._inject(with_script=False)

            games = await asyncio.get_event_loop().run_in_executor(None, self._build_data)
            if games is not None:   # None means the build failed; {} is a legitimate "no games"
                self.data = games
            # A plain data refresh doesn't need the script re-run -- that tears
            # panel.js's own box down and rebuilds it (see push_data()'s
            # docstring). Only fall back to the full injection when nothing is
            # running yet to receive the lightweight update.
            if not await cdp.is_panel_alive() or not await cdp.push_data(self._payload()):
                await self._inject()

    def _build_data(self):
        """Blocking: reads ROMs and calls the RA API. None when it fell over,
        so a failed refresh leaves the last good data on screen."""
        try:
            return gamedata.build(HASH_CACHE, self.settings['ra_key'] or None,
                                  self.settings['ra_user'] or None, RA_CACHE)
        except Exception as e:
            self.last_error = str(e)
            decky.logger.exception('game data: %s', e)
            return None

    def _payload(self):
        return {'games': self.data, 'tabs': _tabs_meta(self.tabs, self.art_base_url)}

    async def _inject(self, with_script=True):
        """Push the current look into the UI; never fatal, the watchdog retries."""
        if not self.settings['enabled']:
            return False
        stylesheet = css.build(self.tabs,
                               show_counts=self.settings['show_counts'],
                               theme=self.settings['theme'])
        script = self.script if with_script else None
        payload = self._payload() if with_script else None
        try:
            landed = await cdp.apply(stylesheet, script, payload)
        except Exception as e:
            self.last_error = str(e)
            decky.logger.warning('injection failed: %s', e)
            return False
        self.last_error = None if landed else 'Big Picture not running'
        return landed

    async def _teardown(self):
        """Take the panel back off screen, leaving the library as Steam draws it."""
        try:
            await cdp.apply('', 'window.%s && window.%s.stop();' % (
                cdp.SCRIPT_MARKER, cdp.SCRIPT_MARKER))
        except Exception as e:
            decky.logger.warning('teardown: %s', e)
        self.last_error = None

    # ---------- frontend API ----------

    async def get_state(self):
        """Everything the settings sheet shows in one round trip."""
        return {
            'settings': self.settings,
            'tabs': self.tabs,
            'consoles': sorted(console.catalog()),
            'games': len(self.data),
            'linked': bool(self.art_base_url),
            'error': self.last_error,
        }

    async def verify_ra(self):
        """Check the stored RetroAchievements credentials; the settings
        sheet's "Connect" button shows the resulting profile (or error)."""
        user, key = self.settings['ra_user'], self.settings['ra_key']
        if not user or not key:
            return {'ok': False, 'error': 'Username and API key are required'}
        return await asyncio.get_event_loop().run_in_executor(
            None, RA(key, user).verify_profile)

    async def set_settings(self, patch):
        """Merge a change from the settings sheet and apply it live."""
        self.settings.update(patch)
        _save_settings(self.settings)
        if self.settings['enabled']:
            await self._rebuild(rehash=False)
        else:
            await self._teardown()
        return await self.get_state()

    async def set_override(self, tab_id, artwork=None, color=None):
        """Pin one tab's artwork and/or color; None on both clears the override.

        `artwork` is a console name as listed by get_state, or '' for no panel.
        """
        overrides = dict(self.settings['overrides'])
        if artwork is None and color is None:
            overrides.pop(tab_id, None)
        else:
            entry = dict(overrides.get(tab_id, {}))
            if artwork is not None:
                entry['artwork'] = _artwork_file(artwork)
            if color is not None:
                entry['color'] = color
            overrides[tab_id] = entry
        return await self.set_settings({'overrides': overrides})

    async def refresh(self, rehash=False):
        """Rebuild now; `rehash` also throws away the cached ROM hashes."""
        await self._rebuild(rehash=rehash)
        return await self.get_state()


def _artwork_url(artwork, art_base_url):
    """URL (or inline data: URI, when the plugin dir isn't published) for a
    tab's artwork <img> -- see panel.js's ensureArt()/syncArt(). None if the
    tab has no artwork file at all."""
    if not artwork:
        return None
    path = os.path.join(console.ART_DIR, artwork)
    if not os.path.isfile(path):
        return None
    if art_base_url:
        return art_base_url.rstrip('/') + '/' + quote(artwork)
    with open(path, 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode('ascii')


def _tabs_meta(tabs, art_base_url):
    """Per-tab info panel.js needs for its "no game selected" fallback and for
    the artwork <img> itself: the Steam collection name(s) to pull live
    playtime from, whatever vendor/year the source theme has for that
    console, and the artwork URL. Position-keyed so the script can match it
    to whichever tab is actually selected in the DOM."""
    out = []
    for tab in tabs:
        if not tab.get('color'):
            continue
        name = os.path.splitext(tab['artwork'])[0] if tab.get('artwork') else tab['title']
        meta = console.meta_for(name)
        out.append({
            'position': tab['position'],
            'name': name,
            'collections': tab.get('collections') or [],
            'vendor': meta.get('vendor'),
            'year': meta.get('year'),
            'artwork': _artwork_url(tab.get('artwork'), art_base_url),
        })
    return out


def _load_settings():
    settings = dict(DEFAULTS)
    try:
        with open(SETTINGS_FILE) as f:
            stored = json.load(f)
        settings.update({k: v for k, v in stored.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return settings


def _save_settings(settings):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=1)


def _artwork_file(name):
    """Console name -> artwork filename; '' stays '' (meaning: no panel here)."""
    if not name:
        return ''
    entry = console.catalog().get(name)
    return entry['file'] if entry else name


def _remove(path):
    try:
        os.remove(path)
    except OSError:
        pass
