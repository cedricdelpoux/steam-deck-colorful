// TS port of py_modules/css.py, so the design can be iterated on in
// JS/CSS with instant reload instead of redeploying to the Deck for every
// change. The static part (selectors, comments, rule order) is no longer
// hand-duplicated here: it lives in assets/panel-structure.css,
// loaded raw (like panel.js) and filled with the same {{...}} tokens as the
// Python side -- a file that drifted once (a stray "*/" in a comment broke
// custom property resolution in production without this differently-worded
// TS version ever reproducing it). Only the per-tab rules (colors, tab
// count) are still generated separately on each side, since they come from
// different data sources (TabMaster vs. this fixture).
import structureTemplate from "../../assets/panel-structure.css?raw";
import { LIB_ROOT, CONTAINER, TAB, TAB_ROW, TOP_BAR, GRID, COUNT, GROUP_HEADER, GROUP_DIVIDER, FIRST_TAB_INDEX } from "./steamSelectors";
import type { FixtureTab } from "./fixtures/data";

// The Deck's Big Picture draws at a fixed logical (CSS px) size -- measured
// live on the real console (see css.py). Keeping this same size here lets
// the pixel-based math below carry over unchanged.
export const VIEWPORT_W = 854;
export const VIEWPORT_H = 534;

const TOP_OFFSET = 98;
const GAP = 20;
const GRID_TOP_NUDGE = 20;
const PANEL_WIDTH = "40%";
const TARGET_IMAGE_HEIGHT = 175;

// Anchored by a small fixed margin under the tab bar rather than centered in
// the leftover space below the artwork+info stack -- centering split the
// slack evenly top and bottom, which under-used the room above the artwork
// while a 2-line title plus the RA/achievement row ran right up against
// the panel's own bottom edge.
const BOX_HEIGHT = VIEWPORT_H - TOP_OFFSET;
const TOP_MARGIN = 16;
const ART_BOTTOM_OFFSET = Math.round(BOX_HEIGHT - (TOP_MARGIN + TARGET_IMAGE_HEIGHT));
const INFO_TOP_FRACTION = (TOP_OFFSET + TOP_MARGIN + TARGET_IMAGE_HEIGHT + GAP) / VIEWPORT_H;

// One veil (color + opacity), shared by the grid (via this CSS) and the
// info box (via panel.js, which reads the same --cp-tint off an inline
// style -- custom properties inherit into inline styles too) -- not two
// settings to keep in sync.
//
// Text stays light (white + drop shadow) either way: the console's own
// color stays dominant even veiled, so dark text never has enough contrast
// on it (tested -- illegible on the dimmed labels). Only the veil's own
// color/opacity changes: black 30% to darken, white 14% (the original
// opacity) to barely lighten.
const TINT_PRESETS = {
  dark: { tint: "rgba(0, 0, 0, 0.3)" },
  light: { tint: "rgba(255, 255, 255, 0.14)" },
};
// Gamepad focus (or :hover in this preview) matches the exact outline
// Steam itself draws around a focused game tile in the grid (measured live
// via CDP: `outline: rgba(255, 255, 255, 0.6) solid 2px`) instead of a
// theme-tinted fill -- same focus affordance as the rest of the UI, and it
// no longer needs tuning per theme since it's the same translucent white
// either way.
const TAB_FOCUS_OUTLINE = "rgba(255, 255, 255, 0.6) solid 2px";
const TEXT = {
  ink: "#ffffff",
  // Full white, same as ink -- 85% read as a dim, mismatched grey rather
  // than "white, just secondary" once actually on screen. The label/value
  // hierarchy in row() comes from font-weight (500 vs 600) instead.
  inkDim: "#ffffff",
  track: "rgba(255, 255, 255, 0.25)",
  shadow: "0 1px 2px rgba(0, 0, 0, 0.35)",
};

function renderTemplate(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_, key: string) => String(values[key]));
}

function structure(infoTopPercent: number, theme: "dark" | "light") {
  const preset = TINT_PRESETS[theme];
  return renderTemplate(structureTemplate, {
    root: `.${LIB_ROOT}`,
    container: `.${CONTAINER}`,
    topbar: `.${TOP_BAR}`,
    tabrow: `.${TAB_ROW}`,
    tab: `.${TAB}`,
    count: `.${COUNT}`,
    top_offset: TOP_OFFSET,
    art_bottom_offset: ART_BOTTOM_OFFSET,
    target_image_height: TARGET_IMAGE_HEIGHT,
    info_top: infoTopPercent.toFixed(2),
    tint: preset.tint,
    ink: TEXT.ink,
    ink_dim: TEXT.inkDim,
    track: TEXT.track,
    shadow: TEXT.shadow,
  });
}

// `:has()` selector matching the root while any of these indexed tabs is
// active, each with `suffix` appended as a descendant selector.
//
// Built per-index rather than appending `suffix` once after a joined comma
// list: a comma has lower precedence than the descendant combinator, so
// `A, B X` is not `A X, B X` -- only the last item would ever get scoped.
function activeTabScope(indexes: number[], suffix = "") {
  return indexes
    .map((i) => `.${LIB_ROOT}:has(.${TAB_ROW} > .${TAB}:nth-of-type(${i})[aria-selected="true"])${suffix ? " " + suffix : ""}`)
    .join(", ");
}

