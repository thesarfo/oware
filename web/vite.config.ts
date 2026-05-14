import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API_HTTP = process.env.VITE_API_URL ?? "http://127.0.0.1:8000";
const API_WS = API_HTTP.replace(/^http/, "ws");

const proxy = {
  "/agents": API_HTTP,
  "/stats": API_HTTP,
  "/games": API_HTTP,
  "/healthz": API_HTTP,
  "/play": { target: API_WS, ws: true },
};

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: true,
    port: 5173,
    host: "0.0.0.0",
    proxy,
  },
  preview: {
    allowedHosts: true,
    host: "0.0.0.0",
    port: Number(process.env.PORT ?? 4173),
    proxy,
  },
});
