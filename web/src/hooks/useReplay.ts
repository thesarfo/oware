import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Frame, GameDetail } from "../lib/games";
import { buildFrames } from "../lib/games";

export interface ReplayView {
  frames: Frame[];
  ply: number;
  total: number;
  frame: Frame;
  playing: boolean;
  speedMs: number;
  setPly: (n: number) => void;
  stepBack: () => void;
  stepForward: () => void;
  toStart: () => void;
  toEnd: () => void;
  togglePlay: () => void;
  setSpeed: (ms: number) => void;
}

export function useReplay(
  game: GameDetail | null,
  initialSpeedMs = 600,
  blocked = false,
  autoplay = false,
): ReplayView {
  const frames = useMemo(() => (game ? buildFrames(game) : []), [game]);
  const [ply, setPlyState] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speedMs, setSpeedMs] = useState(initialSpeedMs);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    setPlyState(0);
    if (autoplay && game !== null && (game.moves.length ?? 0) > 0) {
      // Small breath so the user sees the initial position before playback starts.
      const t = window.setTimeout(() => setPlaying(true), 500);
      return () => window.clearTimeout(t);
    }
    setPlaying(false);
    return undefined;
  }, [game?.game_id, autoplay]);

  useEffect(() => {
    if (!playing || blocked) {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      return;
    }
    if (ply >= frames.length - 1) {
      setPlaying(false);
      return;
    }
    timerRef.current = window.setTimeout(() => setPlyState((p) => p + 1), speedMs);
    return () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    };
  }, [playing, blocked, ply, frames.length, speedMs]);

  const setPly = useCallback(
    (n: number) => {
      const max = Math.max(0, frames.length - 1);
      setPlyState(Math.max(0, Math.min(max, n)));
    },
    [frames.length],
  );

  return {
    frames,
    ply,
    total: Math.max(0, frames.length - 1),
    frame: frames[ply] ?? { pits: [], stores: { south: 0, north: 0 }, to_move: "south", ply: 0, last_move: null },
    playing,
    speedMs,
    setPly,
    stepBack: () => setPly(ply - 1),
    stepForward: () => setPly(ply + 1),
    toStart: () => setPly(0),
    toEnd: () => setPly(frames.length - 1),
    togglePlay: () => setPlaying((p) => !p),
    setSpeed: setSpeedMs,
  };
}
