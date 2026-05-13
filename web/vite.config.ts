import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ["*"],
    port: 5173,
    host: "0.0.0.0",
    proxy: {
      "/agents": "http://127.0.0.1:8000",
      "/stats": "http://127.0.0.1:8000",
      "/games": "http://127.0.0.1:8000",
      "/healthz": "http://127.0.0.1:8000",
      // (older "/stats" entry kept; /stats is now scope-aware)
      "/play": {
        target: "ws://127.0.0.1:8000",
        ws: true,
      },
    },
  },
});
