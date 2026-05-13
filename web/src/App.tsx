import { useEffect } from "react";
import { Board } from "./components/Board";
import { Sidebar } from "./components/Sidebar";
import { MuteToggle } from "./components/MuteToggle";
import { AgentInsight } from "./components/AgentInsight";
import { AnalysisPane } from "./components/AnalysisPane";
import { useGame } from "./hooks/useGame";
import { useTheme } from "./hooks/useTheme";
import { primeAudio } from "./lib/audio";

export function App() {
  const game = useGame();
  const { dark, toggle: toggleTheme } = useTheme();

  useEffect(() => {
    const handler = () => primeAudio();
    window.addEventListener("pointerdown", handler, { once: true });
    return () => window.removeEventListener("pointerdown", handler);
  }, []);

  const onStart = (agentId: string) => game.newGame(agentId, "south");

  const myTurn =
    game.state !== null &&
    game.state.to_move === "south" &&
    game.result === null &&
    !game.thinking;

  const south = game.state?.stores.south ?? 0;
  const north = game.state?.stores.north ?? 0;

  return (
    <div className="flex min-h-screen flex-col bg-white text-ink dark:bg-dark-bg dark:text-dark-ink">

      {/* ── Header ── */}
      <header className="py-4 text-center">
        <h1 className="font-mono text-2xl font-semibold tracking-widest uppercase">Oware</h1>
      </header>

      <div className="flex flex-1 flex-col lg:grid lg:grid-cols-[20rem_1fr_20rem]">

      {/* ── Left HUD ── */}
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

      {/* ── Board ── */}
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
          <p className="font-mono text-sm text-muted dark:text-dark-muted">Pick an opponent to begin.</p>
        )}

        {game.result && (game.result.history?.length ?? 0) > 0 && (
          <AnalysisPane history={game.result.history} humanSide="south" />
        )}
        {game.analysing && (
          <div className="font-mono text-[11px] text-muted dark:text-dark-muted animate-pulse">
            analysing with alphazero…
          </div>
        )}

        <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-wider text-muted dark:text-dark-muted">
          <MuteToggle />
          <button
            onClick={toggleTheme}
            className="rounded-lg border border-line px-3 py-1.5 transition-colors hover:border-ink hover:text-ink dark:border-dark-line dark:hover:border-dark-muted dark:hover:text-dark-ink"
            aria-label="Toggle theme"
          >
            {dark ? "light" : "dark"}
          </button>
          <span>Development Build</span>
        </div>
      </main>

      {/* ── Sidebar ── */}
      <aside className="shrink-0 p-4 lg:p-6">
        <Sidebar onStart={onStart} />
      </aside>

    </div>
    </div>
  );
}

function resultLabel(winner: "south" | "north" | "draw"): string {
  if (winner === "draw") return "draw";
  return winner === "south" ? "you win" : "you lose";
}
