import { useEffect, useState } from "react";
import { Footer } from "../components/Footer";
import { MuteToggle } from "../components/MuteToggle";
import { ScopeToggle } from "../components/ScopeToggle";
import { fetchStats, type Scope, type Stats, type StatsByAgent } from "../lib/games";
import { useHashRoute } from "../hooks/useHashRoute";

interface Props {
  scope: Scope;
}

function pct(n: number, d: number): string {
  if (d === 0) return "—";
  return `${Math.round((n / d) * 100)}%`;
}

function timeAgo(ms: number | null): string {
  if (!ms) return "—";
  const s = Math.floor((Date.now() - ms) / 1000);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}

function Bar({ wins, draws, losses }: { wins: number; draws: number; losses: number }) {
  const total = wins + draws + losses;
  if (total === 0) return <div className="h-2 w-full rounded-full bg-line/40" />;
  const w = (wins / total) * 100;
  const d = (draws / total) * 100;
  const l = (losses / total) * 100;
  return (
    <div className="flex h-2 w-full overflow-hidden rounded-full bg-line/30 dark:bg-dark-line/30">
      <div className="bg-[var(--store-player-stroke)]" style={{ width: `${w}%` }} />
      <div className="bg-muted/50 dark:bg-dark-muted/40" style={{ width: `${d}%` }} />
      <div className="bg-[var(--store-agent-stroke)]" style={{ width: `${l}%` }} />
    </div>
  );
}

function AgentCard({ a }: { a: StatsByAgent }) {
  const winrate = a.games ? Math.round((a.human_wins / a.games) * 100) : 0;
  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-line bg-white/40 p-4 dark:border-dark-line dark:bg-white/0">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-sm font-medium">{a.agent_id}</span>
        <span className="font-mono text-[10px] uppercase tracking-wider text-muted dark:text-dark-muted">
          {a.games} games
        </span>
      </div>
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-3xl font-medium tabular-nums">{winrate}%</span>
        <span className="font-mono text-[11px] text-muted dark:text-dark-muted">human winrate</span>
      </div>
      <Bar wins={a.human_wins} draws={a.draws} losses={a.agent_wins} />
      <div className="flex justify-between font-mono text-[10px] text-muted dark:text-dark-muted">
        <span>you {a.human_wins}</span>
        <span>draw {a.draws}</span>
        <span>agent {a.agent_wins}</span>
      </div>
      <div className="mt-1 flex justify-between border-t border-line pt-2 font-mono text-[10px] text-muted dark:border-dark-line dark:text-dark-muted">
        <span>avg plies {a.avg_plies}</span>
        <span>avg captures {a.avg_seeds_captured}</span>
      </div>
    </div>
  );
}

