// Settings sheet for the console panel.
//
// The panel itself is drawn by the backend, which injects its CSS and script
// into Steam's Big Picture page -- nothing here renders any of it. This only
// reads and writes the settings behind it.
import { callable, definePlugin } from "@decky/api";
import {
  ButtonItem,
  DropdownItem,
  PanelSection,
  PanelSectionRow,
  TextField,
  ToggleField,
} from "@decky/ui";
import { useEffect, useRef, useState } from "react";
import { FaTimes } from "react-icons/fa";
import { FiLayout } from "react-icons/fi";

const AUTO = "__auto";
const NONE = "__none";

interface Settings {
  enabled: boolean;
  show_counts: boolean;
  inline_images: boolean;
  theme: "dark" | "light";
  ra_key: string;
  ra_user: string;
  overrides: Record<string, { artwork?: string; color?: string }>;
}

interface Tab {
  id: string;
  title: string;
  position: number;
  artwork: string | null;
  color: string | null;
  source: "auto" | "manual" | "none";
}

interface State {
  settings: Settings;
  tabs: Tab[];
  consoles: string[];
  games: number;
  linked: boolean;
  error: string | null;
}

type RaStatus =
  | { ok: true; user: string; avatar: string; points: number; member_since: string | null }
  | { ok: false; error: string };

const getState = callable<[], State>("get_state");
const setSettings = callable<[Partial<Settings>], State>("set_settings");
const setOverride = callable<[string, string | null, string | null], State>("set_override");
const refresh = callable<[boolean], State>("refresh");
const verifyRa = callable<[], RaStatus>("verify_ra");

