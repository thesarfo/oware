import { useEffect, useState } from "react";
import { Footer } from "../components/Footer";
import { MuteToggle } from "../components/MuteToggle";
import { PageHeader } from "../components/PageHeader";
import { ScopeToggle } from "../components/ScopeToggle";
import {
  fetchStats,
  type Kind,
  type LeaderboardEntry,
  type Scope,
  type StandingsEntry,
  type Stats,
  type StatsByAgent,
} from "../lib/games";
import { useHashRoute } from "../hooks/useHashRoute";

interface Props {
  scope: Scope;
  kind: Kind;
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

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-white/40 p-4 dark:border-dark-line dark:bg-white/0">
      <div className="font-mono text-[10px] uppercase tracking-wider text-muted dark:text-dark-muted">
        {label}
      </div>
      <div className="mt-1 font-mono text-3xl font-medium tabular-nums">{value}</div>
      {sub && <div className="mt-0.5 font-mono text-[10px] text-muted dark:text-dark-muted">{sub}</div>}
    </div>
  );
}

function WinBar({ wins, draws, losses }: { wins: number; draws: number; losses: number }) {
  const total = wins + draws + losses;
  if (total === 0) return <div className="h-2 w-full rounded-full bg-line/40" />;
  return (
    <div className="flex h-2 w-full overflow-hidden rounded-full bg-line/30 dark:bg-dark-line/30">
      <div className="bg-[var(--store-player-stroke)]" style={{ width: `${(wins / total) * 100}%` }} />
      <div className="bg-muted/50 dark:bg-dark-muted/40" style={{ width: `${(draws / total) * 100}%` }} />
      <div className="bg-[var(--store-agent-stroke)]" style={{ width: `${(losses / total) * 100}%` }} />
    </div>
  );
}

// ─── Human vs AI view ────────────────────────────────────────────────────────

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
      <WinBar wins={a.human_wins} draws={a.draws} losses={a.agent_wins} />
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

