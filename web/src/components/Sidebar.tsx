import { useState } from "react";
import { AgentPicker } from "./AgentPicker";
import { RulesTab } from "./RulesTab";

interface Props {
  onStart: (agentId: string) => void;
}

type Tab = "play" | "rules";

const TABS: { id: Tab; label: string }[] = [
  { id: "play", label: "Play" },
  { id: "rules", label: "Rules" },
];

export function Sidebar({ onStart }: Props) {
  const [tab, setTab] = useState<Tab>("play");
  const [open, setOpen] = useState(true);

  return (
    <div className="flex w-full flex-col rounded-2xl border border-line dark:border-dark-line lg:w-80">
      <div className="flex items-center gap-1 p-2">
        <div className="flex flex-1 gap-1 rounded-xl border border-line p-1 dark:border-dark-line">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => { setTab(t.id); setOpen(true); }}
              className={`flex-1 rounded-lg py-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors ${
                tab === t.id && open
                  ? "bg-ink text-white dark:bg-dark-ink dark:text-dark-bg"
                  : "text-muted hover:text-ink dark:text-dark-muted dark:hover:text-dark-ink"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <button
          onClick={() => setOpen((o) => !o)}
          className="rounded-lg border border-line px-2.5 py-1.5 font-mono text-[11px] text-muted transition-colors hover:border-ink hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink"
          aria-label={open ? "Collapse" : "Expand"}
        >
          {open ? "▲" : "▼"}
        </button>
      </div>

      {open && (
        <div className="max-h-[50vh] overflow-y-auto px-4 pb-4 lg:max-h-[calc(100vh-140px)]">
          {tab === "play" && <AgentPicker onStart={onStart} />}
          {tab === "rules" && <RulesTab />}
        </div>
      )}
    </div>
  );
}