function Content() {
  const [state, setState] = useState<State | null>(null);
  const [busy, setBusy] = useState(false);
  const [raStatus, setRaStatus] = useState<RaStatus | null>(null);
  const [raChecking, setRaChecking] = useState(false);
  // Track what's on screen separately from settings.ra_user/ra_key: those
  // only change once persisted, so driving TextField's value straight off
  // them would have React overwrite each keystroke with the stale value.
  // Persisted on every change rather than on blur, since the on-screen
  // keyboard below blurs the field before delivering the keypress.
  const [raUserDraft, setRaUserDraft] = useState("");
  const [raKeyDraft, setRaKeyDraft] = useState("");
  const activeRaField = useRef<"ra_user" | "ra_key" | null>(null);

  useEffect(() => {
    getState().then((s) => {
      setState(s);
      setRaUserDraft(s.settings.ra_user);
      setRaKeyDraft(s.settings.ra_key);
      // Show connection status right away if credentials are already saved,
      // same as Dolphin/RetroArch/DuckStation do when you reopen RA settings.
      if (s.settings.ra_user && s.settings.ra_key) {
        checkRa();
      }
    });
  }, []);

  const editRaField = (field: "ra_user" | "ra_key", next: string) => {
    (field === "ra_user" ? setRaUserDraft : setRaKeyDraft)(next);
    void setSettings({ [field]: next });
  };

  useEffect(() => {
    // SteamOS's touch on-screen keyboard is its own native window
    // (EWindowType.Keyboard), not a DOM overlay -- on the Deck's touchscreen
    // its keystrokes land on `document.body` instead of the focused <input>
    // (confirmed live via CDP: the input blurs *before* the keydown even
    // arrives). Gamepad-driven typing is unaffected -- there the keydown
    // already targets the real input, so this never fires for it.
    const onStrayKeydown = (e: KeyboardEvent) => {
      const field = activeRaField.current;
      if (!field || e.target !== document.body) {
        return;
      }
      const current = field === "ra_user" ? raUserDraft : raKeyDraft;
      if (e.key === "Backspace") {
        e.preventDefault();
        editRaField(field, current.slice(0, -1));
      } else if (e.key.length === 1) {
        e.preventDefault();
        editRaField(field, current + e.key);
      }
    };
    document.addEventListener("keydown", onStrayKeydown, true);
    return () => document.removeEventListener("keydown", onStrayKeydown, true);
  }, [raUserDraft, raKeyDraft]);

  const checkRa = async () => {
    setRaChecking(true);
    try {
      setRaStatus(await verifyRa());
    } finally {
      setRaChecking(false);
    }
  };

  const disconnectRa = () => {
    editRaField("ra_user", "");
    editRaField("ra_key", "");
    setRaStatus(null);
  };

  // Every call returns the whole state, so the sheet always shows what the
  // backend actually ended up with rather than what we asked for.
  const run = async (call: Promise<State>) => {
    setBusy(true);
    try {
      setState(await call);
    } finally {
      setBusy(false);
    }
  };

  if (!state) {
    return (
      <PanelSection>
        <PanelSectionRow>
          <div style={{ fontSize: "12px", opacity: 0.8 }}>Loading…</div>
        </PanelSectionRow>
      </PanelSection>
    );
  }

  const { settings, tabs, consoles } = state;

  return (
    <>
      <PanelSection title="Panel">
        <PanelSectionRow>
          <ToggleField
            label="Enabled"
            checked={settings.enabled}
            disabled={busy}
            onChange={(enabled) => run(setSettings({ enabled }))}
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <ToggleField
            label="Game count in tab"
            checked={settings.show_counts}
            disabled={busy || !settings.enabled}
            onChange={(show_counts) => run(setSettings({ show_counts }))}
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <ToggleField
            label="Light theme"
            checked={settings.theme === "light"}
            disabled={busy || !settings.enabled}
            onChange={(light) => run(setSettings({ theme: light ? "light" : "dark" }))}
          />
        </PanelSectionRow>
      </PanelSection>

      <PanelSection title="RetroAchievements">
        {raStatus?.ok ? (
          <PanelSectionRow>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <img
                src={raStatus.avatar}
                width={48}
                height={48}
                style={{ borderRadius: "6px", flexShrink: 0 }}
              />
              <div style={{ minWidth: 0, flexGrow: 1 }}>
                <div style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis" }}>
                  {raStatus.user}
                </div>
                <div style={{ fontSize: "11px", opacity: 0.8 }}>{raStatus.points} points</div>
              </div>
              <div
                onClick={() => disconnectRa()}
                title="Disconnect"
                style={{ cursor: "pointer", opacity: 0.6, flexShrink: 0, padding: "4px" }}
              >
                <FaTimes />
              </div>
            </div>
          </PanelSectionRow>
        ) : (
          <>
            <PanelSectionRow>
              <TextField
                label="Username"
                value={raUserDraft}
                disabled={busy}
                onFocus={() => (activeRaField.current = "ra_user")}
                onChange={(e) => editRaField("ra_user", e.currentTarget.value)}
              />
            </PanelSectionRow>
            <PanelSectionRow>
              <TextField
                label="API key"
                description="From retroachievements.org, Settings › Web API key"
                value={raKeyDraft}
                bIsPassword
                disabled={busy}
                onFocus={() => (activeRaField.current = "ra_key")}
                onChange={(e) => editRaField("ra_key", e.currentTarget.value)}
              />
            </PanelSectionRow>
            <PanelSectionRow>
              <ButtonItem layout="below" disabled={raChecking} onClick={() => checkRa()}>
                {raChecking ? "Connecting…" : "Connect"}
              </ButtonItem>
            </PanelSectionRow>
            {raStatus && !raStatus.ok && (
              <PanelSectionRow>
                <div style={{ fontSize: "12px", color: "#ff6b6b" }}>{raStatus.error}</div>
              </PanelSectionRow>
            )}
          </>
        )}
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            description="Wipes the cached ROM hashes and re-matches every game against RetroAchievements from scratch. New or changed ROMs are already picked up automatically -- only useful if achievement matching looks wrong."
            disabled={busy}
            onClick={() => run(refresh(true))}
          >
            Rescan ROM hashes
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>

      <PanelSection title="Tabs">
        {tabs.length === 0 && (
          <PanelSectionRow>
            <div style={{ fontSize: "12px", opacity: 0.8 }}>No TabMaster tabs found.</div>
          </PanelSectionRow>
        )}
        {tabs.map((tab) => {
          const override = settings.overrides[tab.id]?.artwork;
          const selected =
            override === undefined ? AUTO : override === "" ? NONE : override.replace(/\.png$/, "");
          const auto = tab.source === "auto" && tab.artwork
            ? `Auto (${tab.artwork.replace(/\.png$/, "")})`
            : "Auto (no match)";
          return (
            <PanelSectionRow key={tab.id}>
              <DropdownItem
                label={tab.title || tab.id}
                rgOptions={[
                  { data: AUTO, label: auto },
                  { data: NONE, label: "No panel" },
                  ...consoles.map((name) => ({ data: name, label: name })),
                ]}
                selectedOption={selected}
                disabled={busy || !settings.enabled}
                onChange={(option) =>
                  run(
                    option.data === AUTO
                      ? setOverride(tab.id, null, null)
                      : setOverride(tab.id, option.data === NONE ? "" : option.data, null),
                  )
                }
              />
            </PanelSectionRow>
          );
        })}
      </PanelSection>

      <PanelSection title="Status">
        <PanelSectionRow>
          <div style={{ fontSize: "12px", opacity: 0.8 }}>
            {state.error
              ? `Error: ${state.error}`
              : `${state.games} games · artwork ${state.linked ? "linked" : "inlined"}`}
          </div>
        </PanelSectionRow>
      </PanelSection>
    </>
  );
}

export default definePlugin(() => ({
  // Separate from plugin.json's own "name" (which drives the install folder
  // and settings path) -- this is what Decky's plugin list displays, as
  // plain centered text in a ~204px column with no way to inject JSX there.
  // Keep it short: anything much longer than ~16 characters wraps to two
  // lines and throws off alignment against single-line sibling plugins.
  name: "Colorful",
  // The QAM's own panel header (once this plugin is open) is a different,
  // JSX-capable spot -- titleView lets the full context stay on one line
  // there without needing `name` itself to carry it.
  titleView: (
    <div style={{ display: "flex", alignItems: "baseline", gap: "5px", whiteSpace: "nowrap" }}>
      <span>Colorful</span>
      <span style={{ fontSize: "11px", opacity: 0.6 }}>for TabMaster</span>
    </div>
  ),
  content: <Content />,
  icon: <FiLayout />,
}));
