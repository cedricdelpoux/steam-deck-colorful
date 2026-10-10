import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import wyw from "@wyw-in-js/vite";
import fs from "node:fs";
import path from "node:path";

// Sert les artworks console réelles du plugin (plugin/assets/consoles/*.png)
// sous /console-art/, pour ne jamais avoir à les dupliquer dans preview/.
function serveConsoleArt() {
  const artDir = path.resolve(__dirname, "../plugin/assets/consoles");
  return {
    name: "serve-console-art",
    configureServer(server: any) {
      server.middlewares.use("/console-art", (req: any, res: any, next: any) => {
        const file = decodeURIComponent((req.url || "").split("?")[0]).replace(/^\//, "");
        const full = path.join(artDir, file);
        if (!full.startsWith(artDir) || !fs.existsSync(full)) return next();
        res.setHeader("Content-Type", "image/png");
        // Ces PNG sont régénérés sur place (même nom de fichier) à chaque
        // passage de build_assets.py -- sans ça, le navigateur garde en
        // cache une ancienne version et on croit revoir un bug déjà corrigé.
        res.setHeader("Cache-Control", "no-store");
        fs.createReadStream(full).pipe(res);
      });
    },
  };
}

export default defineConfig({
  // Linaria (@linaria/core, @linaria/react) délègue son intégration bundler
  // au projet wyw-in-js depuis la v6/7 -- @linaria/vite est resté sur
  // l'ancienne v5 et ne sait pas transformer ce que produisent nos imports
  // @linaria/core actuels. wyw() avant react() : il doit extraire les
  // `css`/`styled` en vraies feuilles de style avant que le plugin React ne
  // transforme le JSX.
  plugins: [wyw(), react(), serveConsoleArt()],
  // Port fixe et dédié (ni le défaut Vite 5173, ni 8888) pour ne jamais
  // entrer en conflit avec un autre outil déjà lancé (tunnel CDP, etc.).
  server: { port: 5183, strictPort: true },
});
