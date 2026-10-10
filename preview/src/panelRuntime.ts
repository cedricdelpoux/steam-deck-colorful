// Feeds fixture data through the same entry points the plugin uses on the
// Deck (window.__cpData, window.opener.collectionStore), then runs the real
// assets/panel.js unmodified.
import panelJsSource from "../../assets/panel.js?raw";
import type { FixtureTab } from "./fixtures/data";

export function installPanelData(tabs: FixtureTab[], opts: { artBaseUrl?: string } = {}) {
  const { artBaseUrl } = opts;
  const games: Record<string, unknown> = {};
  for (const tab of tabs) {
    for (const game of tab.games) {
      if (game.data) games[String(game.appid)] = game.data;
    }
  }

  const tabsMeta = tabs
    .filter((t) => t.color)
    .map((t) => ({
      position: t.position,
      name: t.title,
      collections: t.collections,
      vendor: t.vendor,
      year: t.year,
      artwork: t.artwork && artBaseUrl ? `${artBaseUrl.replace(/\/$/, "")}/${encodeURIComponent(t.artwork)}` : null,
    }));

  (window as unknown as { __cpData: unknown }).__cpData = { games, tabs: tabsMeta };

  // Read by panel.js's collectAppsForTab() for the "no game selected" view.
  const collections = new Map<string, { m_strName: string; allApps: unknown[] }>();
  for (const tab of tabs) {
    for (const name of tab.collections) {
      collections.set(name, { m_strName: name, allApps: tab.games });
    }
  }
  (window as unknown as { opener: unknown }).opener = {
    collectionStore: { m_mapCollectionsFromStorage: collections },
  };
}

/** Runs panel.js, which stops any previous instance itself. */
export function runPanelScript() {
  // eslint-disable-next-line no-new-func
  new Function(panelJsSource)();
}
