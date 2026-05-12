import { useEffect, useState } from "react";
import type { AgentEntry } from "../lib/protocol";

interface Props {
  onStart: (agentId: string) => void;
}

export function AgentPicker({ onStart }: Props) {
  const [agents, setAgents] = useState<AgentEntry[]>([]);
  const [selected, setSelected] = useState<string>("");

  useEffect(() => {
    fetch("/agents")
      .then((r) => r.json())
      .then((data: AgentEntry[]) => {
        setAgents(data);
        if (data.length) setSelected(data[0].id);
      });
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <div className="font-mono text-xs uppercase tracking-wide text-muted">Opponent</div>
      <div className="flex flex-col gap-1.5">
        {agents.map((a) => (
          <button
            key={a.id}
            onClick={() => setSelected(a.id)}
            className={`flex flex-col items-start border px-3 py-2 text-left transition-colors ${
              selected === a.id
                ? "border-ink bg-white"
                : "border-line hover:border-muted hover:bg-white/60"
            }`}
          >
            <span className="text-sm font-medium">{a.name}</span>
            <span className="text-[11px] text-muted">{a.description}</span>
          </button>
        ))}
      </div>

      <button
        onClick={() => selected && onStart(selected)}
        disabled={!selected}
        className="border border-ink bg-ink py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-40"
      >
        Start game
      </button>
    </div>
  );
}
