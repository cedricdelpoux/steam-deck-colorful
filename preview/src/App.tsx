import { useEffect, useMemo, useState } from "react";
import { css } from "@linaria/core";
import { LibraryMock } from "./LibraryMock";
import { buildPanelCss } from "./buildPanelCss";
import { installPanelData, runPanelScript } from "./panelRuntime";
import { TABS } from "./fixtures/data";

const page = css`
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  padding: 24px;
`;

const toolbar = css`
  display: flex;
  align-items: center;
  gap: 20px;
  background: #1a2332;
  border: 1px solid #2a3a4d;
  border-radius: 10px;
  padding: 10px 16px;
  font-size: 13px;

  label {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
  }
`;

const hintText = css`
  color: #93a6b8;
`;

// The mock keeps the Deck's real logical size (854x534) so the px math in
// buildPanelCss.ts holds. `zoom` scales the layout itself, unlike
// `transform: scale()` which leaves the original box reserving its old size.
const stage = css`
  width: 854px;
  height: 534px;
  zoom: 1.25;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  border-radius: 6px;
  overflow: hidden;
  flex: none;
`;

export function App() {
  const [activeId, setActiveId] = useState(TABS[0].id);
  const [showCounts, setShowCounts] = useState(true);
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  const css = useMemo(() => buildPanelCss(TABS, { showCounts, theme }), [showCounts, theme]);

  useEffect(() => {
    let tag = document.getElementById("cp-panel-style") as HTMLStyleElement | null;
    if (!tag) {
      tag = document.createElement("style");
      tag.id = "cp-panel-style";
      document.head.appendChild(tag);
    }
    tag.textContent = css;
  }, [css]);

  useEffect(() => {
    installPanelData(TABS, { artBaseUrl: "/console-art" });
    runPanelScript();
    return () => {
      (window as unknown as { __consolePanel?: { stop(): void } }).__consolePanel?.stop();
    };
  }, []);

  // Left/right arrows act as L1/R1. Ignored in form fields so the theme
  // <select> keeps its own arrow keys.
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      const target = e.target as HTMLElement | null;
      if (target && ["SELECT", "INPUT", "TEXTAREA"].includes(target.tagName)) return;
      e.preventDefault();
      setActiveId((current) => {
        const index = TABS.findIndex((t) => t.id === current);
        const next = index + (e.key === "ArrowRight" ? 1 : -1);
        return TABS[Math.min(Math.max(next, 0), TABS.length - 1)].id;
      });
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className={page}>
      <div className={toolbar}>
        <strong>Colorful preview</strong>
        <label>
          <input type="checkbox" checked={showCounts} onChange={(e) => setShowCounts(e.target.checked)} />
          Game count in tab
        </label>
        <label>
          Theme:
          <select value={theme} onChange={(e) => setTheme(e.target.value as "dark" | "light")}>
            <option value="dark">Dark (default)</option>
            <option value="light">Light</option>
          </select>
        </label>
        <span className={hintText}>Click a game = gamepad focus (.gpfocus) · ←/→ = L1/R1</span>
      </div>
      <div className={stage}>
        <LibraryMock tabs={TABS} activeId={activeId} onActivate={setActiveId} />
      </div>
    </div>
  );
}
