import { useEffect } from "react";
import { Board } from "./components/Board";
import { Sidebar } from "./components/Sidebar";
import { MuteToggle } from "./components/MuteToggle";
import { useGame } from "./hooks/useGame";
import { primeAudio } from "./lib/audio";

export function App() {
  const game = useGame();

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
    <div className="relative min-h-screen w-full">
      <div className="absolute left-6 top-5 space-y-3 font-mono text-[11px] leading-tight text-ink">
        <div>
          <div className="text-muted"># Oware</div>
          <div>{game.conn === "open" ? "127.0.0.1 /play #" : "disconnected"}</div>
        </div>
        {game.state && (
          <>
            <div>
              <div className="text-muted">GameBoard</div>
              <div>{formatRow(game.state.pits.slice(6, 12).reverse())}</div>
              <div>{formatRow(game.state.pits.slice(0, 6))}</div>
            </div>
            <div>
              <div className="text-muted">Score</div>
              <div>{game.agent?.name ?? "AI Agent"} : {north}</div>
              <div>Player : {south}</div>
            </div>
            <div>
              <div className="text-muted">Status</div>
              <div>
                {game.result
                  ? resultLabel(game.result.winner)
                  : game.thinking
                    ? "agent thinking…"
                    : myTurn
                      ? "your move"
                      : "—"}
              </div>
            </div>
          </>
        )}
        {game.error && <div className="text-red-600">err: {game.error}</div>}
      </div>

      <div className="absolute right-6 top-5">
        <Sidebar onStart={onStart} />
      </div>

      <div className="flex h-screen items-center justify-center px-8">
        {game.state ? (
          <div className="w-full max-w-[920px]">
            <Board
              state={game.state}
              onPlay={(pit) => game.sendMove(pit)}
              disabled={!myTurn}
            />
            {game.result && (
              <div className="mt-6 flex items-center justify-center gap-4 font-mono text-sm">
                <span>{resultLabel(game.result.winner)}</span>
                <span className="text-muted">
                  final: you {game.result.final_stores.south} ·{" "}
                  {game.agent?.name ?? "agent"} {game.result.final_stores.north}
                </span>
              </div>
            )}
            {game.state && !game.result && (
              <div className="mt-6 flex justify-center">
                <button
                  onClick={game.resign}
                  className="border border-line px-3 py-1 font-mono text-xs uppercase tracking-wide text-muted hover:border-ink hover:text-ink"
                >
                  Resign
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="font-mono text-sm text-muted">Pick an opponent to begin.</div>
        )}
      </div>

      <div className="absolute bottom-3 right-4 flex items-center gap-3 font-mono text-[10px] uppercase tracking-wider text-muted">
        <MuteToggle />
        <span>Development Build</span>
      </div>
    </div>
  );
}

function formatRow(row: number[]): string {
  return "(" + row.map((n) => `'${n}'`).join(", ") + ")";
}

function resultLabel(winner: "south" | "north" | "draw"): string {
  if (winner === "draw") return "draw";
  return winner === "south" ? "you win" : "you lose";
}
