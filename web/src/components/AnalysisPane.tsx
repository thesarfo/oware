import type { MoveEntry } from "../lib/protocol";
import { humanPit } from "../lib/pit";

interface Props {
  history: MoveEntry[];
  humanSide: "south" | "north";
}

export function AnalysisPane({ history, humanSide }: Props) {
  if (!history.length) return null;

  const label = (by: string) => by === humanSide ? "you" : "agent";

  return (
    <div className="w-full max-w-[960px] rounded-xl border border-line dark:border-dark-line font-mono text-xs">
      <div className="px-4 py-2.5 text-xs uppercase tracking-wide text-muted dark:text-dark-muted">
        Move history · {history.length} plies
      </div>

      {/* Column headers */}
      <div className="grid grid-cols-[3rem_5rem_4rem_4rem_auto] border-t border-line px-4 py-2 text-xs uppercase tracking-wide text-muted dark:border-dark-line dark:text-dark-muted">
        <span className="text-center">#</span>
        <span className="text-center">by</span>
        <span className="text-center">pit</span>
        <span className="text-center">cap</span>
        <span className="text-center">az</span>
      </div>

      {/* Rows — scrollable */}
      <div className="max-h-96 overflow-y-auto border-t border-line dark:border-dark-line divide-y divide-line/40 dark:divide-dark-line/40">
        {history.map((m) => {
          const isPlayer = m.by === humanSide;
          const azDiffers = m.az_hint !== undefined && m.az_hint !== m.pit;
          return (
            <div
              key={m.ply}
              className={`grid grid-cols-[3rem_5rem_4rem_4rem_auto] px-4 py-2.5 text-center ${
                isPlayer ? "" : "bg-line/10 dark:bg-dark-line/10"
              }`}
            >
              <span className="text-muted dark:text-dark-muted">{m.ply + 1}</span>
              <span className={isPlayer ? "text-ink dark:text-dark-ink font-medium" : "text-muted dark:text-dark-muted"}>
                {label(m.by)}
              </span>
              <span>{humanPit(m.pit)}</span>
              <span className={m.captured > 0 ? "text-ink dark:text-dark-ink" : "text-muted dark:text-dark-muted"}>
                {m.captured > 0 ? `+${m.captured}` : "—"}
              </span>
              <span className={azDiffers ? "text-muted dark:text-dark-muted" : "invisible"}>
                {azDiffers ? `→ ${humanPit(m.az_hint)}` : "·"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
