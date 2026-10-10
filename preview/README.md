# Preview

A React/Vite sandbox to iterate on the panel's design in a browser, without
deploying to the Deck.

Requires **Node 22.12 or later**: Linaria's CSS compiler (`oxc-parser` /
`oxc-transform`) crashes on older versions.

```bash
cd preview
npm install
npm run dev
```

Then open <http://localhost:5183> (the port is set in `vite.config.ts`).

## How it works

The mock reproduces just enough of the Big Picture library DOM (the same
obfuscated classes `css.py` and `panel.js` target, see `src/steamSelectors.ts`)
for the production CSS and script to apply unchanged, with fixture data
instead of real Steam/RetroAchievements data.

- `src/fixtures/data.ts`: a Steam tab, a few consoles with a handful of games
  each, and a "Homebrew" tab with no matching console to check that it keeps
  Steam's look.
- `src/LibraryMock.tsx`: the fake page (tab bar and grid), styled with
  [Linaria](https://github.com/callstack/linaria).
- `src/buildPanelCss.ts`: a TypeScript port of the per-tab rules in `css.py`.
  The static rules come from `plugin/assets/panel-structure.css`, shared with
  the Python side.
- `src/panelRuntime.ts`: feeds the fixture data into `window.__cpData` and
  `window.opener.collectionStore`, then runs the real `plugin/assets/panel.js`
  unmodified.

Clicking a game simulates gamepad focus (`.gpfocus`), and the left/right
arrow keys switch tabs like L1/R1.

## Known limitations

- `@oxc-parser/binding-darwin-arm64` and `@oxc-transform/binding-darwin-arm64`
  are pinned in `package.json` to work around an npm bug with
  platform-specific optional dependencies
  (https://github.com/npm/cli/issues/4828). On another platform, replace them
  with the matching binding or remove them and run `npm install` again.
- The browser must support `:has()` (any recent Chrome, Edge or Safari).

## Bringing a design back to the plugin

1. Static rules live in `plugin/assets/panel-structure.css` and need no
   porting. Per-tab rules changed in `buildPanelCss.ts` must be mirrored in
   `plugin/py_modules/css.py`.
2. `plugin/assets/panel.js` is shared as-is.
3. Build and deploy as described in [docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md).
