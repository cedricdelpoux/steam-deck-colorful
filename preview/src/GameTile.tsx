import { css, cx } from "@linaria/core";
import type { FixtureGame } from "./fixtures/data";

const thumb = css`
  aspect-ratio: 2 / 3;
  border-radius: 6px;
  background: #4a5560;
`;

const title = css`
  font-size: 10px;
  line-height: 1.2;
  color: #d7e2ec;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const tile = css`
  display: flex;
  flex-direction: column;
  gap: 6px;
  cursor: pointer;
  outline: none;

  &.gpfocus .${thumb} {
    outline: 3px solid #ffffff;
    background: #5c6975;
  }
`;

// `app` must stay a prop of this component: panel.js finds the focused game
// by walking React fibers up to props with a numeric `appid` (appFromFocus).
export function GameTile({
  app,
  focused,
  onClick,
}: {
  app: FixtureGame;
  focused: boolean;
  onClick: () => void;
}) {
  return (
    <div className={cx(tile, focused && "gpfocus")} onClick={onClick} tabIndex={0}>
      <div className={thumb} />
      <div className={title}>{app.display_name}</div>
    </div>
  );
}
