# Setup details

Colorful only *decorates* tabs that already exist in your library — it
doesn't create your emulator setup or your tabs itself. Three things need to
be in place first, in this order:

1. **[EmuDeck](https://www.emudeck.com/)** — sets up your emulators and ROM
   folders, and (via Steam ROM Manager) adds your games to Steam as
   non-Steam shortcuts, one Steam **collection** per console. Follow its own
   setup flow and scan/add your consoles with their emulators; without this
   step there are no games and no per-console collections for anything below
   to work with.
2. **[Decky Loader](https://decky.xyz/)** — the plugin framework this (and
   every other Decky plugin) runs on. Install it first if you haven't already
   installed any Decky plugin on this Deck.
3. **[TabMaster](https://github.com/JanMalch/decky-tab-master)** — turns
   Steam's collections (the ones EmuDeck/Steam ROM Manager created) into tabs
   in the library UI. **Required** — this plugin has no notion of a "tab"
   outside the ones TabMaster creates; it reads TabMaster's own
   `settings.json` (`py_modules/tabmaster.py`) to know what tabs exist and in
   what order. Without it, Colorful loads without error but has nothing to
   attach to: no tabs are found, no panels are drawn, and the settings
   sheet's "Tabs" section just says "No TabMaster tabs found."

   In TabMaster's own settings, add one tab per console and give each a
   filter rule of type **Collection**, pointing at the Steam collection
   Steam ROM Manager created for that system (e.g. "Nintendo GameCube",
   "Sega Genesis/Mega Drive") — see TabMaster's own docs for the exact steps.
   One collection per tab is what Colorful expects; a tab built from several
   collections or a non-collection filter (genre, playtime...) has nothing
   for it to resolve a single console artwork/color from.

Once your consoles show up as their own tabs in the library (TabMaster's own
result, before installing this plugin at all), you're ready to install and
configure Colorful itself — see the main README's
[Install](../README.md#2-install) and
[Configure](../README.md#3-configure) sections.
