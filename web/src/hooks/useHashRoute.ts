import { useEffect, useState } from "react";

export type Route =
  | { name: "play" }
  | { name: "match" }
  | { name: "leaderboard" }
  | { name: "games"; scope: "mine" | "all"; kind: "human" | "match" | "all" }
  | { name: "replay"; gameId: string; scope: "mine" | "all" }
  | { name: "stats"; scope: "mine" | "all"; kind: "human" | "match" | "all" };

function parseScope(qs: string): "mine" | "all" {
  return qs.includes("scope=all") ? "all" : "mine";
}

function parseKind(qs: string): "human" | "match" | "all" {
  if (qs.includes("kind=match")) return "match";
  if (qs.includes("kind=all")) return "all";
  return "human";
}

function parse(): Route {
  const raw = window.location.hash.replace(/^#/, "");
  const [path, qs = ""] = raw.split("?");
  if (path === "" || path === "/" || path === "/play") return { name: "play" };
  if (path === "/match") return { name: "match" };
  if (path === "/leaderboard") return { name: "leaderboard" };
  if (path === "/games") return { name: "games", scope: parseScope(qs), kind: parseKind(qs) };
  if (path === "/stats") return { name: "stats", scope: parseScope(qs), kind: parseKind(qs) };
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
