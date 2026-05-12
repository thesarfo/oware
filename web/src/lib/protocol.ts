export type Side = "south" | "north";

export type EndReason = "majority" | "must_feed" | "no_progress" | "resign" | "disconnect";

export interface Stores {
  south: number;
  north: number;
}

export interface LastMove {
  by: Side;
  pit: number;
  captured: number;
}

export interface GameState {
  type: "state";
  game_id: string;
  pits: number[];
  stores: Stores;
  to_move: Side;
  ply: number;
  legal_moves: number[];
  last_move: LastMove | null;
}

export interface AgentBrief {
  id: string;
  name: string;
}

export interface GameStarted {
  type: "game_started";
  game_id: string;
  agent: AgentBrief;
  state: GameState;
}

export interface AgentThinking {
  type: "agent_thinking";
  game_id: string;
  since: number;
}

export interface AgentMoveMsg {
  type: "agent_move";
  game_id: string;
  pit: number;
  thought_ms: number;
  extras: Record<string, unknown>;
}

export interface GameOver {
  type: "game_over";
  game_id: string;
  winner: Side | "draw";
  reason: EndReason;
  final_stores: Stores;
}

export interface ErrorMsg {
  type: "error";
  code: string;
  message: string;
}

export type ServerMessage =
  | GameStarted
  | GameState
  | AgentThinking
  | AgentMoveMsg
  | GameOver
  | ErrorMsg
  | { type: "pong"; t: number };

export interface AgentEntry {
  id: string;
  name: string;
  family: string;
  description: string;
  est_elo: number | null;
}
