import { useEffect, useState } from "react";

export type Route =
  | { name: "play" }
  | { name: "games"; scope: "mine" | "all" }
  | { name: "replay"; gameId: string; scope: "mine" | "all" }
  | { name: "stats"; scope: "mine" | "all" };

function parseScope(qs: string): "mine" | "all" {
  return qs.includes("scope=all") ? "all" : "mine";
}

function parse(): Route {
  const raw = window.location.hash.replace(/^#/, "");
  const [path, qs = ""] = raw.split("?");
  if (path === "" || path === "/" || path === "/play") return { name: "play" };
  if (path === "/games") return { name: "games", scope: parseScope(qs) };
  if (path === "/stats") return { name: "stats", scope: parseScope(qs) };
  const m = path.match(/^\/games\/([^/]+)$/);
  if (m) return { name: "replay", gameId: m[1], scope: parseScope(qs) };
  return { name: "play" };
}

export function useHashRoute(): [Route, (path: string) => void] {
  const [route, setRoute] = useState<Route>(parse);
  useEffect(() => {
    const onChange = () => setRoute(parse());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  const navigate = (path: string) => {
    window.location.hash = path;
  };
  return [route, navigate];
}
