import { useState } from "react";
import { AgentPicker } from "./AgentPicker";
import { RulesTab } from "./RulesTab";
// import { StatsTab } from "./StatsTab";

interface Props {
  onStart: (agentId: string) => void;
}

type Tab = "play" | "rules" | "stats";

const TABS: { id: Tab; label: string }[] = [
  { id: "play", label: "Play" },
  { id: "rules", label: "Rules" },
];

export function Sidebar({ onStart }: Props) {
  const [tab, setTab] = useState<Tab>("play");

  return (
    <div className="flex w-80 flex-col border border-line bg-white/40">
      <div className="flex border-b border-line">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 border-b-2 py-2 font-mono text-[11px] uppercase tracking-wider transition-colors ${
              tab === t.id
                ? "border-ink text-ink"
                : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="max-h-[calc(100vh-140px)] overflow-y-auto p-5">
        {tab === "play" && <AgentPicker onStart={onStart} />}
        {tab === "rules" && <RulesTab />}
        {/* {tab === "stats" && <StatsTab />} */}
      </div>
    </div>
  );
}
