# Developing Colorful

This covers the codebase itself — how it's laid out and how the pieces fit
together. For installing and using the plugin, see the main [README](../README.md).

## Repo layout

```
plugin/           the actual Decky plugin -- this is what gets installed
  main.py         backend entry point (a Decky "Plugin" class)
  py_modules/     everything main.py imports -- one file per concern (see table below)
  assets/         shipped as-is: panel.js, and assets/consoles/ (the built artwork)
  src/index.tsx   the settings sheet's React UI, compiled to plugin/dist/ by rollup
assets/           NOT in the repo -- raw 2160x2160 source renders that
                  tools/build_assets.py downscales into plugin/assets/consoles/
install.sh        stages plugin/ onto the Deck and restarts the plugin loader
```

## How it fits together

The library UI lives in Steam's **Big Picture** page, which a Decky plugin
cannot reach from its own frontend (that runs in SharedJSContext). So the
backend does the work and injects into that page over the CEF debugger on
`127.0.0.1:8080`, the same way CSS Loader does:

| piece | role |
| --- | --- |
| `main.py` | ties it together; watchdog re-injects when Steam restarts |
| `py_modules/cdp.py` | the injection itself (style tag + panel script) |
| `py_modules/watchfile.py` | inotify wrapper -- picks up TabMaster changes instantly |
| `py_modules/tabmaster.py` | reads TabMaster's tabs, matches each to artwork |
| `py_modules/console.py` | resolves artwork + color per tab |
| `py_modules/css.py` | generates the stylesheet (panel, tab strip, grid offset) |
| `py_modules/steamui.py` | symlinks the artwork under steamloopback.host |
| `assets/panel.js` | the info box, running inside the library page |
| `src/index.tsx` | settings sheet in the Decky menu |

Per-game data (the info box's numbers) is its own small pipeline, orchestrated
by `py_modules/gamedata.py`: `shortcuts.py` and `playtime.py` read Steam's own
files, `rom_region.py` (with `psx.py` for the CD-based case) reads the ROM's
header, `saves.py` finds the newest save/state, `rahash.py` computes the
RetroAchievements hash, and `ra_api.py` calls their web API with it.

Two details worth remembering:

- **Artwork is served, not inlined.** Anything symlinked into Steam's `steamui`
  folder is reachable from the page as a root-relative URL. Inlining the PNGs as
  `data:` URIs also works and is the fallback, but costs ~350 KB of stylesheet
  per visible tab against ~6 KB for the whole thing.
- **RetroAchievements identifies games by ROM hash, never by title** (the
  rcheevos algorithms are ported in `py_modules/rahash.py`), because the same
  game can be present as several dumps.

## Building and installing from source

Once Colorful is listed on the Decky store, that's the normal way to install
it — this is only for building and deploying straight from a checkout.

```bash
cd plugin && npm install && npm run build
cd .. && ./install.sh              # or ./install.sh deck@<ip>
```

`~/homebrew/plugins` is root-owned, so the script stages the files in the deck
user's home and moves them in with sudo, then restarts `plugin_loader.service`.

**`plugin/package.json` must ship to the Deck.** Decky Loader reads that file's
`"type": "module"` field to decide how to load the bundle: present it picks
`ESMODULE_V1` (`import()`, which understands `export`); absent it silently
falls back to `LEGACY_EVAL_IIFE` (`eval()`, which throws `SyntaxError:
Unexpected token 'export'` on our rollup output). It's fine to exclude
`package-lock.json`, `rollup.config.js`, `tsconfig.json`, `node_modules`,
`src`, and `tools` from the deploy — none of those are read at runtime — but
never exclude `package.json` itself.

## Building the artwork

`plugin/assets/consoles/` is generated, not edited by hand. The raw source
renders (from the COLORFUL theme, see the README's credits) are not in this
repo; download them from the theme's page into `assets/` first:

```bash
python3 plugin/tools/build_assets.py assets/hardware-set-source assets/extra-source
```

It trims the transparent margins, downscales to 800 px (299 MB → 54 MB) and
writes `console-map.json` with a color per console — the source theme's own
color when the name resolves in `colors.json`, otherwise the dominant
saturated color of the render itself.

## Preview harness

`preview/` is a Vite/React sandbox that mocks Steam's library DOM (same
obfuscated classes `css.py`/`panel.js` target) so the look can be iterated on
in a browser instead of redeploying to the Deck for every change. It imports
the real `plugin/assets/panel.js` and the shared `plugin/assets/panel-structure.css`
template raw, so a validated change there carries over to production as-is;
only the per-tab CSS generation (`buildPanelCss.ts`) is a hand-kept TypeScript
port of `css.py`, since the two pull tab data from different places. See
`preview/README.md` for how to run it.
