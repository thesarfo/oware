import { apiUrl } from "./api";

export interface GameListEntry {
  game_id: string;
  agent_id: string;
  opponent_kind: "human" | "agent";
  opponent_agent_id: string | null;
  winner: "south" | "north" | "draw" | null;
  reason: string;
  plies: number;
  final_stores: { south: number; north: number };
  created_at: number;
  ended_at: number | null;
  final_pits: number[];
}

export interface GameMove {
  ply: number;
  side: "south" | "north";
  actor: "human" | "agent";
  action: number;
  captured: number;
  pits_after: number[];
  store_south_after: number;
  store_north_after: number;
  thought_ms: number | null;
  az_hint: number | null;
}

export interface GameDetail {
  game_id: string;
  agent_id: string;
  opponent_kind: "human" | "agent";
  opponent_agent_id: string | null;
  winner: "south" | "north" | "draw" | null;
  reason: string;
  plies: number;
  final_stores: { south: number; north: number };
  created_at: number;
  ended_at: number | null;
  human_plays: "south" | "north" | null;
  initial_state: { pits: number[]; stores: [number, number]; to_move: number; ply: number };
  moves: GameMove[];
}

export interface Frame {
  pits: number[];
  stores: { south: number; north: number };
  to_move: "south" | "north";
  ply: number;
  last_move: { by: "south" | "north"; pit: number; captured: number } | null;
}

export function buildFrames(game: GameDetail): Frame[] {
  const frames: Frame[] = [];
  frames.push({
    pits: [...game.initial_state.pits],
    stores: { south: game.initial_state.stores[0], north: game.initial_state.stores[1] },
    to_move: game.initial_state.to_move === 0 ? "south" : "north",
    ply: 0,
    last_move: null,
  });
  for (const m of game.moves) {
    frames.push({
      pits: [...m.pits_after],
      stores: { south: m.store_south_after, north: m.store_north_after },
      to_move: m.side === "south" ? "north" : "south",
      ply: m.ply + 1,
      last_move: { by: m.side, pit: m.action, captured: m.captured },
    });
  }
  return frames;
}

export type Scope = "mine" | "all";
export type Kind = "human" | "match" | "all";

export interface GamesResponse {
  total: number;
  page: number;
  page_size: number;
  items: GameListEntry[];
}

export async function fetchGames(scope: Scope = "mine", kind: Kind = "all", page = 1): Promise<GamesResponse> {
  const r = await fetch(apiUrl(`/games?scope=${scope}&kind=${kind}&page=${page}&page_size=24`), { credentials: "include" });
  if (!r.ok) return { total: 0, page, page_size: 24, items: [] };
  return r.json();
}

export async function fetchGame(
  id: string,
  scope: Scope = "mine",
): Promise<GameDetail | null> {
  const r = await fetch(apiUrl(`/games/${id}?scope=${scope}`), { credentials: "include" });
  if (!r.ok) return null;
  return r.json();
}

export interface StatsByAgent {
  agent_id: string;
  games: number;
  human_wins: number;
  agent_wins: number;
  draws: number;
  resigns: number;
  avg_plies: number;
  avg_seeds_captured: number;
}

export interface StatsByReason {
  reason: string;
  games: number;
}

export interface RecentStatsGame {
  game_id: string;
  agent_id: string;
  opponent_agent_id: string | null;
  winner: "south" | "north" | "draw" | null;
  reason: string;
  plies: number;
  south: number;
  north: number;
  created_at: number;
}

export interface LeaderboardEntry {
  south: string;
  north: string;
  games: number;
  south_wins: number;
  north_wins: number;
  draws: number;
  avg_plies: number;
}

export interface StandingsEntry {
  agent: string;
  games: number;
  wins: number;
  losses: number;
  draws: number;
  win_pct: number;
  avg_plies: number;
}

export interface Stats {
  scope: Scope;
  kind: Kind;
  totals: {
    games: number;
    avg_plies: number;
    human_wins: number;
    draws: number;
    agent_wins: number;
    unique_clients: number;
  };
  by_agent: StatsByAgent[];
  by_reason: StatsByReason[];
  leaderboard: LeaderboardEntry[];
  standings: StandingsEntry[];
  recent: RecentStatsGame[];
}

export async function fetchStats(scope: Scope = "all", kind: Kind = "human"): Promise<Stats | null> {
  const r = await fetch(apiUrl(`/stats?scope=${scope}&kind=${kind}`), { credentials: "include" });
  if (!r.ok) return null;
  const data = await r.json();
  // guard against older server responses missing these fields
  data.standings = data.standings ?? [];
  data.leaderboard = data.leaderboard ?? [];
  return data;
}
