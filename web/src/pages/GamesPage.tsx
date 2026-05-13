import { useEffect, useMemo, useState } from "react";
import { BoardView } from "../components/BoardView";
import { Footer } from "../components/Footer";
import { MuteToggle } from "../components/MuteToggle";
import { ScopeToggle } from "../components/ScopeToggle";
import { fetchGames, type GameListEntry, type Scope } from "../lib/games";
import { useHashRoute } from "../hooks/useHashRoute";

type OutcomeFilter = "any" | "won" | "lost" | "draw";
type AgentFilter = "any" | string;
type ReasonFilter = "any" | string;

function timeAgo(ms: number | null): string {
  if (!ms) return "—";
  const s = Math.floor((Date.now() - ms) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

type Tone = "win" | "loss" | "draw" | "neutral";

function outcome(g: GameListEntry): { text: string; tone: Tone } {
  if (g.winner === "draw") return { text: "draw", tone: "draw" };
  if (g.winner === "south") return { text: "you won", tone: "win" };
  if (g.winner === "north") return { text: "you lost", tone: "loss" };
  return { text: g.reason, tone: "neutral" };
}

function finalFrame(g: GameListEntry) {
  const pits =
    Array.isArray(g.final_pits) && g.final_pits.length === 12
      ? g.final_pits
      : Array(12).fill(0);
  return {
    pits,
    stores: g.final_stores ?? { south: 0, north: 0 },
    last_move: null,
  };
}

const TONE_CLASS: Record<Tone, string> = {
  win: "text-[var(--store-player-stroke)]",
  loss: "text-[var(--store-agent-stroke)]",
  draw: "text-muted dark:text-dark-muted",
  neutral: "text-muted dark:text-dark-muted",
};

interface Props {
  scope: Scope;
}

export function GamesPage({ scope }: Props) {
  const [, navigate] = useHashRoute();
  const [games, setGames] = useState<GameListEntry[] | null>(null);
  const [outcomeFilter, setOutcomeFilter] = useState<OutcomeFilter>("any");
  const [agentFilter, setAgentFilter] = useState<AgentFilter>("any");
  const [reasonFilter, setReasonFilter] = useState<ReasonFilter>("any");

  useEffect(() => {
    setGames(null);
    setOutcomeFilter("any");
    setAgentFilter("any");
    setReasonFilter("any");
    fetchGames(scope).then(setGames);
  }, [scope]);

  const agentOptions = useMemo(() => {
    if (!games) return [];
    return Array.from(new Set(games.map((g) => g.agent_id))).sort();
  }, [games]);
  const reasonOptions = useMemo(() => {
    if (!games) return [];
    return Array.from(new Set(games.map((g) => g.reason))).sort();
  }, [games]);

  const filtered = useMemo(() => {
    if (!games) return null;
    return games.filter((g) => {
      if (agentFilter !== "any" && g.agent_id !== agentFilter) return false;
      if (reasonFilter !== "any" && g.reason !== reasonFilter) return false;
      if (outcomeFilter === "won" && g.winner !== "south") return false;
      if (outcomeFilter === "lost" && g.winner !== "north") return false;
      if (outcomeFilter === "draw" && g.winner !== "draw") return false;
      return true;
    });
  }, [games, agentFilter, reasonFilter, outcomeFilter]);

  const filtersActive =
    outcomeFilter !== "any" || agentFilter !== "any" || reasonFilter !== "any";

  return (
    <div className="min-h-screen bg-white text-ink dark:bg-dark-bg dark:text-dark-ink">
      <header className="flex items-center justify-between px-6 py-4">
        <button
          onClick={() => navigate("/")}
          className="rounded-lg border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted transition-colors hover:border-ink hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink"
        >
          ← play
        </button>
        <h1 className="font-mono text-base font-semibold uppercase tracking-widest">
          Game history
        </h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate(`/stats?scope=${scope}`)}
            className="rounded-lg border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted transition-colors hover:border-ink hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink"
          >
            stats →
          </button>
          <MuteToggle />
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-10">
        <div className="mb-4 flex items-center justify-between gap-4">
          <ScopeToggle
            scope={scope}
            onChange={(s) => navigate(`/games?scope=${s}`)}
          />
          <span className="font-mono text-[11px] text-muted dark:text-dark-muted">
            {filtered === null
              ? ""
              : filtersActive
                ? `${filtered.length} of ${games?.length ?? 0}`
                : `${filtered.length} ${scope === "mine" ? "of yours" : "across all players"}`}
          </span>
        </div>

        {games !== null && games.length > 0 && (
          <div className="mb-6 flex flex-col gap-2.5">
            <FilterRow
              label="outcome"
              options={[
                { value: "any", label: "any" },
                { value: "won", label: "won" },
                { value: "lost", label: "lost" },
                { value: "draw", label: "draw" },
              ]}
              value={outcomeFilter}
              onChange={(v) => setOutcomeFilter(v as OutcomeFilter)}
            />
            <FilterRow
              label="opponent"
              options={[
                { value: "any", label: "any" },
                ...agentOptions.map((a) => ({ value: a, label: a })),
              ]}
              value={agentFilter}
              onChange={setAgentFilter}
            />
            <FilterRow
              label="end reason"
              options={[
                { value: "any", label: "any" },
                ...reasonOptions.map((r) => ({ value: r, label: r })),
              ]}
              value={reasonFilter}
              onChange={setReasonFilter}
            />
            {filtersActive && (
              <button
                onClick={() => {
                  setOutcomeFilter("any");
                  setAgentFilter("any");
                  setReasonFilter("any");
                }}
                className="self-start font-mono text-[10px] uppercase tracking-wider text-muted underline-offset-2 hover:text-ink hover:underline dark:text-dark-muted dark:hover:text-dark-ink"
              >
                clear filters
              </button>
            )}
          </div>
        )}

        {games === null && (
          <div className="flex justify-center pt-20 font-mono text-xs text-muted dark:text-dark-muted">
            loading…
          </div>
        )}
        {games !== null && games.length === 0 && (
          <div className="flex justify-center pt-20 font-mono text-sm text-muted dark:text-dark-muted">
            {scope === "mine"
              ? "No completed games yet. Finish one on the play page and it'll appear here."
              : "No completed games recorded yet."}
          </div>
        )}
        {filtered !== null && games !== null && games.length > 0 && filtered.length === 0 && (
          <div className="flex justify-center pt-12 font-mono text-sm text-muted dark:text-dark-muted">
            No games match the current filters.
          </div>
        )}

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {filtered?.map((g) => {
            const out = outcome(g);
            return (
              <button
                key={g.game_id}
                onClick={() => navigate(`/games/${g.game_id}?scope=${scope}`)}
                className="group flex flex-col gap-3 overflow-hidden rounded-2xl border border-line bg-white/40 p-4 text-left transition-colors hover:border-ink dark:border-dark-line dark:bg-white/0 dark:hover:border-dark-muted"
              >
                <div className="flex items-baseline justify-between font-mono text-[11px]">
                  <span className="text-ink dark:text-dark-ink">vs {g.agent_id}</span>
                  <span className="text-muted dark:text-dark-muted">{timeAgo(g.ended_at)}</span>
                </div>
                <div className="rounded-xl bg-canvas/40 p-2 dark:bg-dark-bg/40">
                  <BoardView frame={finalFrame(g)} />
                </div>
                <div className="flex items-baseline justify-between font-mono text-[11px]">
                  <span className={`uppercase tracking-wider ${TONE_CLASS[out.tone]}`}>
                    {out.text}
                  </span>
                  <span className="text-muted dark:text-dark-muted">
                    {g.final_stores?.south ?? 0}–{g.final_stores?.north ?? 0} · {g.plies}p
                  </span>
                </div>
                <div className="flex items-baseline justify-between font-mono text-[10px] text-muted dark:text-dark-muted">
                  <span>{g.reason}</span>
                  <span className="uppercase tracking-wider opacity-0 transition-opacity group-hover:opacity-100">
                    replay →
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        <Footer className="mt-10" />
      </main>
    </div>
  );
}

function FilterRow({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-24 shrink-0 font-mono text-[10px] uppercase tracking-wider text-muted dark:text-dark-muted">
        {label}
      </span>
      <div className="flex flex-wrap gap-1.5">
        {options.map((o) => {
          const active = o.value === value;
          return (
            <button
              key={o.value}
              onClick={() => onChange(o.value)}
              className={`rounded-full border px-2.5 py-0.5 font-mono text-[11px] transition-colors ${
                active
                  ? "border-ink bg-ink text-white dark:border-dark-ink dark:bg-dark-ink dark:text-dark-bg"
                  : "border-line text-muted hover:border-muted hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink"
              }`}
            >
              {o.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
