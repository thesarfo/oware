import type { AgentMoveMsg } from "../lib/protocol";

interface Props {
  move: AgentMoveMsg;
}

export function AgentInsight({ move }: Props) {
  const scores = move.extras?.scores as (number | null)[] | undefined;

  return (
    <div className="rounded-xl border border-line p-3 font-mono text-[11px] text-muted space-y-6 dark:border-dark-line dark:text-dark-muted">
      <div className="uppercase tracking-wide">Last move · pit {move.pit + 1}</div>
      {scores && (
        <div className="flex gap-1 items-end h-8">
          {scores.map((s, i) => {
            const active = s !== null && isFinite(s);
            const chosen = i === move.pit;
            const finite = scores.filter((v): v is number => v !== null && isFinite(v));
            const min = finite.length ? Math.min(...finite) : 0;
            const max = finite.length ? Math.max(...finite) : 1;
            const range = max - min || 1;
            const height = active ? Math.max(4, ((s! - min) / range) * 28) : 4;
            return (
              <div key={i} className="flex flex-col items-center gap-0.5 w-5">
                <div
                  style={{ height }}
                  className={`w-full rounded-sm transition-all ${chosen
                    ? "bg-ink dark:bg-dark-ink"
                    : active
                      ? "bg-muted/40 dark:bg-dark-muted/40"
                      : "bg-line/40 dark:bg-dark-line/40"
                    }`}
                />
                <span className={chosen ? "text-ink font-semibold dark:text-dark-ink" : ""}>{i + 1}</span>
              </div>
            );
          })}
        </div>
      )}
      {move.extras?.depth_reached !== undefined && (
        <div className="text-muted/70 dark:text-dark-muted">
          depth {move.extras.depth_reached as number} · {(move.extras.nodes as number).toLocaleString()} nodes
        </div>
      )}
    </div>
  );
}
