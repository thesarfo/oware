import { useEffect, useState } from "react";
import { Footer } from "../components/Footer";
import { MuteToggle } from "../components/MuteToggle";
import { PageHeader } from "../components/PageHeader";
import { fetchStats, type LeaderboardEntry, type StandingsEntry, type Stats } from "../lib/games";
import { useHashRoute } from "../hooks/useHashRoute";

function pct(n: number, d: number): string {
  if (d === 0) return "—";
  return `${Math.round((n / d) * 100)}%`;
}

function WinBar({ wins, draws, losses }: { wins: number; draws: number; losses: number }) {
  const total = wins + draws + losses;
  if (total === 0) return <div className="h-1.5 w-full rounded-full bg-line/40" />;
  return (
    <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-line/30 dark:bg-dark-line/30">
      <div className="bg-[var(--store-player-stroke)]" style={{ width: `${(wins / total) * 100}%` }} />
      <div className="bg-muted/40 dark:bg-dark-muted/30" style={{ width: `${(draws / total) * 100}%` }} />
      <div className="bg-[var(--store-agent-stroke)]" style={{ width: `${(losses / total) * 100}%` }} />
    </div>
  );
}

function Standings({ rows }: { rows: StandingsEntry[] }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-line dark:border-dark-line">
      <table className="w-full font-mono text-[11px]">
        <thead>
          <tr className="border-b border-line text-left text-[10px] uppercase tracking-wider text-muted dark:border-dark-line dark:text-dark-muted">
            <th className="px-4 py-3 w-8">#</th>
            <th className="px-4 py-3">agent</th>
            <th className="px-4 py-3 text-right">gp</th>
            <th className="px-4 py-3 text-right text-[var(--store-player-stroke)]">w</th>
            <th className="px-4 py-3 text-right">d</th>
            <th className="px-4 py-3 text-right text-[var(--store-agent-stroke)]">l</th>
            <th className="px-4 py-3 text-right">win%</th>
            <th className="px-4 py-3 min-w-[140px]"></th>
            <th className="px-4 py-3 text-right">avg plies</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={r.agent}
              className="border-b border-line/40 last:border-0 dark:border-dark-line/40 hover:bg-ink/[0.02] dark:hover:bg-dark-ink/[0.04]"
            >
              <td className="px-4 py-3 tabular-nums text-muted dark:text-dark-muted">
                {i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : i + 1}
              </td>
              <td className="px-4 py-3 font-medium text-ink dark:text-dark-ink">{r.agent}</td>
              <td className="px-4 py-3 text-right tabular-nums text-muted dark:text-dark-muted">{r.games}</td>
              <td className="px-4 py-3 text-right tabular-nums text-[var(--store-player-stroke)]">{r.wins}</td>
              <td className="px-4 py-3 text-right tabular-nums text-muted dark:text-dark-muted">{r.draws}</td>
              <td className="px-4 py-3 text-right tabular-nums text-[var(--store-agent-stroke)]">{r.losses}</td>
              <td className="px-4 py-3 text-right tabular-nums font-semibold">{r.win_pct}%</td>
              <td className="px-4 py-3">
                <WinBar wins={r.wins} draws={r.draws} losses={r.losses} />
              </td>
              <td className="px-4 py-3 text-right tabular-nums text-muted dark:text-dark-muted">{r.avg_plies}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MatchupCard({ e }: { e: LeaderboardEntry }) {
  const total = e.south_wins + e.north_wins + e.draws;
  return (
    <div className="rounded-2xl border border-line bg-white/40 p-4 dark:border-dark-line dark:bg-white/0">
      <div className="flex items-center justify-between font-mono text-[11px]">
        <div className="flex items-center gap-2">
          <span className="font-medium text-[var(--store-player-stroke)]">{e.south}</span>
          <span className="text-muted dark:text-dark-muted">vs</span>
          <span className="font-medium text-[var(--store-agent-stroke)]">{e.north}</span>
        </div>
        <span className="text-muted dark:text-dark-muted">{e.games}g · {e.avg_plies}p avg</span>
      </div>
      <div className="mt-2.5">
        <WinBar wins={e.south_wins} draws={e.draws} losses={e.north_wins} />
      </div>
      <div className="mt-1.5 flex justify-between font-mono text-[10px]">
        <span className="text-[var(--store-player-stroke)]">{e.south_wins} ({pct(e.south_wins, total)})</span>
        <span className="text-muted dark:text-dark-muted">draw {e.draws}</span>
        <span className="text-[var(--store-agent-stroke)]">{e.north_wins} ({pct(e.north_wins, total)})</span>
      </div>
    </div>
  );
}

export function LeaderboardPage() {
  const [, navigate] = useHashRoute();
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    fetchStats("all", "match").then(setStats);
  }, []);

  const empty = stats !== null && stats.totals.games === 0;

  return (
    <div className="min-h-screen bg-white text-ink dark:bg-dark-bg dark:text-dark-ink">
      <PageHeader
        left={<button onClick={() => navigate("/match")} className="rounded-lg border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted transition-colors hover:border-ink hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink">← match</button>}
        right={<><button onClick={() => navigate("/games?scope=all&kind=match")} className="rounded-lg border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted hover:border-ink hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink">history</button><MuteToggle /></>}
      >
        Leaderboard
      </PageHeader>

      <main className="mx-auto max-w-5xl px-6 pb-12">
        {stats === null && (
          <div className="pt-24 text-center font-mono text-xs text-muted dark:text-dark-muted">loading…</div>
        )}

        {empty && (
          <div className="pt-24 text-center font-mono text-sm text-muted dark:text-dark-muted">
            No AI vs AI matches recorded yet.{" "}
            <button onClick={() => navigate("/match")} className="underline underline-offset-2 hover:text-ink dark:hover:text-dark-ink">
              Run one →
            </button>
          </div>
        )}

        {stats !== null && !empty && (
          <div className="flex flex-col gap-10">
            {/* Summary strip */}
            <div className="flex flex-wrap gap-6 border-b border-line pb-6 font-mono text-[11px] text-muted dark:border-dark-line dark:text-dark-muted">
              <span><span className="text-ink dark:text-dark-ink font-medium">{stats.totals.games}</span> matches</span>
              <span><span className="text-ink dark:text-dark-ink font-medium">{stats.totals.avg_plies}</span> avg plies</span>
              <span><span className="text-ink dark:text-dark-ink font-medium">{pct(stats.totals.draws, stats.totals.games)}</span> draw rate</span>
            </div>

            {/* Standings */}
            {stats.standings.length > 0 && (
              <section>
                <h2 className="mb-3 font-mono text-xs uppercase tracking-widest text-muted dark:text-dark-muted">
                  Standings
                </h2>
                <Standings rows={stats.standings} />
              </section>
            )}

            {/* Head-to-head */}
            {stats.leaderboard.length > 0 && (
              <section>
                <h2 className="mb-3 font-mono text-xs uppercase tracking-widest text-muted dark:text-dark-muted">
                  Head-to-head
                </h2>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {stats.leaderboard.map((e) => (
                    <MatchupCard key={`${e.south}-${e.north}`} e={e} />
                  ))}
                </div>
              </section>
            )}
          </div>
        )}

        <Footer className="mt-10" />
      </main>
    </div>
  );
}
