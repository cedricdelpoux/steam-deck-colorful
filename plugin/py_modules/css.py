"""Build the stylesheet injected into the library UI.

The structural half is fixed; only the per-tab rules change, and those are
generated from whatever tabs TabMaster currently holds rather than hardcoded by
position. Tabs are still targeted by position (`nth-of-type`) because that is
all the DOM exposes, but the mapping behind each position is resolved fresh, so
reordering tabs no longer scrambles the artwork.
"""
import os
import re

TAB = '._3eEbSktrstBdLk0dVpnKVI'
TAB_ROW = '._1CJeU7emnRNSJ8Xk3Leavm'
LIB_ROOT = '.ZBBhezbBR4VJYysmVhF3_'
CONTAINER = '._3IBLc81yyL08OJ7rfKtF00'
TOP_BAR = '._2JobstxtZVYF3078DblN2M'
GRID = '.WDa0_WKNSWIa38S26gl_T'
COUNT = '._1ui4IlLDo2hf32UFCezr1t'
GROUP_HEADER = '._2hvQbTq62AjXQS4tZqVepi'   # "Never played" etc. -- always in the
                                             # DOM, but empty unless the grid is grouped
GROUP_DIVIDER = '._3pJqXMYgfG8Emi3vn6e2WV'  # the rule line next to it -- a sibling,
                                             # not part of GROUP_HEADER itself

# nth-of-type(3) is the first tab in the bar; 1 and 2 are the L1/R1 hints.
FIRST_TAB_INDEX = 3

# Steam Deck's Big Picture UI is drawn at a fixed logical (CSS-pixel) size --
# it does not reflow like a page -- measured live over CDP as 854x534.
VIEWPORT_W, VIEWPORT_H = 854, 534
TOP_OFFSET = 98             # matches the ::before's own `top` below (the tab bar)
GAP = 20                    # breathing room kept between artwork and info box, px
GRID_TOP_NUDGE = 20         # visual-only push down for grids with no group header
# Wide enough for the artwork/info box, narrow enough to leave 3 games visible
# on the grid beside it -- not exposed as a setting, this is the one value
# that keeps both true.
PANEL_WIDTH = '40%'

# The panel's background covers the full height (top:98px to the bottom), but
# the artwork and the info box each occupy a fixed-size slot within it, the two
# stacked with a constant gap. Anchored by a small fixed margin under the tab
# bar rather than centered in the space that's left over -- centering split
# the slack evenly top and bottom, which under-used the room above the
# artwork while a 2-line title plus the RA/achievement row ran right up
# against the panel's own bottom edge.
_BOX_HEIGHT = VIEWPORT_H - TOP_OFFSET
# panel.js sizes the artwork <img> to this height itself (see ensureArt()).
TARGET_IMAGE_HEIGHT = 175
_TOP_MARGIN = 16
ART_BOTTOM_OFFSET = round(_BOX_HEIGHT - (_TOP_MARGIN + TARGET_IMAGE_HEIGHT))
INFO_TOP_FRACTION = (TOP_OFFSET + _TOP_MARGIN + TARGET_IMAGE_HEIGHT + GAP) / VIEWPORT_H

# One veil (color + opacity), shared by the grid (via this CSS) and the info
# box (via panel.js, which reads the same --cp-tint off an inline style --
# custom properties inherit into inline styles too) -- not two settings to
# keep in sync.
#
# Text stays light (white + drop shadow) either way: the console's own color
# stays dominant even veiled, so dark text never has enough contrast on it
# (tested -- illegible on the dimmed labels). Only the veil's own color/opacity
# changes: black 30% to darken, white 14% (the original opacity) to barely
# lighten.
_TINT_OPACITY_DARK = 0.3
_TINT_OPACITY_LIGHT = 0.14
# Gamepad focus (or :hover in the preview) matches the exact outline Steam
# itself draws around a focused game tile in the grid (measured live via CDP:
# `outline: rgba(255, 255, 255, 0.6) solid 2px`) instead of a theme-tinted
# fill -- same focus affordance as the rest of the UI, and it no longer needs
# tuning per theme since it's the same translucent white either way.
_TAB_FOCUS_OUTLINE = 'rgba(255, 255, 255, 0.6) solid 2px'
_TEXT = {
    'ink': '#ffffff',
    # Full white, same as 'ink' -- 85% read as a dim, mismatched grey rather
    # than "white, just secondary" once actually on screen. The label/value
    # hierarchy in row() comes from font-weight (500 vs 600) instead.
    'ink_dim': '#ffffff',
    'track': 'rgba(255, 255, 255, 0.25)',
    'shadow': '0 1px 2px rgba(0, 0, 0, 0.35)',
}


