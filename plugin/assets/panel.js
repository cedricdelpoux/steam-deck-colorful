// The info box shown in the lower part of the console panel.
//
// Runs in Steam's Big Picture context, where the library DOM lives -- the
// plugin's own frontend (SharedJSContext) can't reach it, so the backend
// injects this script instead, with per-game/per-tab data embedded as
// window.__cpData.
//
// IDs/marker come from window.__cpNamespace (set by cdp.py) rather than being
// hardcoded, so two installs of this file never fight over the same DOM ids
// or window.__consolePanel marker -- disabling one would otherwise tear down
// the other's live instance too. The `|| 'literal'` fallbacks only matter for
// a manual eval with no namespace set.
(() => {
  const NS = window.__cpNamespace || {};
  const ID = NS.infoId || 'cp-info-box';
  const ART_ID = NS.artId || 'cp-art';
  const MARKER = NS.marker || '__consolePanel';

  if (window[MARKER]) {
    window[MARKER].stop();
  }

  const LIB_ROOT = '.ZBBhezbBR4VJYysmVhF3_';
  const CONTAINER = '._3IBLc81yyL08OJ7rfKtF00';
  const TAB = '._3eEbSktrstBdLk0dVpnKVI';
  const TAB_ROW = '._1CJeU7emnRNSJ8Xk3Leavm';
  // let, not const: refresh() below reassigns these in place when the
  // backend pushes new data without re-running this whole script (see
  // push_data() in cdp.py) -- everything that reads DATA/TABS closes over
  // these bindings, so it sees the new values without needing its own update.
  let DATA = (window.__cpData && window.__cpData.games) || {};
  let TABS = (window.__cpData && window.__cpData.tabs) || [];

  const REGION_CODE = {Europe: 'EU', USA: 'US', Japan: 'JP', France: 'FR', Germany: 'DE',
                       Spain: 'ES', Italy: 'IT', Australia: 'AU'};

  // ---------- data ----------

  function appFromFocus(el) {
    let element = el;
    for (let i = 0; i < 12 && element; i++) {
      const fiberKey = Object.keys(element).find(k => k.startsWith('__reactFiber$'));
      if (fiberKey) {
        let fiber = element[fiberKey], depth = 0;
        while (fiber && depth < 30) {
          const props = fiber.memoizedProps || fiber.pendingProps;
          if (props) {
            for (const propName of ['app', 'overview', 'appOverview']) {
              const candidate = props[propName];
              if (candidate && typeof candidate === 'object' && typeof candidate.appid === 'number') {
                return candidate;
              }
            }
          }
          fiber = fiber.return; depth++;
        }
      }
      element = element.parentElement;
    }
    return null;
  }

  // The overview reports 0 minutes for non-Steam shortcuts. The live counter
  // exists only once Steam has loaded the game's details (its page was opened);
  // otherwise fall back to what gamedata.py read from localconfig.vdf.
  function playtimeOf(app, gameData) {
    try {
      const store = window.appDetailsStore || (window.opener && window.opener.appDetailsStore);
      const details = store && store.GetAppDetails(app.appid);
      if (details && details.nPlaytimeForever) return details.nPlaytimeForever;
    } catch (e) { /* store not reachable from this window */ }
    return app.minutes_playtime_forever || (gameData && gameData.playtime) || 0;
  }

  const esc = s => String(s).replace(/[&<>"']/g,
    c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

  function regionCode(region) {
    if (!region || region === '?') return null;
    return region.split('+').map(r => REGION_CODE[r] || r.slice(0, 2).toUpperCase()).join('·');
  }

  function fmtPlaytime(minutes) {
    if (!minutes) return 'Never played';
    if (minutes < 60) return minutes + ' min';
    const h = Math.floor(minutes / 60), m = minutes % 60;
    return m ? `${h}h ${m}m` : `${h}h`;
  }

  // Calendar-day difference (local midnight to local midnight), not a raw
  // 24h window — otherwise "played late yesterday, checked early today"
  // reads as less than 24h elapsed and wrongly shows "Today".
  function fmtAgo(ts) {
    if (!ts) return '—';
    const then = new Date(ts * 1000);
    const startOfDay = date => new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const days = Math.round((startOfDay(new Date()) - startOfDay(then)) / 86400000);
    const time = then.toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit'});
    if (days <= 0) return `Today, ${time}`;
    if (days === 1) return `Yesterday, ${time}`;
    if (days < 30) return `${days} days ago, ${time}`;
    return then.toLocaleDateString('en-US', {day: 'numeric', month: 'short', year: 'numeric'});
  }

  // ---------- view ----------

  function ensureBox() {
    let box = document.getElementById(ID);
    if (box) return box;
    const container = document.querySelector(LIB_ROOT + ' ' + CONTAINER);
    if (!container) return null;

    box = document.createElement('div');
    box.id = ID;
    box.style.cssText = [
      'position:absolute',
      'left:3%',
      'width:calc(var(--cp-width, 0%) - 6%)',
      // Read from the root rather than hardcoded here, so this always lines
      // up with where css.py anchored the artwork above it (see css.py). The
      // max-height is derived from that same top, minus a bottom margin, so an
      // unusually long title can never push the box past the panel's edge --
      // it clips its own overflow (title is line-clamped anyway) instead.
      'top:var(--cp-info-top, 53%)',
      'max-height:calc(100% - var(--cp-info-top, 53%) - 4%)',
      // Floor for the common case (title + 2 rows, ~82px measured) -- just
      // smooths the shrink-to-fallback-and-back jump; a game with more rows
      // still grows taller than this.
      'min-height:82px',
      // Same voile (--cp-tint) as the grid, plus matching ink colors --
      // css.py sets all of these on the root alongside --cp-color, so the
      // grid and this box always agree on which side (light-on-dark vs
      // dark-on-light) they're rendering.
      'background:var(--cp-tint, rgba(0,0,0,0.3))',
      'border-radius:14px',
      'z-index:11',
      'pointer-events:none',
      'box-sizing:border-box',
      'padding:12px 14px',
      'display:flex',
      'flex-direction:column',
      'gap:8px',
      'overflow:hidden',
      'font-family:inherit',
      'color:var(--cp-ink, #fff)',
      'text-shadow:var(--cp-shadow, 0 1px 2px rgba(0,0,0,0.35))'
    ].join(';');
    container.appendChild(box);
    return box;
  }

  // A real <img>, sized by its own fixed height, rather than a CSS
  // background-image shared across tabs via one background-size -- each
  // tab's art keeps its own natural width, and it's inspectable like any
  // other element.
  function ensureArt() {
    let img = document.getElementById(ART_ID);
    if (img) return img;
    const container = document.querySelector(LIB_ROOT + ' ' + CONTAINER);
    if (!container) return null;

    img = document.createElement('img');
    img.id = ART_ID;
    img.alt = '';
    img.style.cssText = [
      'position:absolute',
      // Centered within the panel's own width (0 to --cp-width), not the
      // whole container -- translateX(-50%) centers on the actual rendered
      // width instead of needing to know it up front.
      'left:calc(var(--cp-width, 0%) / 2)',
      'transform:translateX(-50%)',
      // Same anchor line CONTAINER's info box top is built from (see
      // buildPanelCss.ts/css.py) -- both read off the root so they can never
      // drift apart.
      'bottom:var(--cp-art-bottom, 20px)',
      'height:var(--cp-art-height, 175px)',
      'width:auto',
      'max-width:76%',
      'z-index:2',
      'pointer-events:none',
      'transition:left 0.3s ease-in-out'
    ].join(';');
    container.appendChild(img);
    return img;
  }

  const row = (label, value) =>
    `<div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px;font-size:12px">
       <span style="font-weight:500;color:var(--cp-ink-dim, rgba(255,255,255,0.85));text-shadow:var(--cp-shadow, 0 1px 2px rgba(0,0,0,0.35));white-space:nowrap">${label}</span>
       <span style="font-weight:600;text-align:right;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${value}</span>
     </div>`;

  // "Most played" label followed by a ranked list, since a top 3 doesn't fit
  // next to one label the way row()'s single value does.
  const mostPlayedList = (entries) =>
    `<div style="font-size:12px">
       <div style="font-weight:500;color:var(--cp-ink-dim, rgba(255,255,255,0.85));text-shadow:var(--cp-shadow, 0 1px 2px rgba(0,0,0,0.35));margin-bottom:3px">Most played</div>
       <div style="display:flex;flex-direction:column;gap:3px">
         ${entries.map(e =>
           `<div style="display:flex;justify-content:space-between;gap:8px;padding-left:10px">
              <span style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(e.name)}</span>
              <span style="font-weight:600;white-space:nowrap;flex:none">${fmtPlaytime(e.minutes)}</span>
            </div>`
         ).join('')}
       </div>
     </div>`;

  // A label/value row plus the thin progress bar underneath it, shared by the
  // RetroAchievements and native Steam achievements rows.
  const achievementProgressRow = (label, awarded, total) => {
    const percent = total ? Math.round(100 * awarded / total) : 0;
    return row(label, `${awarded} / ${total}`) +
      `<div style="height:4px;border-radius:2px;background:var(--cp-track, rgba(255,255,255,0.25));overflow:hidden">
         <div style="height:100%;width:${percent}%;background:var(--cp-ink, #fff)"></div>
       </div>`;
  };

  // Remembers the last confirmed RA status per game, across backend
  // refreshes -- a data push that happens to not carry `ra` for a game
  // already confirmed to have it (recomputing, or a push that only touched
  // other games) used to make the block disappear and reappear; this keeps
  // showing the last known state instead until a newer one replaces it.
  const raCache = new Map();   // appid -> gameData.ra

  function raRow(gameData, appid) {
    if (gameData && gameData.ra) raCache.set(appid, gameData.ra);
    const ra = (gameData && gameData.ra) || raCache.get(appid);
    if (!ra) return '';
    if (ra.status === 'ok') {
      return achievementProgressRow('RetroAchievements', ra.awarded, ra.total);
    }
    if (ra.status === 'pending') return row('RetroAchievements', 'No achievements yet');
    if (ra.status === 'unsupported') {
      const regionAbbrev = gameData && regionCode(gameData.region);
      return row('RetroAchievements',
        regionAbbrev && regionAbbrev !== 'US' ? `${regionAbbrev} dump unsupported` : 'Dump unsupported');
    }
    return '';
  }

  function savesRow(gameData) {
    if (!gameData || !gameData.saves) return '';
    const saves = gameData.saves;
    return row('Last save', saves.latest ? fmtAgo(saves.latest.mtime) : 'None');
  }

  // Native Steam games have no gamedata.py entry (that only covers emulated
  // ROMs), so their achievements come live from the client itself.
  // SteamClient.Apps.GetMyAchievementsForApp has no local-file equivalent,
  // so it has to be called from here rather than precomputed on the backend.
  const steamAchCache = new Map();   // appid -> {status: 'loading'|'ok'|'none', awarded, total}

  function fetchSteamAchievements(appid) {
    if (steamAchCache.has(appid)) return;
    // The local SteamClient in this context is a stub with no .Apps namespace;
    // the fully-featured one only exists on window.opener.
    const client = (window.opener && window.opener.SteamClient) || window.SteamClient;
    if (!client || !client.Apps) { steamAchCache.set(appid, {status: 'none'}); return; }
    steamAchCache.set(appid, {status: 'loading'});
    client.Apps.GetMyAchievementsForApp(String(appid)).then(res => {
      const list = res && res.result === 1 ? res.data.rgAchievements : null;
      steamAchCache.set(appid, list && list.length
        ? {status: 'ok', awarded: list.filter(a => a.bAchieved).length, total: list.length}
        : {status: 'none'});
      if (lastApp && lastApp.appid === appid) render(lastApp);
    }).catch(() => steamAchCache.set(appid, {status: 'none'}));
  }

  function steamAchRow(app) {
    fetchSteamAchievements(app.appid);   // no-op once cached, loading or not
    const cached = steamAchCache.get(app.appid);
    // Shown for the single round trip before the client answers, instead of
    // nothing -- a blank gap that then had the row pop in a moment later
    // read as a glitch rather than something still loading.
    if (!cached || cached.status === 'loading') return row('Achievements', 'Loading…');
    if (cached.status !== 'ok') return '';
    return achievementProgressRow('Achievements', cached.awarded, cached.total);
  }

  const badge = (text) =>
    `<span style="flex:none;font-size:10px;font-weight:700;padding:1px 6px;border-radius:6px;
                  color:#fff;background:rgba(0,0,0,0.25)">${text}</span>`;

  const titleHeader = (text, badgeHtml) =>
    `<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:2px">
       <div style="font-size:14px;font-weight:700;line-height:1.2;overflow:hidden;
                   display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical">${text}</div>
       ${badgeHtml}
     </div>`;

  function renderGame(app) {
    const box = ensureBox();
    const gameData = DATA[String(app.appid)];
    const regionAbbrev = gameData && regionCode(gameData.region);

    box.innerHTML =
      titleHeader(esc(app.display_name), regionAbbrev ? badge(regionAbbrev) : '') +
      row('Playtime', fmtPlaytime(playtimeOf(app, gameData))) +
      row('Last played', fmtAgo(app.rt_last_time_played)) +
      savesRow(gameData) +
      (gameData ? raRow(gameData, app.appid) : steamAchRow(app));
  }

  // Which tab (by position, 0-based among real tabs) is currently selected in
  // the tab strip, or null if that can't be read. querySelectorAll(TAB) only
  // ever matches actual tabs (not the L1/R1 hint elements before them), so
  // unlike css.py's :nth-of-type selectors this index needs no offset.
  function currentTabPosition() {
    const tabRow = document.querySelector(LIB_ROOT + ' ' + TAB_ROW);
    if (!tabRow) return null;
    const tabs = Array.from(tabRow.querySelectorAll(TAB));
    const idx = tabs.findIndex(t => t.getAttribute('aria-selected') === 'true');
    return idx >= 0 ? idx : null;
  }

  // Steam's own live app records (playtime, last-played) for every game in
  // this tab's collection(s) -- collectionStore is the same store TabMaster
  // itself reads to decide what a tab contains, so this never drifts from
  // what's actually shown in the grid.
  function collectAppsForTab(tabMeta) {
    try {
      const store = window.opener && window.opener.collectionStore;
      if (!store || !tabMeta.collections.length) return [];
      const wanted = new Set(tabMeta.collections);
      const apps = [];
      for (const col of store.m_mapCollectionsFromStorage.values()) {
        if (wanted.has(col.m_strName)) apps.push(...col.allApps);
      }
      return apps;
    } catch (e) {
      return [];
    }
  }

  // Which panel-enabled tab (if any) is currently selected. Looked up from
  // TABS rather than reading --cp-color back off the DOM: that custom
  // property transitions, so a synchronous getComputedStyle() read right
  // after switching tabs returned the *previous* tab's value, wrongly
  // hiding the box until some unrelated later render.
  function currentTabMeta() {
    const position = currentTabPosition();
    return position === null ? null : TABS.find(t => t.position === position) || null;
  }

  // Shown while a console tab is active but nothing is highlighted yet (an
  // empty tab, or the instant before Steam moves focus onto a tile) --
  // console trivia plus a live aggregate, instead of an empty box.
  function renderFallback(tabMeta) {
    const box = ensureBox();
    const apps = collectAppsForTab(tabMeta);
    // minutes_playtime_forever stays 0 for a shortcut until its details page
    // has been opened this session (same quirk playtimeOf() works around for
    // the single-game view) -- reused here so the aggregate isn't just 0.
    const played = apps.map(a => ({name: a.display_name, minutes: playtimeOf(a, DATA[String(a.appid)])}));
    const totalMinutes = played.reduce((sum, p) => sum + p.minutes, 0);
    const topPlayed = played.filter(p => p.minutes > 0).sort((a, b) => b.minutes - a.minutes).slice(0, 3);

    box.innerHTML =
      (tabMeta.name ? titleHeader(esc(tabMeta.name), badge(String(apps.length))) : '') +
      row('Total playtime', fmtPlaytime(totalMinutes)) +
      (topPlayed.length ? mostPlayedList(topPlayed) : '');
  }

  // Shows/hides the artwork <img> and (re)points it at the current tab's
  // picture -- independent of whether a game is focused, unlike the info
  // box below, so it stays up regardless of what renderGame/renderFallback
  // are doing.
  function syncArt(tabMeta) {
    const img = ensureArt();
    if (!img) return;
    if (!tabMeta || !tabMeta.artwork) { img.style.display = 'none'; return; }
    if (img.src !== tabMeta.artwork) img.src = tabMeta.artwork;
    img.style.display = 'block';
  }

  function render(app) {
    const box = ensureBox();
    if (!box) return;

    const tabMeta = currentTabMeta();
    syncArt(tabMeta);
    if (!tabMeta) { box.style.display = 'none'; return; }

    box.style.display = 'flex';
    if (app) renderGame(app); else renderFallback(tabMeta);
  }

  // ---------- wiring ----------

  let lastApp = null, lastTabPosition = null;

  function tick() {
    const position = currentTabPosition();
    if (position !== lastTabPosition) {
      lastTabPosition = position;
      lastApp = null;   // switched tabs -- don't keep showing the old tab's game
    }

    const focused = document.querySelector('.gpfocus');
    if (!focused) {
      lastApp = null;
    } else if (focused.closest(TAB_ROW)) {
      lastApp = null;   // on a tab, not a tile -- a real move away from any game
    } else {
      // Re-resolved every tick, not just on focus change: moving from one
      // tile straight to another can land on a tick where the new tile's
      // React fiber hasn't attached its `app` prop yet, so appFromFocus
      // returns null for a frame even though this is a game tile. Keep
      // showing the previous game through that gap instead of flashing the
      // fallback view; the retry picks up the real app the next frame.
      const app = appFromFocus(focused);
      if (app) lastApp = app;
    }
    render(lastApp);
  }

  // A tab switch (L1/R1) fires a whole burst of class/aria-selected mutations
  // as Steam updates the tab row and moves focus -- calling tick() straight
  // from the observer re-rendered on every single one, including the split
  // second mid-burst where no tab yet reads as selected. Coalescing into one
  // tick() per animation frame means the DOM has settled before anything
  // gets read.
  let tickScheduled = false;
  function scheduleTick() {
    if (tickScheduled) return;
    tickScheduled = true;
    requestAnimationFrame(() => { tickScheduled = false; tick(); });
  }

  const observer = new MutationObserver(scheduleTick);
  observer.observe(document.body,
    {attributes: true, subtree: true, attributeFilter: ['class', 'aria-selected']});
  tick();

  window[MARKER] = {
    stop() {
      observer.disconnect();
      const el = document.getElementById(ID);
      if (el) el.remove();
      const art = document.getElementById(ART_ID);
      if (art) art.remove();
    },
    current: () => lastApp && {name: lastApp.display_name, appid: lastApp.appid,
                               data: DATA[String(lastApp.appid)] || null},
    // Called by cdp.py's push_data() after it updates window.__cpData, so a
    // routine refresh (new playtime, RA progress landing) just redraws the
    // existing box with fresh numbers instead of tearing the whole thing
    // down and rebuilding it the way re-running this script would.
    refresh() {
      DATA = (window.__cpData && window.__cpData.games) || {};
      TABS = (window.__cpData && window.__cpData.tabs) || [];
      tick();
    }
  };

  return 'info panel running (' + Object.keys(DATA).length + ' games with data)';
})()
