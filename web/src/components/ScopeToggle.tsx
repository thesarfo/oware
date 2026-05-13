import type { Scope } from "../lib/games";

interface Props {
  scope: Scope;
  onChange: (s: Scope) => void;
}

export function ScopeToggle({ scope, onChange }: Props) {
  return (
    <div className="inline-flex rounded-xl border border-line p-1 font-mono text-[11px] uppercase tracking-wider dark:border-dark-line">
      {(["mine", "all"] as const).map((s) => (
        <button
          key={s}
          onClick={() => onChange(s)}
          className={`rounded-lg px-3 py-1 transition-colors ${
            scope === s
              ? "bg-ink text-white dark:bg-dark-ink dark:text-dark-bg"
              : "text-muted hover:text-ink dark:text-dark-muted dark:hover:text-dark-ink"
          }`}
        >
          {s}
        </button>
      ))}
    </div>
  );
}
