import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import wyw from "@wyw-in-js/vite";
import fs from "node:fs";
import path from "node:path";

// Serves the plugin's real console artwork (assets/consoles/*.png) under
// /console-art/, so it never needs copying into preview/.
function serveConsoleArt() {
  const artDir = path.resolve(__dirname, "../assets/consoles");
  return {
    name: "serve-console-art",
    configureServer(server: any) {
      server.middlewares.use("/console-art", (req: any, res: any, next: any) => {
        const file = decodeURIComponent((req.url || "").split("?")[0]).replace(/^\//, "");
        const full = path.join(artDir, file);
        if (!full.startsWith(artDir) || !fs.existsSync(full)) return next();
        res.setHeader("Content-Type", "image/png");
        // build_assets.py regenerates these in place under the same names.
        res.setHeader("Cache-Control", "no-store");
        fs.createReadStream(full).pipe(res);
      });
    },
  };
}

export default defineConfig({
  // Linaria's bundler integration lives in wyw-in-js since v6 (@linaria/vite
  // is stuck on v5). wyw() must run before react() so styles are extracted
  // before JSX is transformed.
  plugins: [wyw(), react(), serveConsoleArt()],
  server: { port: 5183, strictPort: true },
});