function HumanStatsView({ stats, scope, navigate }: { stats: Stats; scope: Scope; navigate: (p: string) => void }) {
  return (
    <div className="flex flex-col gap-8">
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="games" value={String(stats.totals.games)} />
        <StatCard label="human winrate" value={pct(stats.totals.human_wins, stats.totals.games)} />
        <StatCard label="avg plies" value={String(stats.totals.avg_plies)} />
        <StatCard
          label={scope === "all" ? "unique players" : "draw rate"}
          value={scope === "all" ? String(stats.totals.unique_clients) : pct(stats.totals.draws, stats.totals.games)}
        />
      </section>

      <section className="rounded-2xl border border-line bg-white/40 p-5 dark:border-dark-line dark:bg-white/0">
        <h2 className="mb-3 font-mono text-xs uppercase tracking-wide text-muted dark:text-dark-muted">Outcomes</h2>
        <WinBar wins={stats.totals.human_wins} draws={stats.totals.draws} losses={stats.totals.agent_wins} />
        <div className="mt-2 flex justify-between font-mono text-[11px] text-muted dark:text-dark-muted">
          <span>you won {stats.totals.human_wins} · {pct(stats.totals.human_wins, stats.totals.games)}</span>
          <span>draws {stats.totals.draws} · {pct(stats.totals.draws, stats.totals.games)}</span>
          <span>agent won {stats.totals.agent_wins} · {pct(stats.totals.agent_wins, stats.totals.games)}</span>
        </div>
        {stats.by_reason.length > 0 && (
          <div className="mt-4 border-t border-line pt-3 dark:border-dark-line">
            <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-muted dark:text-dark-muted">by end reason</div>
            <div className="flex flex-wrap gap-2 font-mono text-[11px]">
              {stats.by_reason.map((r) => (
                <span key={r.reason} className="rounded-full border border-line px-2.5 py-0.5 text-muted dark:border-dark-line dark:text-dark-muted">
                  {r.reason} <span className="text-ink dark:text-dark-ink">{r.games}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 font-mono text-xs uppercase tracking-wide text-muted dark:text-dark-muted">Per opponent</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {stats.by_agent.map((a) => <AgentCard key={a.agent_id} a={a} />)}
        </div>
      </section>

      <RecentSection stats={stats} scope={scope} navigate={navigate} />
    </div>
  );
}

// ─── AI vs AI view ────────────────────────────────────────────────────────────

function StandingsTable({ rows }: { rows: StandingsEntry[] }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-line dark:border-dark-line">
      <table className="w-full font-mono text-[11px]">
        <thead>
          <tr className="border-b border-line text-left text-[10px] uppercase tracking-wider text-muted dark:border-dark-line dark:text-dark-muted">
            <th className="px-4 py-2.5 w-8">#</th>
            <th className="px-4 py-2.5">agent</th>
            <th className="px-4 py-2.5 text-right">gp</th>
            <th className="px-4 py-2.5 text-right">w</th>
            <th className="px-4 py-2.5 text-right">d</th>
            <th className="px-4 py-2.5 text-right">l</th>
            <th className="px-4 py-2.5 text-right">win%</th>
            <th className="px-4 py-2.5 min-w-[120px]">record</th>
            <th className="px-4 py-2.5 text-right">avg plies</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={r.agent}
              className={`border-b border-line/50 last:border-0 dark:border-dark-line/50 ${
                i === 0 ? "bg-[var(--store-player-stroke)]/5" : ""
              }`}
            >
              <td className="px-4 py-2.5 tabular-nums text-muted dark:text-dark-muted">{i + 1}</td>
              <td className="px-4 py-2.5 font-medium text-ink dark:text-dark-ink">{r.agent}</td>
              <td className="px-4 py-2.5 text-right tabular-nums text-muted dark:text-dark-muted">{r.games}</td>
              <td className="px-4 py-2.5 text-right tabular-nums text-[var(--store-player-stroke)]">{r.wins}</td>
              <td className="px-4 py-2.5 text-right tabular-nums text-muted dark:text-dark-muted">{r.draws}</td>
              <td className="px-4 py-2.5 text-right tabular-nums text-[var(--store-agent-stroke)]">{r.losses}</td>
              <td className="px-4 py-2.5 text-right tabular-nums font-medium">{r.win_pct}%</td>
              <td className="px-4 py-2.5">
                <WinBar wins={r.wins} draws={r.draws} losses={r.losses} />
              </td>
              <td className="px-4 py-2.5 text-right tabular-nums text-muted dark:text-dark-muted">{r.avg_plies}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MatchupRow({ e }: { e: LeaderboardEntry }) {
  const total = e.south_wins + e.north_wins + e.draws;
  return (
    <div className="rounded-xl border border-line bg-white/40 p-4 dark:border-dark-line dark:bg-white/0">
      <div className="flex items-center justify-between font-mono text-[11px]">
        <div className="flex items-center gap-2">
          <span className="font-medium text-[var(--store-player-stroke)]">{e.south}</span>
          <span className="text-muted dark:text-dark-muted">vs</span>
          <span className="font-medium text-[var(--store-agent-stroke)]">{e.north}</span>
        </div>
        <span className="text-muted dark:text-dark-muted">{e.games} games · {e.avg_plies}p avg</span>
      </div>
      <div className="mt-2">
        <WinBar wins={e.south_wins} draws={e.draws} losses={e.north_wins} />
      </div>
      <div className="mt-1.5 flex justify-between font-mono text-[10px] text-muted dark:text-dark-muted">
        <span className="text-[var(--store-player-stroke)]">{e.south} {e.south_wins} ({pct(e.south_wins, total)})</span>
        <span>draw {e.draws}</span>
        <span className="text-[var(--store-agent-stroke)]">{e.north} {e.north_wins} ({pct(e.north_wins, total)})</span>
      </div>
    </div>
  );
}

function MatchStatsView({ stats, scope, navigate }: { stats: Stats; scope: Scope; navigate: (p: string) => void }) {
  const southWins = stats.leaderboard.reduce((s, e) => s + e.south_wins, 0);
  const northWins = stats.leaderboard.reduce((s, e) => s + e.north_wins, 0);
  const draws = stats.totals.draws;
  const games = stats.totals.games;

  return (
    <div className="flex flex-col gap-8">
      {/* Headline */}
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="matches" value={String(games)} />
        <StatCard label="south win rate" value={pct(southWins, games)} sub={`${southWins} wins`} />
        <StatCard label="north win rate" value={pct(northWins, games)} sub={`${northWins} wins`} />
        <StatCard label="draw rate" value={pct(draws, games)} sub={`avg ${stats.totals.avg_plies}p`} />
      </section>

      {/* End reasons */}
      {stats.by_reason.length > 0 && (
        <section className="rounded-2xl border border-line bg-white/40 p-5 dark:border-dark-line dark:bg-white/0">
          <h2 className="mb-3 font-mono text-xs uppercase tracking-wide text-muted dark:text-dark-muted">How games end</h2>
          <div className="flex flex-wrap gap-2 font-mono text-[11px]">
            {stats.by_reason.map((r) => (
              <span key={r.reason} className="rounded-full border border-line px-2.5 py-0.5 text-muted dark:border-dark-line dark:text-dark-muted">
                {r.reason} <span className="text-ink dark:text-dark-ink">{r.games}</span>
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Standings */}
      {stats.standings.length > 0 && (        <section>
          <h2 className="mb-3 font-mono text-xs uppercase tracking-wide text-muted dark:text-dark-muted">Standings</h2>
          <StandingsTable rows={stats.standings} />
        </section>
      )}

      {/* Head-to-head matchups */}
      {stats.leaderboard.length > 0 && (
        <section>
          <h2 className="mb-3 font-mono text-xs uppercase tracking-wide text-muted dark:text-dark-muted">Head-to-head</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {stats.leaderboard.map((e) => (
              <MatchupRow key={`${e.south}-${e.north}`} e={e} />
            ))}
          </div>
        </section>
      )}

      <RecentSection stats={stats} scope={scope} navigate={navigate} />
    </div>
  );
}

// ─── Shared recent section ────────────────────────────────────────────────────

function RecentSection({ stats, scope, navigate }: { stats: Stats; scope: Scope; navigate: (p: string) => void }) {
  return (
    <section className="rounded-2xl border border-line bg-white/40 p-6 dark:border-dark-line dark:bg-white/0">
      <h2 className="mb-4 font-mono text-xs uppercase tracking-wide text-muted dark:text-dark-muted">Recent</h2>
      <div className="flex flex-col gap-1">
        {stats.recent.map((r) => {
          const isMatch = !!r.opponent_agent_id;
          const label = isMatch ? `${r.agent_id} vs ${r.opponent_agent_id}` : `vs ${r.agent_id}`;
          const outcomeText = isMatch
            ? r.winner === "south" ? `${r.agent_id} won`
              : r.winner === "north" ? `${r.opponent_agent_id} won`
              : r.winner === "draw" ? "draw" : r.reason
            : r.winner === "south" ? "you won"
              : r.winner === "north" ? "you lost"
              : r.winner === "draw" ? "draw" : r.reason;
          const tone =
            r.winner === "south" ? "text-[var(--store-player-stroke)]"
            : r.winner === "north" ? "text-[var(--store-agent-stroke)]"
            : "text-muted dark:text-dark-muted";
          return (
            <button
              key={r.game_id}
              onClick={() => navigate(`/games/${r.game_id}?scope=${scope}`)}
              className="grid grid-cols-[12rem_minmax(0,1fr)_auto] items-baseline gap-x-6 rounded-lg px-3 py-2.5 text-left font-mono text-[11px] transition-colors hover:bg-ink/5 dark:hover:bg-dark-ink/10"
            >
              <span className="truncate text-ink dark:text-dark-ink">{label}</span>
              <span className={`truncate ${tone}`}>{outcomeText}</span>
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
  );
}

// ─── Page shell ───────────────────────────────────────────────────────────────

export function StatsPage({ scope, kind }: Props) {
  const [, navigate] = useHashRoute();
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    setStats(null);
    fetchStats(scope, kind).then(setStats);
  }, [scope, kind]);

  const isMatch = kind === "match";

  return (
    <div className="min-h-screen bg-white text-ink dark:bg-dark-bg dark:text-dark-ink">
      <PageHeader
        left={<button onClick={() => navigate(`/games?scope=${scope}&kind=${kind}`)} className="rounded-lg border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted transition-colors hover:border-ink hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink">← games</button>}
        right={<><button onClick={() => navigate("/")} className="rounded-lg border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted hover:border-ink hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink">play</button><MuteToggle /></>}
      >
        {isMatch ? "AI vs AI · Stats" : "Analytics"}
      </PageHeader>

      <main className="mx-auto max-w-6xl px-6 pb-12">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          {/* Scope toggle only shown for human stats */}
          {!isMatch && (
            <ScopeToggle scope={scope} onChange={(s) => navigate(`/stats?scope=${s}&kind=${kind}`)} />
          )}
          <div className={`flex items-center gap-1 font-mono text-[10px] ${isMatch ? "" : "ml-auto"}`}>
            {(["human", "match"] as Kind[]).map((k) => (
              <button
                key={k}
                onClick={() => navigate(`/stats?scope=${scope}&kind=${k}`)}
                className={`rounded-full border px-2.5 py-0.5 transition-colors ${
                  kind === k
                    ? "border-ink bg-ink text-white dark:border-dark-ink dark:bg-dark-ink dark:text-dark-bg"
                    : "border-line text-muted hover:border-muted hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink"
                }`}
              >
                {k === "human" ? "vs human" : "ai vs ai"}
              </button>
            ))}
          </div>
        </div>

        {stats === null && (
          <div className="pt-20 text-center font-mono text-xs text-muted dark:text-dark-muted">loading…</div>
        )}

        {stats !== null && stats.totals.games === 0 && (
          <div className="pt-20 text-center font-mono text-sm text-muted dark:text-dark-muted">
            {isMatch
              ? "No AI vs AI matches recorded yet. Run one from the match page."
              : scope === "mine"
                ? "No completed games yet. Play one and come back."
                : "No completed games recorded."}
          </div>
        )}

        {stats !== null && stats.totals.games > 0 && (
          isMatch
            ? <MatchStatsView stats={stats} scope={scope} navigate={navigate} />
            : <HumanStatsView stats={stats} scope={scope} navigate={navigate} />
        )}

        <Footer className="mt-10" />
      </main>
    </div>
  );
}