export function StatsPage({ scope }: Props) {
  const [, navigate] = useHashRoute();
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    setStats(null);
    fetchStats(scope).then(setStats);
  }, [scope]);

  return (
    <div className="min-h-screen bg-white text-ink dark:bg-dark-bg dark:text-dark-ink">
      <header className="flex items-center justify-between px-6 py-4">
        <button
          onClick={() => navigate(`/games?scope=${scope}`)}
          className="rounded-lg border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted transition-colors hover:border-ink hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink"
        >
          ← games
        </button>
        <h1 className="font-mono text-base font-semibold uppercase tracking-widest">
          Analytics
        </h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate("/")}
            className="rounded-lg border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted hover:border-ink hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink"
          >
            play
          </button>
          <MuteToggle />
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-12">
        <div className="mb-6 flex items-center justify-between">
          <ScopeToggle
            scope={scope}
            onChange={(s) => navigate(`/stats?scope=${s}`)}
          />
          <span className="font-mono text-[11px] text-muted dark:text-dark-muted">
            {scope === "mine" ? "your games only" : "every recorded game"}
          </span>
        </div>

        {stats === null && (
          <div className="pt-20 text-center font-mono text-xs text-muted dark:text-dark-muted">
            loading…
          </div>
        )}

        {stats !== null && stats.totals.games === 0 && (
          <div className="pt-20 text-center font-mono text-sm text-muted dark:text-dark-muted">
            {scope === "mine"
              ? "No completed games yet. Play one and come back."
              : "No completed games recorded."}
          </div>
        )}

        {stats !== null && stats.totals.games > 0 && (
          <div className="flex flex-col gap-8">
            {/* Headline numbers */}
            <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <StatCard label="games" value={String(stats.totals.games)} />
              <StatCard
                label="human winrate"
                value={pct(stats.totals.human_wins, stats.totals.games)}
              />
              <StatCard label="avg plies" value={String(stats.totals.avg_plies)} />
              <StatCard
                label={scope === "all" ? "unique players" : "draw rate"}
                value={
                  scope === "all"
                    ? String(stats.totals.unique_clients)
                    : pct(stats.totals.draws, stats.totals.games)
                }
              />
            </section>

            {/* Outcome distribution */}
            <section className="rounded-2xl border border-line bg-white/40 p-5 dark:border-dark-line dark:bg-white/0">
              <h2 className="mb-3 font-mono text-xs uppercase tracking-wide text-muted dark:text-dark-muted">
                Outcomes
              </h2>
              <Bar
                wins={stats.totals.human_wins}
                draws={stats.totals.draws}
                losses={stats.totals.agent_wins}
              />
              <div className="mt-2 flex justify-between font-mono text-[11px] text-muted dark:text-dark-muted">
                <span>
                  you won {stats.totals.human_wins} ·{" "}
                  {pct(stats.totals.human_wins, stats.totals.games)}
                </span>
                <span>
                  draws {stats.totals.draws} ·{" "}
                  {pct(stats.totals.draws, stats.totals.games)}
                </span>
                <span>
                  agent won {stats.totals.agent_wins} ·{" "}
                  {pct(stats.totals.agent_wins, stats.totals.games)}
                </span>
              </div>

              {stats.by_reason.length > 0 && (
                <div className="mt-4 border-t border-line pt-3 dark:border-dark-line">
                  <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-muted dark:text-dark-muted">
                    by end reason
                  </div>
                  <div className="flex flex-wrap gap-2 font-mono text-[11px]">
                    {stats.by_reason.map((r) => (
                      <span
                        key={r.reason}
                        className="rounded-full border border-line px-2.5 py-0.5 text-muted dark:border-dark-line dark:text-dark-muted"
                      >
                        {r.reason} <span className="text-ink dark:text-dark-ink">{r.games}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </section>

            {/* Per-agent breakdown */}
            <section>
              <h2 className="mb-3 font-mono text-xs uppercase tracking-wide text-muted dark:text-dark-muted">
                Per opponent
              </h2>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {stats.by_agent.map((a) => (
                  <AgentCard key={a.agent_id} a={a} />
                ))}
              </div>
            </section>

            {/* Recent games */}
            <section className="rounded-2xl border border-line bg-white/40 p-6 dark:border-dark-line dark:bg-white/0">
              <h2 className="mb-4 font-mono text-xs uppercase tracking-wide text-muted dark:text-dark-muted">
                Recent
              </h2>
              <div className="flex flex-col gap-1">
                {stats.recent.map((r) => {
                  const outcomeText =
                    r.winner === "south"
                      ? "you won"
                      : r.winner === "north"
                        ? "you lost"
                        : r.winner === "draw"
                          ? "draw"
                          : r.reason;
                  const outcomeTone =
                    r.winner === "south"
                      ? "text-[var(--store-player-stroke)]"
                      : r.winner === "north"
                        ? "text-[var(--store-agent-stroke)]"
                        : "text-muted dark:text-dark-muted";
                  return (
                    <button
                      key={r.game_id}
                      onClick={() => navigate(`/games/${r.game_id}?scope=${scope}`)}
                      className="grid grid-cols-[10rem_minmax(0,1fr)_auto] items-baseline gap-x-6 rounded-lg px-3 py-2.5 text-left font-mono text-[11px] transition-colors hover:bg-ink/5 dark:hover:bg-dark-ink/10"
                    >
                      <span className="truncate text-ink dark:text-dark-ink">
                        vs {r.agent_id}
                      </span>
                      <span className={`truncate ${outcomeTone}`}>{outcomeText}</span>
                      <span className="tabular-nums text-muted dark:text-dark-muted">
                        {r.south}–{r.north}
                        <span className="mx-1.5 opacity-50">·</span>
                        {r.plies}p
                        <span className="mx-1.5 opacity-50">·</span>
                        {timeAgo(r.created_at)}
                      </span>
                    </button>
                  );
                })}
              </div>
            </section>
          </div>
        )}

        <Footer className="mt-10" />
      </main>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-line bg-white/40 p-4 dark:border-dark-line dark:bg-white/0">
      <div className="font-mono text-[10px] uppercase tracking-wider text-muted dark:text-dark-muted">
        {label}
      </div>
      <div className="mt-1 font-mono text-3xl font-medium tabular-nums">{value}</div>
    </div>
  );
}
