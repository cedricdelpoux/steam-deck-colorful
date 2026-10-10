// Fixture data to preview the theme without a Deck. Shapes match
// console.resolve() for tabs, and main.py's window.__cpData payload for game
// and tab data.

export interface FixtureGame {
  appid: number;
  display_name: string;
  minutes_playtime_forever: number;
  rt_last_time_played: number; // unix seconds, 0 = never played
}

export interface FixtureGameData {
  region?: string;
  saves?: { latest: { mtime: number } | null };
  ra?:
    | { status: "ok"; awarded: number; total: number }
    | { status: "pending" }
    | { status: "unsupported" };
}

export interface FixtureTab {
  id: string;
  title: string;
  position: number;
  artwork: string; // file in plugin/assets/consoles, or "" for no panel
  color: string | null;
  collections: string[];
  vendor?: string;
  year?: string;
  games: (FixtureGame & { data?: FixtureGameData })[];
}

const now = Math.floor(Date.now() / 1000);
const daysAgo = (n: number) => now - n * 86400;

export const TABS: FixtureTab[] = [
  // First, so it's testable without scrolling the tab bar.
  {
    id: "steam",
    title: "Steam",
    position: 0,
    artwork: "Steam.png",
    color: "#33363b",
    collections: ["Steam"],
    games: [
      { appid: 500001, display_name: "Portal 2", minutes_playtime_forever: 612, rt_last_time_played: daysAgo(5) },
      { appid: 500002, display_name: "Hades", minutes_playtime_forever: 1830, rt_last_time_played: daysAgo(0) },
    ],
  },
  {
    id: "nes",
    title: "Nintendo Entertainment System",
    position: 1,
    artwork: "Nintendo Entertainment System.png",
    color: "#ba3141",
    collections: ["Nintendo Entertainment System"],
    vendor: "Nintendo",
    year: "1983",
    games: [
      {
        appid: 100001,
        display_name: "Super Mario Bros.",
        minutes_playtime_forever: 734,
        rt_last_time_played: daysAgo(0),
        data: { region: "USA", ra: { status: "ok", awarded: 18, total: 22 }, saves: { latest: { mtime: now - 3600 } } },
      },
      {
        appid: 100002,
        display_name: "The Legend of Zelda",
        minutes_playtime_forever: 1290,
        rt_last_time_played: daysAgo(2),
        data: { region: "USA", ra: { status: "ok", awarded: 6, total: 24 }, saves: { latest: { mtime: daysAgo(2) } } },
      },
      {
        appid: 100003,
        display_name: "Metroid",
        minutes_playtime_forever: 0,
        rt_last_time_played: 0,
        data: { region: "Europe", ra: { status: "pending" }, saves: { latest: null } },
      },
      {
        appid: 100004,
        display_name: "Kirby's Adventure",
        minutes_playtime_forever: 210,
        rt_last_time_played: daysAgo(35),
        data: { region: "USA", ra: { status: "unsupported" }, saves: { latest: { mtime: daysAgo(35) } } },
      },
      {
        appid: 100005,
        display_name: "Mega Man 2",
        minutes_playtime_forever: 88,
        rt_last_time_played: daysAgo(1),
        data: { region: "Japan", ra: { status: "ok", awarded: 30, total: 30 }, saves: { latest: { mtime: daysAgo(1) } } },
      },
      {
        appid: 100006,
        display_name: "Castlevania III: Dracula's Curse",
        minutes_playtime_forever: 42,
        rt_last_time_played: daysAgo(400),
      },
    ],
  },
  {
    id: "snes",
    title: "Super Nintendo Entertainment System",
    position: 2,
    artwork: "Super Nintendo Entertainment System.png",
    color: "#d64042",
    collections: ["Super Nintendo Entertainment System"],
    vendor: "Nintendo",
    year: "1990",
    games: [
      {
        appid: 200001,
        display_name: "Super Mario World",
        minutes_playtime_forever: 980,
        rt_last_time_played: daysAgo(0),
        data: { region: "USA", ra: { status: "ok", awarded: 96, total: 96 }, saves: { latest: { mtime: now - 900 } } },
      },
      {
        appid: 200002,
        display_name: "Chrono Trigger",
        minutes_playtime_forever: 2210,
        rt_last_time_played: daysAgo(6),
        data: { region: "USA", ra: { status: "ok", awarded: 40, total: 72 }, saves: { latest: { mtime: daysAgo(6) } } },
      },
      {
        appid: 200003,
        display_name: "Super Metroid",
        minutes_playtime_forever: 640,
        rt_last_time_played: daysAgo(14),
        data: { region: "Europe", ra: { status: "ok", awarded: 12, total: 12 }, saves: { latest: { mtime: daysAgo(14) } } },
      },
      {
        appid: 200004,
        display_name: "EarthBound",
        minutes_playtime_forever: 0,
        rt_last_time_played: 0,
        data: { region: "USA", ra: { status: "pending" }, saves: { latest: null } },
      },
      {
        appid: 200005,
        display_name: "Donkey Kong Country",
        minutes_playtime_forever: 155,
        rt_last_time_played: daysAgo(60),
      },
    ],
  },
  {
    id: "genesis",
    title: "Sega Genesis/Mega Drive",
    position: 3,
    artwork: "Sega Genesis.png",
    color: "#c23b2c",
    collections: ["Sega Genesis/Mega Drive"],
    vendor: "Sega",
    year: "1988",
    games: [
      {
        appid: 300001,
        display_name: "Sonic the Hedgehog 2",
        minutes_playtime_forever: 320,
        rt_last_time_played: daysAgo(3),
        data: { region: "USA", ra: { status: "ok", awarded: 26, total: 34 }, saves: { latest: { mtime: daysAgo(3) } } },
      },
      {
        appid: 300002,
        display_name: "Streets of Rage 2",
        minutes_playtime_forever: 175,
        rt_last_time_played: daysAgo(10),
        data: { region: "Europe", ra: { status: "unsupported" } },
      },
      {
        appid: 300003,
        display_name: "Golden Axe",
        minutes_playtime_forever: 0,
        rt_last_time_played: 0,
      },
      {
        appid: 300004,
        display_name: "Gunstar Heroes",
        minutes_playtime_forever: 64,
        rt_last_time_played: daysAgo(200),
        data: { region: "Japan", ra: { status: "ok", awarded: 5, total: 40 } },
      },
    ],
  },
  {
    id: "psx",
    title: "Sony PlayStation",
    position: 4,
    artwork: "Sony Playstation.png",
    color: "#878c92",
    collections: ["Sony PlayStation"],
    vendor: "Sony",
    year: "1994",
    games: [
      {
        appid: 400001,
        display_name: "Final Fantasy VII",
        minutes_playtime_forever: 3120,
        rt_last_time_played: daysAgo(1),
        data: { region: "USA", ra: { status: "ok", awarded: 14, total: 52 }, saves: { latest: { mtime: daysAgo(1) } } },
      },
      {
        appid: 400002,
        display_name: "Metal Gear Solid",
        minutes_playtime_forever: 540,
        rt_last_time_played: daysAgo(20),
        data: { region: "Europe", ra: { status: "ok", awarded: 8, total: 8 }, saves: { latest: { mtime: daysAgo(20) } } },
      },
      {
        appid: 400003,
        display_name: "Crash Bandicoot",
        minutes_playtime_forever: 0,
        rt_last_time_played: 0,
        data: { region: "USA", ra: { status: "pending" }, saves: { latest: null } },
      },
      {
        appid: 400004,
        display_name: "Tekken 3",
        minutes_playtime_forever: 275,
        rt_last_time_played: daysAgo(80),
      },
    ],
  },
  // No matching console: checks that an unstyled tab keeps Steam's look.
  {
    id: "homebrew",
    title: "Homebrew",
    position: 5,
    artwork: "",
    color: null,
    collections: [],
    games: [
      { appid: 600001, display_name: "Some Homebrew Demo", minutes_playtime_forever: 12, rt_last_time_played: daysAgo(15) },
    ],
  },
];