export interface BuildOptions {
  showCounts?: boolean;
  theme?: "dark" | "light"; // black veil (darkens) or white (lightens) over the grid + info box
}

export function buildPanelCss(tabs: FixtureTab[], opts: BuildOptions = {}): string {
  const { showCounts = true, theme = "dark" } = opts;
  const parts: string[] = [structure(INFO_TOP_FRACTION * 100, theme)];

  const panelIndexes: number[] = [];
  for (const tab of tabs) {
    if (!tab.color) continue;
    const index = FIRST_TAB_INDEX + tab.position;
    panelIndexes.push(index);

    const declarations = [`--cp-width: ${PANEL_WIDTH};`, `--cp-color: ${tab.color};`];

    parts.push(
      `/* ${tab.title} */\n.${LIB_ROOT}:has(.${TAB_ROW} > .${TAB}:nth-of-type(${index})[aria-selected="true"]) {\n    ${declarations.join(
        "\n    "
      )}\n}\n`
    );
  }

  if (panelIndexes.length) {
    parts.push(
      `/* Only on tabs that show a panel, so the others keep Steam's look */\n${activeTabScope(panelIndexes)} {\n    --cp-tab-active-bg: transparent;\n    --cp-tab-idle-bg: var(--cp-tint);\n}\n`
    );

    parts.push(
      `${activeTabScope(panelIndexes, `.${GRID}`)} {\n    left: var(--cp-width) !important;\n    right: 0 !important;\n    width: auto !important;\n    transition: left 0.3s ease-in-out;\n}\n`
    );

    // Grid background tinted to the console's own color, posted on CONTAINER
    // rather than GRID: GRID gets a translateY "nudge" below, and a
    // background painted on it would move with that transform, uncovering a
    // strip of the default dark LIB_ROOT background. CONTAINER never moves;
    // its ::before (the panel color, higher z-index) already covers the
    // panel side.
    parts.push(
      `${activeTabScope(panelIndexes, `.${CONTAINER}`)} {\n` +
        `    background-image: linear-gradient(var(--cp-tint), var(--cp-tint));\n` +
        `    background-color: var(--cp-color);\n}\n`
    );

    const nudgeScope = activeTabScope(panelIndexes, `.${GRID}:not(:has(.${GROUP_HEADER}:not(:empty)))`);
    parts.push(`${nudgeScope} {\n    transform: translateY(${GRID_TOP_NUDGE}px) !important;\n    transition: none !important;\n}\n`);

    // "Recent"/"Never played" etc.: Steam's own font-weight:100 at 60% white
    // reads as barely-there over the tinted grid, and the rule line next to
    // it (a sibling, not part of the header) is an even fainter gradient.
    parts.push(
      `${activeTabScope(panelIndexes, `.${GROUP_HEADER}`)} {\n    color: #ffffff !important;\n    font-weight: 600 !important;\n}\n` +
        `${activeTabScope(panelIndexes, `.${GROUP_DIVIDER}`)} {\n    background-image: linear-gradient(to right, rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0)) !important;\n}\n`
    );

    // :hover is added alongside .gpfocus in this preview only (not in
    // css.py), so the focus style can be tested with a mouse. outline-offset
    // is 0, not the grid's 2px: tabs sit close enough together that an
    // outward offset would overlap neighbors.
    const focusScopeActive = [
      activeTabScope(panelIndexes, `.${TAB_ROW} .${TAB}[aria-selected="true"].gpfocus`),
      activeTabScope(panelIndexes, `.${TAB_ROW} .${TAB}[aria-selected="true"]:hover`),
    ].join(", ");
    const focusScopeIdle = [
      activeTabScope(panelIndexes, `.${TAB_ROW} .${TAB}[aria-selected="false"].gpfocus`),
      activeTabScope(panelIndexes, `.${TAB_ROW} .${TAB}[aria-selected="false"]:hover`),
    ].join(", ");
    parts.push(
      `${focusScopeActive} {\n    background-color: var(--cp-tab-active-bg, transparent) !important;\n    outline: ${TAB_FOCUS_OUTLINE};\n    outline-offset: 0;\n    color: var(--cp-ink, #ffffff) !important;\n    box-shadow: none !important;\n}\n` +
        `${focusScopeIdle} {\n    background-color: var(--cp-tab-idle-bg, var(--cp-tint)) !important;\n    outline: ${TAB_FOCUS_OUTLINE};\n    outline-offset: 0;\n    color: var(--cp-ink, #ffffff) !important;\n    box-shadow: none !important;\n}\n`
    );
  }

  if (!showCounts) {
    parts.push(`.${LIB_ROOT} .${TAB_ROW} .${TAB} .${COUNT} {\n    display: none;\n}\n`);
  }

  return parts.join("\n");
}