def _tint(mode):
    if mode == 'light':
        return 'rgba(255, 255, 255, %s)' % _TINT_OPACITY_LIGHT
    return 'rgba(0, 0, 0, %s)' % _TINT_OPACITY_DARK


# The static half of the stylesheet -- selectors, comments, rule order -- used
# to be hand-duplicated here and in preview/src/buildPanelCss.ts, and drifted:
# a stray "*/" inside a comment broke custom property resolution in production
# while the differently-worded TS copy never hit it. Loaded raw from a file
# both sides can read (buildPanelCss.ts imports the same path via Vite's
# `?raw`), so there is exactly one copy of this text left to get wrong.
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STRUCTURE_TEMPLATE_PATH = os.path.join(_HERE, 'assets', 'panel-structure.css')
_TOKEN_RE = re.compile(r'\{\{(\w+)\}\}')

with open(_STRUCTURE_TEMPLATE_PATH, 'r', encoding='utf-8') as _f:
    STRUCTURE_TEMPLATE = _f.read()


def _render(template, values):
    return _TOKEN_RE.sub(lambda m: str(values[m.group(1)]), template)


def _active_tab_scope(indexes, suffix=''):
    """`:has()` selector matching the root while any of these indexed tabs is
    active, each with `suffix` appended as a descendant selector.

    Built per-index rather than appending `suffix` once after a joined comma
    list: a comma has lower precedence than the descendant combinator, so
    `A, B X` is not `A X, B X` -- only the last item would ever get scoped.
    """
    return ', '.join(
        '%s:has(%s > %s:nth-of-type(%d)[aria-selected="true"])%s'
        % (LIB_ROOT, TAB_ROW, TAB, i, ' ' + suffix if suffix else '')
        for i in indexes
    )


