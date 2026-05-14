// Single source of truth for API origin. Set VITE_API_URL at build time
// (e.g. https://oware-api.up.railway.app). Falls back to same-origin for
// local dev, where the dev server proxies /agents, /games, etc.
const RAW = (import.meta.env.VITE_API_URL ?? "").trim();
const DEV_DEFAULT = import.meta.env.DEV ? "http://localhost:8000" : "";
export const API_BASE = (RAW || DEV_DEFAULT).replace(/\/+$/, "");

if (import.meta.env.DEV) {
  // eslint-disable-next-line no-console
  console.info(`[oware] API_BASE = ${API_BASE || "(same-origin)"}`);
}

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${p}`;
}

export function wsUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (API_BASE) {
    return API_BASE.replace(/^http/, "ws") + p;
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${p}`;
}
