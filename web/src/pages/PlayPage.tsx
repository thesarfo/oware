import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Board } from "../components/Board";
import { Footer } from "../components/Footer";
import { Sidebar } from "../components/Sidebar";
import { MuteToggle } from "../components/MuteToggle";
import { AgentInsight } from "../components/AgentInsight";
import { AnalysisPane } from "../components/AnalysisPane";
import { PageHeader } from "../components/PageHeader";
import { useGame } from "../hooks/useGame";
import { useTheme } from "../hooks/useTheme";
import { useHashRoute } from "../hooks/useHashRoute";
import { primeAudio } from "../lib/audio";

export function PlayPage() {
  const game = useGame();
  const { dark, toggle: toggleTheme } = useTheme();
  const [, navigate] = useHashRoute();

  useEffect(() => {
    const handler = () => primeAudio();
    window.addEventListener("pointerdown", handler, { once: true });
    return () => window.removeEventListener("pointerdown", handler);
  }, []);

  const onStart = (agentId: string) => game.newGame(agentId, "south");
  const [pickerOpen, setPickerOpen] = useState(false);

  const myTurn =
    game.state !== null &&
    game.state.to_move === "south" &&
    game.result === null &&
    !game.thinking;

  const south = game.state?.stores.south ?? 0;
  const north = game.state?.stores.north ?? 0;

  return (
    <div className="flex min-h-screen flex-col bg-white text-ink dark:bg-dark-bg dark:text-dark-ink">
      <PageHeader
        left={<span className="font-mono text-[10px] uppercase tracking-widest text-muted">play</span>}
        right={
          <>
            <button onClick={() => navigate("/match")} className="border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted transition-colors hover:border-ink hover:text-ink dark:border-dark-line dark:hover:border-dark-muted dark:hover:text-dark-ink">ai vs ai</button>
            <button onClick={() => navigate("/stats?scope=all")} className="border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted transition-colors hover:border-ink hover:text-ink dark:border-dark-line dark:hover:border-dark-muted dark:hover:text-dark-ink">stats</button>
            <button onClick={() => navigate("/games")} className="border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted transition-colors hover:border-ink hover:text-ink dark:border-dark-line dark:hover:border-dark-muted dark:hover:text-dark-ink">history →</button>
          </>
        }
      >
        <span className="flex items-center gap-3 text-4xl">
          <img src="/logo.png" alt="Oware" className="h-14 w-14 rounded-2xl object-cover shadow-md" />
          Oware
        </span>
      </PageHeader>

      <div className="flex flex-1 flex-col lg:grid lg:grid-cols-[20rem_1fr_20rem]">
        <aside className="flex shrink-0 flex-col gap-3 p-4 font-mono text-[11px] leading-tight lg:p-6">
          <div className="rounded-xl border border-line p-3 dark:border-dark-line">
            <div className="text-muted dark:text-dark-muted"># Oware</div>
            <div>{game.conn === "open" ? "connected" : "disconnected"}</div>
          </div>

          {game.lastAgentMove && <AgentInsight move={game.lastAgentMove} />}

          {game.state && (
            <>
              <div className="rounded-xl border border-line p-3 space-y-1 dark:border-dark-line">
                <div className="text-muted dark:text-dark-muted">Score</div>
                <div>{game.agent?.name ?? "Agent"} : {north}</div>
                <div>Player : {south}</div>
              </div>
              <div className="rounded-xl border border-line p-3 dark:border-dark-line">
                <div className="text-muted dark:text-dark-muted">Status</div>
                <div>
                  {game.result
                    ? resultLabel(game.result.winner)
                    : game.thinking
                      ? "thinking…"
                      : myTurn
                        ? "your move"
                        : "—"}
                </div>
              </div>
            </>
          )}

          {game.error && <div className="text-red-500">err: {game.error}</div>}
        </aside>

        <main className="flex flex-1 flex-col items-center justify-center gap-4 p-0 lg:p-8">
          {game.state ? (
            <>
              <div className="w-full max-w-[960px]">
                <Board
                  state={game.state}
                  onPlay={(pit) => game.sendMove(pit)}
                  disabled={!myTurn}
                />
              </div>

              {game.result && (
                <div className="flex items-center gap-4 font-mono text-sm">
                  <span>{resultLabel(game.result.winner)}</span>
                  <span className="text-muted dark:text-dark-muted">
                    you {game.result.final_stores.south} · {game.agent?.name ?? "agent"} {game.result.final_stores.north}
                  </span>
                  <button
                    onClick={() => navigate(`/games/${game.state!.game_id}?scope=mine`)}
                    className="border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted hover:border-ink hover:text-ink dark:border-dark-line"
                  >
                    replay →
                  </button>
                </div>
              )}

              {!game.result && (
                <button
                  onClick={game.resign}
                  className="rounded-xl border border-line px-4 py-2 font-mono text-xs uppercase tracking-wide text-muted transition-colors hover:border-ink hover:text-ink active:scale-95 dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink"
                >
                  Resign
                </button>
              )}
            </>
          ) : (
            <div className="flex w-full max-w-lg flex-col gap-5 px-4 py-6 font-mono">
              <p className="text-center text-sm text-muted dark:text-dark-muted">
                Pick an opponent below to begin.
              </p>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <TipCard title="How to play">
                  You are <span className="text-[var(--store-player-stroke)]">south</span>. Click any of your six pits to sow seeds counter-clockwise. Capture by landing on a pit that brings the opponent's count to 2 or 3.
                </TipCard>
                <TipCard title="Opponents">
                  <span className="font-medium">Random</span> — plays randomly.<br />
                  <span className="font-medium">Minimax</span> — d2 easy · d4 medium · d6 hard.<br />
                  <span className="font-medium">DQN / PPO / AZ</span> — trained agents, strongest last.
                </TipCard>
                <TipCard title="AI vs AI">
                  Watch any two agents play each other. Hit <button onClick={() => navigate("/match")} className="underline underline-offset-2 hover:text-ink dark:hover:text-dark-ink">ai vs ai</button> in the header, pick both sides and a speed, then start.
                </TipCard>
                <TipCard title="Stats & history">
                  Every game is recorded. <button onClick={() => navigate("/games")} className="underline underline-offset-2 hover:text-ink dark:hover:text-dark-ink">History</button> shows all your replays. <button onClick={() => navigate("/stats?scope=all")} className="underline underline-offset-2 hover:text-ink dark:hover:text-dark-ink">Stats</button> breaks down your winrate per opponent. <button onClick={() => navigate("/leaderboard")} className="underline underline-offset-2 hover:text-ink dark:hover:text-dark-ink">Leaderboard</button> ranks agents head-to-head.
                </TipCard>
              </div>
            </div>
          )}

          {game.result && (game.result.history?.length ?? 0) > 0 && (
            <AnalysisPane history={game.result.history} humanSide="south" />
          )}
          {game.analysing && (
            <div className="font-mono text-[11px] text-muted dark:text-dark-muted animate-pulse">
              analysing with alphazero…
            </div>
          )}

          <div className="flex flex-col items-center gap-3 font-mono text-[10px] uppercase tracking-wider text-muted dark:text-dark-muted">
            <div className="flex items-center gap-3">
              <MuteToggle />
              <button
                onClick={toggleTheme}
                className="rounded-lg border border-line px-3 py-1.5 transition-colors hover:border-ink hover:text-ink dark:border-dark-line dark:hover:border-dark-muted dark:hover:text-dark-ink"
                aria-label="Toggle theme"
              >
                {dark ? "light" : "dark"}
              </button>
            </div>
            <Footer />
          </div>
        </main>

        <aside className="shrink-0 p-4 lg:p-6">
          {/* Mobile toggle */}
          <button
            onClick={() => setPickerOpen((o) => !o)}
            className="mb-3 flex w-full items-center justify-between rounded-xl border border-line px-4 py-2.5 font-mono text-[11px] uppercase tracking-wider text-muted transition-colors hover:border-ink hover:text-ink lg:hidden dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink"
          >
            <span>choose opponent</span>
            <span>{pickerOpen ? "▲" : "▼"}</span>
          </button>
          <div className={`${pickerOpen ? "block" : "hidden"} lg:block`}>
            <Sidebar onStart={(id) => { onStart(id); setPickerOpen(false); }} />
          </div>
        </aside>
      </div>
    </div>
  );
}

function resultLabel(winner: "south" | "north" | "draw"): string {
  if (winner === "draw") return "draw";
  return winner === "south" ? "you win" : "you lose";
}

function TipCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-white/40 p-4 dark:border-dark-line dark:bg-white/0">
      <div className="mb-1.5">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-ink dark:text-dark-ink">{title}</span>
      </div>
      <p className="text-[11px] leading-relaxed text-muted dark:text-dark-muted">{children}</p>
    </div>
  );
}
