"""Inject CSS and JS into Steam's Big Picture UI over the CEF debugger.

A Decky plugin's own frontend runs in SharedJSContext, which does not hold the
library DOM -- that lives in the "Steam Big Picture Mode" target. So styling and
the info panel are injected from here instead, the same way CSS Loader does it.

The connection drops whenever Steam restarts, so callers are expected to keep
calling apply(); it reconnects and re-injects on its own.
"""
import asyncio
import json
import os
import re

import aiohttp

import decky

CEF_URL = 'http://127.0.0.1:8080/json/list'
TARGET_TITLE = 'Steam Big Picture Mode'

# Namespaced by this plugin's own install folder name (== the "name" from its
# plugin.json, since that's what install.sh / deck-install-remote.sh name the
# ~/homebrew/plugins/<name> folder after) so two installs built from the same
# code (e.g. a redesign staged side by side with the original, both targeting
# the exact same Steam DOM) never collide: without this, both shared the same
# <style> tag id and the same window.__consolePanel marker, so disabling one
# plugin's `_teardown()` blanked the *other's* stylesheet too and called
# `.stop()` on whichever instance's script happened to be the live one --
# tearing down both from a single plugin's own settings toggle. Built from
# DECKY_PLUGIN_DIR rather than a hypothetical DECKY_PLUGIN_NAME constant,
# since DECKY_PLUGIN_DIR is already relied on elsewhere in this codebase and
# confirmed to exist.
_SLUG = re.sub(r'[^a-z0-9]+', '-', os.path.basename(decky.DECKY_PLUGIN_DIR).lower()).strip('-') or 'console-panel'
STYLE_ID = 'console-panel-style-%s' % _SLUG
INFO_ID = 'cp-info-box-%s' % _SLUG
ART_ID = 'cp-art-%s' % _SLUG
SCRIPT_MARKER = '__consolePanel_%s' % _SLUG.replace('-', '_')


def _style_js(css):
    """JS that creates/updates a single <style> tag, so re-injecting is idempotent."""
    return (
        "(() => {"
        f"  let el = document.getElementById({json.dumps(STYLE_ID)});"
        "   if (!el) {"
        "     el = document.createElement('style');"
        f"    el.id = {json.dumps(STYLE_ID)};"
        "     document.head.appendChild(el);"
        "   }"
        f"  el.textContent = {json.dumps(css)};"
        "   return 'ok';"
        "})()"
    )


async def _find_target(session):
    async with session.get(CEF_URL, timeout=aiohttp.ClientTimeout(total=5)) as r:
        for target in await r.json():
            if target.get('title') == TARGET_TITLE:
                return target
    return None


async def _evaluate(session, target, expression):
    async with session.ws_connect(target['webSocketDebuggerUrl'], max_msg_size=0) as ws:
        await ws.send_json({'id': 1, 'method': 'Runtime.evaluate',
                            'params': {'expression': expression,
                                       'returnByValue': True, 'awaitPromise': True}})
        while True:
            msg = await asyncio.wait_for(ws.receive_json(), timeout=15)
            if msg.get('id') == 1:
                if 'exceptionDetails' in msg.get('result', {}):
                    raise RuntimeError(json.dumps(msg['result']['exceptionDetails'])[:400])
                return msg['result'].get('result', {}).get('value')


async def apply(css, script=None, data=None):
    """Push CSS (and optionally the panel script + its data) into the library UI.

    Returns True once the injection landed, False when Big Picture isn't up yet.
    """
    async with aiohttp.ClientSession() as session:
        target = await _find_target(session)
        if not target:
            return False

        await _evaluate(session, target, _style_js(css))

        if script is not None:
            # panel.js reads its own ids/marker off this instead of having
            # them hardcoded -- see the comment by SCRIPT_MARKER above.
            namespace = 'window.__cpNamespace = %s;\n' % json.dumps(
                {'infoId': INFO_ID, 'artId': ART_ID, 'marker': SCRIPT_MARKER})
            payload = namespace
            if data is not None:
                payload += 'window.__cpData = %s;\n' % json.dumps(data)
            await _evaluate(session, target, payload + script)
        return True


async def push_data(data):
    """Update window.__cpData on the already-running instance and ask it to
    refresh in place, without touching the <style> tag or re-running the
    script.

    Routine data refreshes (playtime, RetroAchievements progress) used to go
    through apply() with a script, which re-runs panel.js's own teardown
    (window[MARKER].stop()) and rebuilds the info box from scratch -- visibly
    tearing it down and back up on every refresh instead of just updating the
    numbers in it.

    Returns False (not just when unreachable, but also when the live script
    predates .refresh() -- e.g. right after deploying a change here, since a
    backend restart alone never reloads the Steam page a stale script is
    still running in) so callers fall back to apply() instead of silently
    updating window.__cpData for nothing. Check is_panel_alive() first too;
    apply() is also what sets window.__cpNamespace in the first place.
    """
    async with aiohttp.ClientSession() as session:
        target = await _find_target(session)
        if not target:
            return False
        payload = (
            'window.__cpData = %s;\n'
            "(() => { const ns = window.__cpNamespace; const inst = ns && window[ns.marker];"
            " if (inst && inst.refresh) { inst.refresh(); return true; } return false; })();"
        ) % json.dumps(data)
        return bool(await _evaluate(session, target, payload))


async def is_panel_alive():
    """True when the injected script is still present (it dies on a Steam restart)."""
    async with aiohttp.ClientSession() as session:
        target = await _find_target(session)
        if not target:
            return False
        try:
            return bool(await _evaluate(
                session, target, "typeof window.%s !== 'undefined'" % SCRIPT_MARKER))
        except Exception:
            return False
