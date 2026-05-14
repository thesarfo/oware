import { useEffect, useState } from "react";
import { Board } from "../components/Board";
import { Footer } from "../components/Footer";
import { MuteToggle } from "../components/MuteToggle";
import { PageHeader } from "../components/PageHeader";
import { useGame } from "../hooks/useGame";
import { useHashRoute } from "../hooks/useHashRoute";
import { useTheme } from "../hooks/useTheme";
import { apiUrl } from "../lib/api";
import { primeAudio } from "../lib/audio";
import type { AgentEntry } from "../lib/protocol";

const SPEEDS = [
  { label: "1×", ms: 1200 },
  { label: "1.5×", ms: 800 },
  { label: "2×", ms: 500 },
  { label: "4×", ms: 250 },
  { label: "max", ms: 0 },
];

export function MatchPage() {
  const game = useGame();
  const { dark, toggle: toggleTheme } = useTheme();
  const [, navigate] = useHashRoute();

  const [agents, setAgents] = useState<AgentEntry[]>([]);
  const [south, setSouth] = useState<string>("");
  const [north, setNorth] = useState<string>("");
  const [speedMs, setSpeedMs] = useState(800);

  useEffect(() => {
    fetch(apiUrl("/agents"), { credentials: "include" })
      .then((r) => r.json())
      .then((data: AgentEntry[]) => {
        setAgents(data);
        if (data.length) {
          setSouth(data[0].id);
          setNorth(data[Math.min(1, data.length - 1)].id);
        }
      });
  }, []);

  useEffect(() => {
    const handler = () => primeAudio();
    window.addEventListener("pointerdown", handler, { once: true });
    return () => window.removeEventListener("pointerdown", handler);
  }, []);

  const start = () => {
    if (!south || !north) return;
    game.newMatch(south, north, speedMs);
  };

  const playing = game.state !== null && game.result === null;

  return (
    <div className="flex min-h-screen flex-col bg-white text-ink dark:bg-dark-bg dark:text-dark-ink">
      <PageHeader
        left={<button onClick={() => navigate("/")} className="rounded-lg border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted transition-colors hover:border-ink hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink">← play</button>}
        right={<>
          <button onClick={() => navigate("/leaderboard")} className="rounded-lg border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted hover:border-ink hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink">leaderboard</button>
          <button onClick={() => navigate("/games?scope=all&kind=match")} className="rounded-lg border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted hover:border-ink hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink">history</button>
          <MuteToggle />
        </>}
      >
        AI vs AI
      </PageHeader>

      <div className="grid flex-1 grid-cols-1 gap-6 px-6 pb-8 lg:grid-cols-[20rem_1fr_20rem]">
        {/* Setup panel — agent pickers + speed */}
        <aside className="flex flex-col gap-4">
          <AgentSlot
            label="north"
            tone="agent"
            agents={agents}
            value={north}
            onChange={setNorth}
            disabled={playing}
          />
          <AgentSlot
            label="south"
            tone="player"
            agents={agents}
            value={south}
            onChange={setSouth}
            disabled={playing}
          />

          <div className="rounded-2xl border border-line p-3 dark:border-dark-line">
            <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-muted dark:text-dark-muted">
              speed
            </div>
            <div className="flex flex-wrap gap-1.5">
              {SPEEDS.map((s) => (
                <button
                  key={s.label}
                  onClick={() => setSpeedMs(s.ms)}
                  className={`rounded-md border px-2.5 py-1 font-mono text-[11px] transition-colors ${speedMs === s.ms
                      ? "border-ink bg-ink text-white dark:border-dark-ink dark:bg-dark-ink dark:text-dark-bg"
                      : "border-line text-muted hover:border-muted hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink"
                    }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={start}
            disabled={!south || !north}
            className="rounded-xl border border-ink bg-ink py-2.5 font-mono text-sm uppercase tracking-wider text-white transition-opacity hover:opacity-90 disabled:opacity-40 dark:border-dark-ink dark:bg-dark-ink dark:text-dark-bg"
          >
            {playing ? "restart match" : game.result ? "play again" : "start match"}
          </button>
        </aside>

        {/* Board */}
        <main className="flex flex-col items-center gap-4">
          {game.state ? (
            <>
              <MatchHeader
                south={game.agent?.name ?? south}
                north={game.northAgent?.name ?? north}
                state={game.state}
                thinking={game.thinking}
              />
              <div className="w-full max-w-[960px]">
                <Board
                  state={game.state}
                  onPlay={() => undefined}
                  disabled={true}
                />
              </div>
              {game.result && (
                <div className="flex flex-wrap items-center justify-center gap-3 font-mono text-sm">
                  <span>
                    {game.result.winner === "draw"
                      ? "draw"
                      : game.result.winner === "south"
                        ? `${game.agent?.name ?? "south"} won`
                        : `${game.northAgent?.name ?? "north"} won`}
                  </span>
                  <span className="text-muted dark:text-dark-muted">
                    {game.result.final_stores.south}–{game.result.final_stores.north} ·{" "}
                    {game.result.reason}
                  </span>
                  <button
                    onClick={() => navigate(`/games/${game.state!.game_id}?scope=mine`)}
                    className="rounded-lg border border-line px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted hover:border-ink hover:text-ink dark:border-dark-line"
                  >
                    replay →
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-3 pt-16 font-mono text-sm text-muted dark:text-dark-muted">
              <p>Pick two agents and start a match.</p>
              <p className="text-[11px]">
                Same telemetry as live play — every match shows up under your{" "}
                <button
                  onClick={() => navigate("/games?scope=mine")}
                  className="underline underline-offset-2 hover:text-ink dark:hover:text-dark-ink"
                >
                  game history
                </button>
                .
              </p>
            </div>
          )}
        </main>

        {/* Right — live state */}
        <aside className="flex flex-col gap-3 font-mono text-[11px]">
          <div className="rounded-xl border border-line p-3 dark:border-dark-line">
            <div className="text-muted dark:text-dark-muted">connection</div>
            <div>{game.conn === "open" ? "connected" : "disconnected"}</div>
          </div>
          {game.state && (
            <div className="rounded-xl border border-line p-3 space-y-1 dark:border-dark-line">
              <div className="text-muted dark:text-dark-muted">score</div>
              <div>
                <span className="text-[var(--store-player-stroke)]">{game.agent?.name ?? south}</span>{" "}
                {game.state.stores.south}
              </div>
              <div>
                <span className="text-[var(--store-agent-stroke)]">{game.northAgent?.name ?? north}</span>{" "}
                {game.state.stores.north}
              </div>
              <div className="pt-1 text-muted dark:text-dark-muted">
                ply {game.state.ply}
              </div>
            </div>
          )}
          {game.lastAgentMove && playing && (
            <div className="rounded-xl border border-line p-3 dark:border-dark-line">
              <div className="text-muted dark:text-dark-muted">last move</div>
              <div>
                pit {game.lastAgentMove.pit + 1}
                <span className="ml-2 text-muted dark:text-dark-muted">
                  {game.lastAgentMove.thought_ms} ms
                </span>
              </div>
            </div>
          )}
        </aside>
      </div>

      <div className="flex items-center justify-center gap-3 px-6 pb-4 font-mono text-[10px] uppercase tracking-wider text-muted dark:text-dark-muted">
        <button
          onClick={toggleTheme}
          className="rounded-lg border border-line px-3 py-1.5 transition-colors hover:border-ink hover:text-ink dark:border-dark-line dark:hover:border-dark-muted dark:hover:text-dark-ink"
        >
          {dark ? "light" : "dark"}
        </button>
      </div>
      <Footer className="pb-6" />
    </div>
  );
}

function AgentSlot({
  label,
  tone,
  agents,
  value,
  onChange,
  disabled,
}: {
  label: string;
  tone: "player" | "agent";
  agents: AgentEntry[];
  value: string;
  onChange: (id: string) => void;
  disabled: boolean;
}) {
  const accent =
    tone === "player"
      ? "text-[var(--store-player-stroke)]"
      : "text-[var(--store-agent-stroke)]";
  const hasElo = agents.some((a) => a.est_elo !== null);
  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-line p-3 dark:border-dark-line">
      <div className="flex items-baseline justify-between">
        <span className={`font-mono text-[10px] uppercase tracking-wider ${accent}`}>
          {label}
        </span>
        {hasElo && (
          <span className="font-mono text-[10px] text-muted dark:text-dark-muted">
            elo · weak → strong
          </span>
        )}
      </div>
      <div className="flex flex-col gap-1">
        {agents.map((a) => (
          <button
            key={a.id}
            onClick={() => onChange(a.id)}
            disabled={disabled}
            className={`flex items-baseline justify-between rounded-lg border px-3 py-1.5 text-left transition-colors disabled:opacity-50 ${value === a.id
                ? "border-ink bg-canvas dark:border-dark-ink dark:bg-dark-bg"
                : "border-line hover:border-muted dark:border-dark-line dark:hover:border-dark-muted"
              }`}
          >
            <div className="flex flex-col">
              <span className="text-[12px] font-medium">{a.name}</span>
              <span className="text-[10px] text-muted dark:text-dark-muted">{a.id}</span>
            </div>
            {a.est_elo !== null && (
              <span className="font-mono text-[11px] tabular-nums text-muted dark:text-dark-muted">
                {a.est_elo}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

function MatchHeader({
  south,
  north,
  state,
  thinking,
}: {
  south: string;
  north: string;
  state: { to_move: "south" | "north" };
  thinking: boolean;
}) {
  const moverName = state.to_move === "south" ? south : north;
  return (
    <div className="flex w-full max-w-[960px] items-center justify-between font-mono text-[12px]">
      <div className="flex items-center gap-2">
        <span
          className={`inline-block h-1.5 w-1.5 rounded-full ${state.to_move === "south"
              ? "bg-[var(--store-player-stroke)] animate-pulse"
              : "bg-line dark:bg-dark-line"
            }`}
        />
        <span>{south}</span>
      </div>
      <span className="text-muted dark:text-dark-muted">
        {thinking ? `${moverName} thinking…` : `${moverName} to move`}
      </span>
      <div className="flex items-center gap-2">
        <span>{north}</span>
        <span
          className={`inline-block h-1.5 w-1.5 rounded-full ${state.to_move === "north"
              ? "bg-[var(--store-agent-stroke)] animate-pulse"
              : "bg-line dark:bg-dark-line"
            }`}
        />
      </div>
    </div>
  );
}
