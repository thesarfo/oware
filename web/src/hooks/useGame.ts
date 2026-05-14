import { useCallback, useEffect, useRef, useState } from "react";
import { wsUrl } from "../lib/api";
import type { AgentMoveMsg, GameOver, GameState, ServerMessage } from "../lib/protocol";

export type ConnState = "connecting" | "open" | "closed";

export interface GameView {
  conn: ConnState;
  state: GameState | null;
  agent: { id: string; name: string } | null;
  northAgent: { id: string; name: string } | null;
  thinking: boolean;
  lastAgentMove: AgentMoveMsg | null;
  result: GameOver | null;
  analysing: boolean;
  error: string | null;
  newGame: (agentId: string, humanPlays: "south" | "north", seed?: number) => void;
  newMatch: (
    southAgentId: string,
    northAgentId: string,
    stepDelayMs?: number,
    seed?: number,
  ) => void;
  sendMove: (pit: number) => void;
  resign: () => void;
}

const WS_URL = wsUrl("/play");

export function useGame(): GameView {
  const wsRef = useRef<WebSocket | null>(null);
  const [conn, setConn] = useState<ConnState>("connecting");
  const [state, setState] = useState<GameState | null>(null);
  const [agent, setAgent] = useState<{ id: string; name: string } | null>(null);
  const [northAgent, setNorthAgent] = useState<{ id: string; name: string } | null>(null);
  const [thinking, setThinking] = useState(false);
  const [lastAgentMove, setLastAgentMove] = useState<AgentMoveMsg | null>(null);
  const [result, setResult] = useState<GameOver | null>(null);
  const [analysing, setAnalysing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    ws.onopen = () => setConn("open");
    ws.onclose = () => setConn("closed");
    ws.onerror = () => setConn("closed");
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data) as ServerMessage;
      switch (msg.type) {
        case "game_started":
          setAgent(msg.agent);
          setNorthAgent(msg.north_agent ?? null);
          setState(msg.state);
          setResult(null);
          setLastAgentMove(null);
          setThinking(false);
          setError(null);
          break;
        case "state":
          setState(msg);
          setThinking(false);
          break;
        case "agent_thinking":
          setThinking(true);
          break;
        case "agent_move":
          setLastAgentMove(msg);
          break;
        case "game_over":
          setResult(msg);
          setThinking(false);
          setAnalysing(true);
          break;
        case "game_analysis":
          setResult((prev) => prev ? { ...prev, history: msg.history } : prev);
          setAnalysing(false);
          break;
        case "error":
          if (msg.code !== "game_over") setError(msg.message);
          break;
        case "pong":
          break;
      }
    };
    return () => ws.close();
  }, []);

  const send = useCallback((payload: object) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
    }
  }, []);

  const newGame = useCallback(
    (agentId: string, humanPlays: "south" | "north", seed?: number) => {
      setState(null);
      setResult(null);
      setAnalysing(false);
      setError(null);
      setNorthAgent(null);
      send({ type: "new_game", agent_id: agentId, human_plays: humanPlays, seed });
    },
    [send],
  );

  const newMatch = useCallback(
    (
      southAgentId: string,
      northAgentId: string,
      stepDelayMs = 600,
      seed?: number,
    ) => {
      setState(null);
      setResult(null);
      setAnalysing(false);
      setError(null);
      send({
        type: "new_match",
        south_agent_id: southAgentId,
        north_agent_id: northAgentId,
        step_delay_ms: stepDelayMs,
        seed,
      });
    },
    [send],
  );

  const sendMove = useCallback(
    (pit: number) => {
      if (!state) return;
      send({ type: "move", game_id: state.game_id, pit });
    },
    [send, state],
  );

  const resign = useCallback(() => {
    if (!state) return;
    send({ type: "resign", game_id: state.game_id });
  }, [send, state]);

  return {
    conn,
    state,
    agent,
    northAgent,
    thinking,
    lastAgentMove,
    result,
    analysing,
    error,
    newGame,
    newMatch,
    sendMove,
    resign,
  };
}
