import { useEffect, useState } from "react";
import { BoardView } from "../components/BoardView";
import { Footer } from "../components/Footer";
import { MuteToggle } from "../components/MuteToggle";
import { fetchGame, type GameDetail, type GameMove, type Scope } from "../lib/games";
import { useHashRoute } from "../hooks/useHashRoute";
import { useReplay } from "../hooks/useReplay";
import { useReplayAnimation } from "../hooks/useReplayAnimation";
import { primeAudio } from "../lib/audio";
import { humanPit } from "../lib/pit";

interface Props {
  gameId: string;
  scope: Scope;
}

const SPEEDS = [
  { label: "1×", ms: 1200 },
  { label: "1.5×", ms: 800 },
  { label: "2×", ms: 500 },
  { label: "4×", ms: 250 },
];

export function ReplayPage({ gameId, scope }: Props) {
  const [, navigate] = useHashRoute();
  const [game, setGame] = useState<GameDetail | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    fetchGame(gameId, scope).then((g) => {
      if (g === null) setMissing(true);
      else setGame(g);
    });
  }, [gameId, scope]);

  useEffect(() => {
    const handler = () => primeAudio();
    window.addEventListener("pointerdown", handler, { once: true });
    return () => window.removeEventListener("pointerdown", handler);
  }, []);

  // animating state needs to gate autoplay → declared before useReplay
  // but useReplayAnimation needs frames → so we accept the dance: animating is
  // false on initial render, then the useEffect inside replay-animation flips it.
  const [animating, setAnimating] = useState(false);
  const replay = useReplay(game, 800, animating, true);
  const anim = useReplayAnimation(replay.frames, replay.ply, replay.speedMs);

  useEffect(() => {
    setAnimating(anim.animating);
  }, [anim.animating]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") replay.stepBack();
      else if (e.key === "ArrowRight") replay.stepForward();
      else if (e.key === " ") {
        e.preventDefault();
        replay.togglePlay();
      } else if (e.key === "Home") replay.toStart();
      else if (e.key === "End") replay.toEnd();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [replay]);

  if (missing) {
    return (
      <div className="flex h-screen items-center justify-center bg-white font-mono text-sm text-muted dark:bg-dark-bg dark:text-dark-muted">
        game not found —{" "}
        <button onClick={() => navigate(`/games?scope=${scope}`)} className="ml-2 underline">
          back
        </button>
      </div>
    );
  }
  if (game === null) {
    return (
      <div className="flex h-screen items-center justify-center bg-white font-mono text-xs text-muted dark:bg-dark-bg dark:text-dark-muted">
        loading game…
      </div>
    );
  }

  const currentMove: GameMove | null =
    replay.ply > 0 ? game.moves[replay.ply - 1] ?? null : null;

  // Hint is for the *upcoming* move from the displayed frame's side-to-move,
  // i.e. the next move in history. So at ply N, show what AZ thought of move N+1.
  const upcomingMove: GameMove | null = game.moves[replay.ply] ?? null;
  const hintPit =
    upcomingMove && upcomingMove.side === "south" && upcomingMove.az_hint !== null
      ? upcomingMove.az_hint
      : null;

  const hintMismatch =
    currentMove &&
    currentMove.side === "south" &&
    currentMove.az_hint !== null &&
    currentMove.az_hint !== currentMove.action;

  return (
    <div className="min-h-screen bg-white text-ink dark:bg-dark-bg dark:text-dark-ink">
      <header className="flex items-center justify-between px-6 py-4">
        <button
          onClick={() => navigate(`/games?scope=${scope}`)}
          className="rounded-lg border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted transition-colors hover:border-ink hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink"
        >
          ← all games
        </button>
        <h1 className="font-mono text-base font-semibold uppercase tracking-widest">
          Replay · {game.agent_id}
        </h1>
        <div className="flex items-center gap-2">
          <MuteToggle />
        </div>
      </header>

      <div className="grid grid-cols-1 gap-4 px-6 pb-8 lg:grid-cols-[20rem_1fr_20rem]">
        {/* Left: outcome + per-ply detail */}
        <aside className="flex flex-col gap-3 font-mono text-[11px] leading-tight">
          <div className="rounded-xl border border-line p-3 dark:border-dark-line">
            <div className="text-muted dark:text-dark-muted">Outcome</div>
            <div className="text-base font-medium">
              {game.winner === "draw"
                ? "draw"
                : game.winner === "south"
                  ? "you win"
                  : game.winner === "north"
                    ? "you lose"
                    : "—"}
            </div>
            <div className="mt-0.5 text-muted dark:text-dark-muted">
              {game.final_stores.south}–{game.final_stores.north} · {game.reason}
            </div>
            <div className="mt-1 text-muted dark:text-dark-muted">
              {game.plies} plies
            </div>
          </div>

          <div className="rounded-xl border border-line p-3 dark:border-dark-line">
            <div className="text-muted dark:text-dark-muted">Ply</div>
            <div className="text-base font-medium">
              {replay.ply}{" "}
              <span className="text-muted dark:text-dark-muted">/ {replay.total}</span>
            </div>
            <div className="mt-1 text-muted dark:text-dark-muted">
              {currentMove
                ? `${currentMove.side === "south" ? "you" : game.agent_id} · pit ${humanPit(currentMove.action)}${currentMove.captured ? ` · +${currentMove.captured}` : ""}`
                : "start"}
            </div>
          </div>

          <AnalysisCard
            currentMove={currentMove}
            upcomingMove={upcomingMove}
            agentName={game.agent_id}
          />
        </aside>

        {/* Center: board */}
        <main className="flex flex-col items-center gap-5">
          <div className="w-full max-w-[960px]">
            <BoardView
              frame={anim.displayed}
              flyingPit={anim.flyingPit}
              flyingTo={anim.flyingTo}
              hintPit={hintPit}
            />
          </div>

          <div className="flex min-h-[2.5rem] w-full max-w-[600px] items-center justify-center">
            {hintMismatch && currentMove && (
              <div className="rounded-xl border border-line bg-canvas px-4 py-2 font-mono text-[11px] dark:border-dark-line dark:bg-dark-bg">
                <span className="text-muted dark:text-dark-muted">you played </span>
                <span className="text-ink dark:text-dark-ink">pit {humanPit(currentMove.action)}</span>
                <span className="mx-2 text-muted dark:text-dark-muted">·</span>
                <span className="text-muted dark:text-dark-muted">az would have played </span>
                <span className="text-ink dark:text-dark-ink">pit {humanPit(currentMove.az_hint)}</span>
              </div>
            )}
          </div>

          {/* Scrubber + transport */}
          <div className="flex w-full max-w-[600px] flex-col gap-3">
            <input
              type="range"
              min={0}
              max={replay.total}
              value={replay.ply}
              onChange={(e) => replay.setPly(Number(e.target.value))}
              className="w-full accent-ink"
              aria-label="ply scrubber"
            />
            <div className="flex flex-wrap items-center justify-center gap-2">
              <Transport onClick={replay.toStart} label="⏮" />
              <Transport onClick={replay.stepBack} label="◀" />
              <Transport
                onClick={replay.togglePlay}
                label={replay.playing ? "pause" : "play"}
                wide
              />
              <Transport onClick={replay.stepForward} label="▶" />
              <Transport onClick={replay.toEnd} label="⏭" />
              <div className="flex items-center gap-1 pl-3 font-mono text-[10px] uppercase tracking-wider text-muted dark:text-dark-muted">
                {SPEEDS.map((s) => (
                  <button
                    key={s.label}
                    onClick={() => replay.setSpeed(s.ms)}
                    className={`rounded-md border px-2 py-1 transition-colors ${
                      replay.speedMs === s.ms
                        ? "border-ink text-ink dark:border-dark-ink dark:text-dark-ink"
                        : "border-line hover:border-muted dark:border-dark-line dark:hover:border-dark-muted"
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </main>

        {/* Right: move list */}
        <aside className="flex flex-col gap-2">
          <div className="rounded-xl border border-line bg-white/40 p-3 dark:border-dark-line dark:bg-white/0">
            <div className="mb-2 font-mono text-xs uppercase tracking-wide text-muted dark:text-dark-muted">
              Moves
            </div>
            <div className="max-h-[60vh] space-y-px overflow-y-auto pr-1">
              <MoveListItem
                idx={0}
                active={replay.ply === 0}
                onClick={() => replay.setPly(0)}
                label="start"
              />
              {game.moves.map((m, i) => {
                const idx = i + 1;
                const mismatch =
                  m.side === "south" && m.az_hint !== null && m.az_hint !== m.action;
                return (
                  <MoveListItem
                    key={i}
                    idx={idx}
                    active={replay.ply === idx}
                    onClick={() => replay.setPly(idx)}
                    label={`${m.side === "south" ? "you" : "ai"} · pit ${humanPit(m.action)}`}
                    capture={m.captured ? `+${m.captured}` : ""}
                    mismatch={mismatch}
                  />
                );
              })}
            </div>
          </div>
        </aside>
      </div>

      <Footer className="px-6 pb-6" />
    </div>
  );
}

function Transport({
  onClick,
  label,
  wide,
}: {
  onClick: () => void;
  label: string;
  wide?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-lg border border-line bg-white/40 px-3 py-1.5 font-mono text-[11px] text-ink transition-colors hover:border-ink dark:border-dark-line dark:bg-white/0 dark:text-dark-ink dark:hover:border-dark-muted ${
        wide ? "w-20" : ""
      }`}
    >
      {label}
    </button>
  );
}

function MoveListItem({
  idx,
  active,
  onClick,
  label,
  capture,
  mismatch,
}: {
  idx: number;
  active: boolean;
  onClick: () => void;
  label: string;
  capture?: string;
  mismatch?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full items-baseline justify-between rounded-md px-2 py-1 text-left font-mono text-[11px] transition-colors ${
        active
          ? "bg-ink/10 text-ink dark:bg-dark-ink/20 dark:text-dark-ink"
          : "text-muted hover:bg-ink/5 hover:text-ink dark:text-dark-muted dark:hover:bg-dark-ink/10 dark:hover:text-dark-ink"
      }`}
    >
      <span className="w-6 tabular-nums">{idx}</span>
      <span className="flex-1 px-2">{label}</span>
      <span className="flex items-center gap-1">
        {mismatch && (
          <span
            className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--store-player-stroke)]"
            title="AZ would have played a different pit"
          />
        )}
        <span className="w-8 text-right">{capture ?? ""}</span>
      </span>
    </button>
  );
}

function AnalysisCard({
  currentMove,
  upcomingMove,
  agentName,
}: {
  currentMove: GameMove | null;
  upcomingMove: GameMove | null;
  agentName: string;
}) {
  // Compute aggregate accuracy across the human's moves so far.
  if (!currentMove && !upcomingMove) {
    return (
      <div className="rounded-xl border border-line p-3 font-mono text-[11px] text-muted dark:border-dark-line dark:text-dark-muted">
        <div className="text-muted dark:text-dark-muted">AZ analysis</div>
        <div className="mt-0.5">no moves yet</div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-line p-3 font-mono text-[11px] dark:border-dark-line">
      <div className="text-muted dark:text-dark-muted">AZ analysis</div>
      {currentMove && currentMove.side === "south" && (
        <div className="mt-2 space-y-1">
          <div className="flex justify-between">
            <span className="text-muted dark:text-dark-muted">your move</span>
            <span>pit {humanPit(currentMove.action)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted dark:text-dark-muted">az recommendation</span>
            <span>
              {currentMove.az_hint === null
                ? "—"
                : currentMove.az_hint === currentMove.action
                  ? "matches ✓"
                  : `pit ${humanPit(currentMove.az_hint)}`}
            </span>
          </div>
        </div>
      )}
      {currentMove && currentMove.side === "north" && (
        <div className="mt-2 text-muted dark:text-dark-muted">
          {agentName}'s move — pit {humanPit(currentMove.action)}
        </div>
      )}
      {upcomingMove && upcomingMove.side === "south" && upcomingMove.az_hint !== null && (
        <div className="mt-3 border-t border-line pt-2 text-muted dark:border-dark-line dark:text-dark-muted">
          next ply hint: pit {humanPit(upcomingMove.az_hint)}
        </div>
      )}
    </div>
  );
}
