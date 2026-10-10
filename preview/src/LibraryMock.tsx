import { useState } from "react";
import { css, cx } from "@linaria/core";
import { LIB_ROOT, CONTAINER, TAB, TAB_ROW, TOP_BAR, GRID, COUNT, GROUP_HEADER } from "./steamSelectors";
import { GameTile } from "./GameTile";
import type { FixtureTab } from "./fixtures/data";

const root = css`
  position: relative;
  width: 854px;
  height: 534px;
  overflow: hidden;
  background: #1b2838;
`;

// CONTAINER covers the full height (0-534), not just what's below the tab
// bar: css.py offsets its ::before/::after by `top: 98px` relative to
// CONTAINER's own top, and panel.js places the info box at a % of
// VIEWPORT_H (see INFO_TOP_FRACTION in buildPanelCss.ts).
const container = css`
  position: absolute;
  inset: 0;
  overflow: hidden;
`;

// Starts 98px down, like the real library, where the grid has its own
// margin under the tab bar.
const grid = css`
  position: absolute;
  top: 98px;
  left: 0;
  right: 0;
  bottom: 0;
  overflow-y: auto;
`;

const gridInner = css`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
  gap: 10px;
  padding: 16px;
`;

// Background on TOP_BAR itself, not just searchRow, so the tab strip's
// rounded corners show the same color as the search row, like on the Deck.
const topBar = css`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 98px;
  z-index: 5;
  background: #16202c;
`;

const searchRow = css`
  height: 40px;
  display: flex;
  align-items: center;
  padding: 0 14px;
  font-size: 13px;
  color: #cfe0f0;
`;

// No horizontal scroll, like the real TabMaster tab bar. Clicking an
// off-screen tab would otherwise scroll the whole mock.
const tabRow = css`
  position: relative;
  height: 58px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 14px;
  overflow: hidden;
`;

// L1/R1 hint, mock decoration only.
const shoulderBtn = css`
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #dbe6f0;
  background: linear-gradient(#3a4656, #232c38);
  border: 1px solid #4a5768;
  border-radius: 6px;
  padding: 3px 9px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.12),
    inset 0 -1px 1px rgba(0, 0, 0, 0.4),
    0 1px 2px rgba(0, 0, 0, 0.3);
  flex: none;
`;

// R1 stays the 2nd DOM child, like on the Deck where nth-of-type(3) is the
// first tab; `order` only moves it visually to the end of the bar.
const shoulderBtnLast = css`
  order: 1;
`;

const tab = css`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  color: #eef4fa;
  cursor: pointer;
  flex: none;
`;

const tabLabel = css`
  white-space: nowrap;
`;

// Just enough of the Big Picture library DOM (same classes and offsets) for
// the production CSS and panel.js to apply unchanged.
export function LibraryMock({
  tabs,
  activeId,
  onActivate,
}: {
  tabs: FixtureTab[];
  activeId: string;
  onActivate: (id: string) => void;
}) {
  const [focusedAppId, setFocusedAppId] = useState<number | null>(null);
  const activeTab = tabs.find((t) => t.id === activeId) ?? tabs[0];

  return (
    <div className={cx(LIB_ROOT, root)}>
      <div className={cx(CONTAINER, container)}>
        <div className={cx(GRID, grid)}>
          {/* Inside GRID, as the "nudge" selector checks
              `GRID:not(:has(GROUP_HEADER:not(:empty)))`. */}
          <div className={GROUP_HEADER} />
          <div className={gridInner}>
            {activeTab.games.map((game) => (
              <GameTile
                key={game.appid}
                app={game}
                focused={focusedAppId === game.appid}
                onClick={() => setFocusedAppId((cur) => (cur === game.appid ? null : game.appid))}
              />
            ))}
          </div>
        </div>
      </div>

      <div className={cx(TOP_BAR, topBar)}>
        <div className={searchRow}>Library</div>
        <div className={cx(TAB_ROW, tabRow)}>
          <div className={shoulderBtn}>L1</div>
          <div className={cx(shoulderBtn, shoulderBtnLast)}>R1</div>
          {tabs.map((t) => (
            <div
              key={t.id}
              className={cx(TAB, tab)}
              aria-selected={t.id === activeId ? "true" : "false"}
              onClick={() => {
                onActivate(t.id);
                setFocusedAppId(null);
              }}
            >
              <span className={tabLabel}>{t.title}</span>
              <span className={COUNT}>{t.games.length}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
