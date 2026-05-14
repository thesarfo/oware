import { useEffect, useState } from "react";
import { apiUrl } from "../lib/api";
import type { AgentEntry } from "../lib/protocol";

interface Props {
  onStart: (agentId: string) => void;
}

const MINIMAX_DEPTHS = [
  { label: "d2", id: "minimax_d2" },
  { label: "d4", id: "minimax_d4" },
  { label: "d6", id: "minimax_d6" },
];

export function AgentPicker({ onStart }: Props) {
  const [agents, setAgents] = useState<AgentEntry[]>([]);
  const [selectedFamily, setSelectedFamily] = useState<string>("");
  const [minimaxDepth, setMinimaxDepth] = useState<string>("minimax_d4");

  useEffect(() => {
    fetch(apiUrl("/agents"), { credentials: "include" })
      .then((r) => r.json())
      .then((data: AgentEntry[]) => {
        setAgents(data);
        const first = data[0];
        if (first) setSelectedFamily(first.family);
      });
  }, []);

  const families = agents.reduce<string[]>((acc, a) => {
    if (!acc.includes(a.family)) acc.push(a.family);
    return acc;
  }, []);

  const familyAgent = (family: string) => agents.find((a) => a.family === family)!;

  const resolvedId =
    selectedFamily === "minimax" ? minimaxDepth : familyAgent(selectedFamily)?.id ?? "";

  const hasElo = agents.some((a) => a.est_elo !== null);
  const eloRange = hasElo
    ? { min: Math.min(...agents.filter(a => a.est_elo !== null).map(a => a.est_elo!)),
        max: Math.max(...agents.filter(a => a.est_elo !== null).map(a => a.est_elo!)) }
    : null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-baseline justify-between">
        <div className="font-mono text-xs uppercase tracking-wide text-muted dark:text-dark-muted">Opponent</div>
        {eloRange && (
          <div className="font-mono text-[10px] text-muted dark:text-dark-muted">
            {eloRange.min} – {eloRange.max} elo · weak → strong
          </div>
        )}
      </div>

      <div className="flex flex-col gap-2">
        {families.map((family) => {
          const rep = familyAgent(family);
          const selected = selectedFamily === family;
          return (
            <button
              key={family}
              onClick={() => setSelectedFamily(family)}
              className={`flex flex-col items-start rounded-xl border px-4 py-3 text-left transition-colors ${
                selected
                  ? "border-ink bg-ink text-white dark:border-dark-ink dark:bg-dark-ink dark:text-dark-bg"
                  : "border-line text-ink hover:border-ink dark:border-dark-line dark:text-dark-ink dark:hover:border-dark-muted"
              }`}
            >
              <div className="flex w-full items-baseline justify-between">
                <span className="text-sm font-semibold">
                  {family === "minimax" ? "Minimax" : rep.name}
                </span>
                {rep.est_elo !== null && (
                  <span className={`font-mono text-[11px] tabular-nums ${selected ? "text-white/70 dark:text-dark-bg/60" : "text-muted dark:text-dark-muted"}`}>
                    {rep.est_elo}
                  </span>
                )}
              </div>
              <span className={`text-[11px] ${selected ? "text-white/70 dark:text-dark-bg/60" : "text-muted dark:text-dark-muted"}`}>
                {rep.description}
              </span>
            </button>
          );
        })}
      </div>

      {selectedFamily === "minimax" && (
        <div className="flex gap-1 rounded-xl border border-line p-1 dark:border-dark-line">
          {MINIMAX_DEPTHS.map(({ label, id }) => {
            const agent = agents.find((a) => a.id === id);
            return (
              <button
                key={id}
                onClick={() => setMinimaxDepth(id)}
                className={`flex flex-1 flex-col items-center rounded-lg py-1.5 font-mono text-xs transition-colors ${
                  minimaxDepth === id
                    ? "bg-ink text-white dark:bg-dark-ink dark:text-dark-bg"
                    : "text-muted hover:text-ink dark:text-dark-muted dark:hover:text-dark-ink"
                }`}
              >
                <span>{label}</span>
                {agent?.est_elo !== null && agent?.est_elo !== undefined && (
                  <span className="text-[9px] opacity-70">{agent.est_elo}</span>
                )}
              </button>
            );
          })}
        </div>
      )}

      <button
        onClick={() => resolvedId && onStart(resolvedId)}
        disabled={!resolvedId}
        className="rounded-xl border border-ink bg-ink py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 active:scale-95 disabled:opacity-40 dark:border-dark-ink dark:bg-dark-ink dark:text-dark-bg"
      >
        Start game
      </button>
    </div>
  );
}
