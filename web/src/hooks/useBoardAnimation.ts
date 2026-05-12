import { useEffect, useRef, useState } from "react";
import type { GameState, Side } from "../lib/protocol";
import { thock, tick } from "../lib/audio";

const HOP_MS = 110;
const CAPTURE_MS = 180;
const SETTLE_MS = 120;

export interface AnimatedBoard {
  displayed: GameState | null;
  flyingPit: number | null;
  flyingTo: "store-south" | "store-north" | null;
  animating: boolean;
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function sowPath(src: number, seeds: number): number[] {
  const path: number[] = [];
  let idx = src;
  while (path.length < seeds) {
    idx = (idx + 1) % 12;
    if (idx === src) continue;
    path.push(idx);
  }
  return path;
}

function absFromAction(action: number, by: Side): number {
  return by === "south" ? action : 6 + action;
}

export function useBoardAnimation(latest: GameState | null): AnimatedBoard {
  const [displayed, setDisplayed] = useState<GameState | null>(latest);
  const [flyingPit, setFlyingPit] = useState<number | null>(null);
  const [flyingTo, setFlyingTo] = useState<"store-south" | "store-north" | null>(null);
  const [animating, setAnimating] = useState(false);

  const queue = useRef<GameState[]>([]);
  const running = useRef(false);
  const current = useRef<GameState | null>(latest);
  const cancelled = useRef(false);

  useEffect(() => {
    if (latest === null) {
      cancelled.current = true;
      queue.current = [];
      running.current = false;
      current.current = null;
      setDisplayed(null);
      setFlyingPit(null);
      setFlyingTo(null);
      setAnimating(false);
      return;
    }
    if (current.current === null || current.current.game_id !== latest.game_id) {
      cancelled.current = true;
      queue.current = [];
      running.current = false;
      current.current = latest;
      setDisplayed(latest);
      setFlyingPit(null);
      setFlyingTo(null);
      setAnimating(false);
      return;
    }
    if (latest.ply <= current.current.ply) return;
    queue.current.push(latest);
    if (!running.current) {
      cancelled.current = false;
      void run();
    }
  }, [latest]);

  async function run() {
    running.current = true;
    setAnimating(true);
    while (queue.current.length > 0 && !cancelled.current) {
      const target = queue.current.shift()!;
      await animateOne(current.current!, target);
      if (cancelled.current) break;
      current.current = target;
    }
    running.current = false;
    setAnimating(false);
    setFlyingPit(null);
    setFlyingTo(null);
  }

  async function animateOne(from: GameState, to: GameState) {
    const lm = to.last_move;
    if (!lm) {
      setDisplayed(to);
      return;
    }
    const src = absFromAction(lm.pit, lm.by);
    const seeds = from.pits[src];
    const path = sowPath(src, seeds);

    const pits = [...from.pits];
    const stores = { ...from.stores };
    pits[src] = 0;
    setDisplayed({ ...from, pits: [...pits] });
    setFlyingPit(src);
    await sleep(60);
    if (cancelled.current) return;

    for (const dest of path) {
      setFlyingPit(dest);
      await sleep(HOP_MS);
      if (cancelled.current) return;
      pits[dest] += 1;
      setDisplayed({ ...from, pits: [...pits], stores: { ...stores } });
      tick();
    }
    setFlyingPit(null);
    await sleep(SETTLE_MS);
    if (cancelled.current) return;

    const captures: number[] = [];
    for (let i = 0; i < 12; i++) {
      if (pits[i] > 0 && to.pits[i] === 0) captures.push(i);
    }
    const moverStore: "store-south" | "store-north" =
      lm.by === "south" ? "store-south" : "store-north";

    for (const c of captures) {
      setFlyingTo(moverStore);
      setFlyingPit(c);
      const gained = pits[c];
      pits[c] = 0;
      if (lm.by === "south") stores.south += gained;
      else stores.north += gained;
      setDisplayed({ ...from, pits: [...pits], stores: { ...stores } });
      thock();
      await sleep(CAPTURE_MS);
      if (cancelled.current) return;
    }
    setFlyingTo(null);
    setFlyingPit(null);
    setDisplayed(to);
  }

  return { displayed, flyingPit, flyingTo, animating };
}
