import { useEffect, useRef, useState } from "react";
import type { Frame } from "../lib/games";
import { thock, tick } from "../lib/audio";

const HOP_MS = 110;
const CAPTURE_MS = 180;
const SETTLE_MS = 120;

export interface AnimatedReplay {
  displayed: Frame;
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

/**
 * Animates frame-to-frame transitions in a replay. When the ply advances by
 * exactly +1, plays the same sow + capture animation that live games use (with
 * sounds). On any other ply change (scrubbing, jumping), it snaps to the new
 * frame without animation.
 */
export function useReplayAnimation(
  frames: Frame[],
  ply: number,
  speedMs: number,
): AnimatedReplay {
  const fallback: Frame = {
    pits: [4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4],
    stores: { south: 0, north: 0 },
    to_move: "south",
    ply: 0,
    last_move: null,
  };
  const initial = frames[ply] ?? fallback;
  const [displayed, setDisplayed] = useState<Frame>(initial);
  const [flyingPit, setFlyingPit] = useState<number | null>(null);
  const [flyingTo, setFlyingTo] = useState<
    "store-south" | "store-north" | null
  >(null);
  const [animating, setAnimating] = useState(false);

  const prevPlyRef = useRef(ply);
  const cancelledRef = useRef(false);
  const runIdRef = useRef(0);

  useEffect(() => {
    const prev = prevPlyRef.current;
    const next = ply;
    prevPlyRef.current = next;

    const prevFrame = frames[prev];
    const nextFrame = frames[next];

    if (!nextFrame) {
      setDisplayed(fallback);
      return;
    }

    // Only animate the natural forward step. Anything else (jump back, big
    // scrub forward, game change) snaps instantly.
    if (
      next !== prev + 1 ||
      !prevFrame ||
      !nextFrame.last_move
    ) {
      cancelledRef.current = true;
      runIdRef.current += 1;
      setAnimating(false);
      setFlyingPit(null);
      setFlyingTo(null);
      setDisplayed(nextFrame);
      return;
    }

    cancelledRef.current = false;
    const myRunId = ++runIdRef.current;
    void animate(prevFrame, nextFrame, myRunId);
    // We deliberately don't include `frames` in deps; ply is the driver.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ply]);

  async function animate(prev: Frame, next: Frame, runId: number) {
    setAnimating(true);
    const lm = next.last_move!;
    const src = lm.by === "south" ? lm.pit : 6 + lm.pit;
    const seeds = prev.pits[src];
    const path = sowPath(src, seeds);

    const pits = [...prev.pits];
    const stores = { ...prev.stores };
    pits[src] = 0;
    setDisplayed({ ...prev, pits: [...pits], last_move: lm });
    setFlyingPit(src);

    // Tighten timing at higher playback speed so the animation fits the tick.
    const speedScale = Math.min(1, speedMs / 600);
    const hop = Math.max(40, HOP_MS * speedScale);
    const settle = Math.max(40, SETTLE_MS * speedScale);
    const cap = Math.max(80, CAPTURE_MS * speedScale);

    await sleep(60);
    if (cancelledRef.current || runIdRef.current !== runId) return;

    for (const dest of path) {
      setFlyingPit(dest);
      await sleep(hop);
      if (cancelledRef.current || runIdRef.current !== runId) return;
      pits[dest] += 1;
      setDisplayed({
        ...prev,
        pits: [...pits],
        stores: { ...stores },
        last_move: lm,
      });
      tick();
    }
    setFlyingPit(null);
    await sleep(settle);
    if (cancelledRef.current || runIdRef.current !== runId) return;

    const captures: number[] = [];
    for (let i = 0; i < 12; i++) {
      if (pits[i] > 0 && next.pits[i] === 0) captures.push(i);
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
      setDisplayed({
        ...prev,
        pits: [...pits],
        stores: { ...stores },
        last_move: lm,
      });
      thock();
      await sleep(cap);
      if (cancelledRef.current || runIdRef.current !== runId) return;
    }
    setFlyingTo(null);
    setFlyingPit(null);
    setDisplayed(next);
    setAnimating(false);
  }

  return { displayed, flyingPit, flyingTo, animating };
}