def build(tabs, show_counts=True, theme='dark'):
    """Full stylesheet for the current tab layout.

    tabs: the list from console.resolve(); entries without a color are left
    untouched so Steam's own look shows through on them.

    theme: 'dark' veils the console color with black (default), 'light'
    with white -- shared by the grid tint below and panel.js's info box.
    """
    parts = [_render(STRUCTURE_TEMPLATE, {
        'root': LIB_ROOT, 'container': CONTAINER, 'topbar': TOP_BAR,
        'tabrow': TAB_ROW, 'tab': TAB, 'count': COUNT,
        'top_offset': TOP_OFFSET,
        'art_bottom_offset': ART_BOTTOM_OFFSET,
        'target_image_height': TARGET_IMAGE_HEIGHT,
        'info_top': '%.2f' % (INFO_TOP_FRACTION * 100),
        'tint': _tint(theme),
        'ink': _TEXT['ink'], 'ink_dim': _TEXT['ink_dim'],
        'track': _TEXT['track'], 'shadow': _TEXT['shadow'],
    })]

    panel_indexes = []
    for tab in tabs:
        if not tab.get('color'):
            continue
        index = FIRST_TAB_INDEX + tab['position']
        panel_indexes.append(index)

        declarations = ['--cp-width: %s;' % PANEL_WIDTH, '--cp-color: %s;' % tab['color']]

        parts.append(
            '/* %s */\n%s:has(%s > %s:nth-of-type(%d)[aria-selected="true"]) {\n    %s\n}\n'
            % (tab['title'] or tab['id'], LIB_ROOT, TAB_ROW, TAB, index,
               '\n    '.join(declarations))
        )

    if panel_indexes:
        scope = _active_tab_scope(panel_indexes)
        parts.append(
            '/* Only on tabs that show a panel, so the others keep Steam\'s look */\n'
            '%s {\n    --cp-tab-active-bg: transparent;\n'
            '    --cp-tab-idle-bg: var(--cp-tint);\n}\n' % scope
        )
        # The grid only needs to move over when a panel is actually showing;
        # applied unconditionally it was stripping Steam's own side padding on
        # every other tab too, leaving the game grid flush against the edges.
        grid_scope = _active_tab_scope(panel_indexes, GRID)
        parts.append(
            '%s {\n    left: var(--cp-width) !important;\n'
            '    right: 0 !important;\n    width: auto !important;\n'
            '    transition: left 0.3s ease-in-out;\n}\n' % grid_scope
        )
        # Grid background tinted to the console's own color (same --cp-tint
        # veil as the info box) -- posted on CONTAINER itself rather than
        # GRID: GRID gets a `transform: translateY(...)` below (the "nudge")
        # for grids with no group header, and a background painted directly
        # on it would have moved with that transform, uncovering a strip of
        # the default (dark) LIB_ROOT background where GRID used to sit.
        # CONTAINER never moves; its own ::before (the panel color, higher
        # z-index) already covers the panel side, so no width restriction is
        # needed here.
        container_tint_scope = _active_tab_scope(panel_indexes, CONTAINER)
        parts.append(
            '%s {\n    background-image: linear-gradient(var(--cp-tint), var(--cp-tint));\n'
            '    background-color: var(--cp-color);\n}\n' % container_tint_scope
        )
        # A row grouped under a header ("Never played"...) gets its top gap
        # from that header text; a flat, ungrouped grid (native Steam games)
        # has nothing else there, so only *that* case gets nudged down --
        # :not(:has(header)) tells them apart. transform doesn't touch the box
        # Steam measures for its own item layout (padding/height did, and
        # broke it) -- it only nudges what's already been painted.
        nudge_scope = _active_tab_scope(
            panel_indexes, '%s:not(:has(%s:not(:empty)))' % (GRID, GROUP_HEADER))
        parts.append(
            # !important + transition:none so it snaps instantly -- Steam's
            # own grid has its own transition that would otherwise animate
            # this like a scroll, and doing that in sync with the panel's own
            # width transition below read as the whole layout lurching left.
            '%s {\n    transform: translateY(%dpx) !important;\n'
            '    transition: none !important;\n}\n' % (nudge_scope, GRID_TOP_NUDGE)
        )
        # "Recent"/"Never played" etc.: Steam's own font-weight:100 at 60%
        # white reads as barely-there over the tinted grid, and the rule
        # line next to it (a sibling, not part of the header) is an even
        # fainter muted brown-grey gradient -- both measured live via CDP.
        parts.append(
            '%s {\n    color: #ffffff !important;\n    font-weight: 600 !important;\n}\n'
            '%s {\n    background-image: linear-gradient(to right, rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0)) !important;\n}\n'
            % (_active_tab_scope(panel_indexes, GROUP_HEADER),
               _active_tab_scope(panel_indexes, GROUP_DIVIDER))
        )
        # Gamepad focus: Steam paints the focused tab solid white with dark
        # text by default; keep the tab's own background instead (active
        # stays transparent, idle keeps its own veil) and add the exact
        # outline Steam itself draws around a focused game tile (measured
        # via CDP), so focus reads the same way everywhere in the UI.
        # outline-offset is 0, not the grid's 2px: tabs sit close enough
        # together that an outward offset would overlap neighbors.
        focus_scope_active = _active_tab_scope(
            panel_indexes, '%s %s[aria-selected="true"].gpfocus' % (TAB_ROW, TAB))
        focus_scope_idle = _active_tab_scope(
            panel_indexes, '%s %s[aria-selected="false"].gpfocus' % (TAB_ROW, TAB))
        parts.append(
            '%s {\n    background-color: var(--cp-tab-active-bg, transparent) !important;\n'
            '    outline: %s;\n    outline-offset: 0;\n'
            '    color: var(--cp-ink, #ffffff) !important;\n    box-shadow: none !important;\n}\n'
            '%s {\n    background-color: var(--cp-tab-idle-bg, var(--cp-tint)) !important;\n'
            '    outline: %s;\n    outline-offset: 0;\n'
            '    color: var(--cp-ink, #ffffff) !important;\n    box-shadow: none !important;\n}\n'
            % (focus_scope_active, _TAB_FOCUS_OUTLINE, focus_scope_idle, _TAB_FOCUS_OUTLINE))

    if not show_counts:
        # Same specificity as the badge's own styling rule above (which always
        # includes TAB and sets display:flex) -- a 3-class selector here would
        # lose to that 4-class one regardless of source order.
        parts.append('%s %s %s %s {\n    display: none;\n}\n' % (LIB_ROOT, TAB_ROW, TAB, COUNT))

    return '\n'.join(parts)
