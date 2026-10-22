import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The build lands inside the Python package, so `railvane serve` ships the UI.
// RAILVANE_API / RAILVANE_POLL are set by compose.dev.yaml (API in another container,
// file events do not cross Windows bind mounts, so poll instead).
export default defineConfig({
  plugins: [react()],
  // One React for the app and for linked packages such as @webheaven/kit (file: dependency during development)
  resolve: { dedupe: ["react", "react-dom"] },
  build: { outDir: "../railvane/static", emptyOutDir: true },
  server: {
    proxy: { "/api": process.env.RAILVANE_API ?? "http://127.0.0.1:8484" },
    watch: { usePolling: Boolean(process.env.RAILVANE_POLL) },
  },
});
