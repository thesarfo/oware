import { useEffect, useState } from "react";
import { isMuted, setMuted, subscribeMuted } from "../lib/audio";

export function MuteToggle() {
  const [muted, setLocal] = useState(isMuted());

  useEffect(() => subscribeMuted(setLocal), []);

  return (
    <button
      onClick={() => setMuted(!muted)}
      className="rounded-lg border border-line px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-muted transition-colors hover:border-ink hover:text-ink dark:border-dark-line dark:text-dark-muted dark:hover:border-dark-muted dark:hover:text-dark-ink"
      aria-label={muted ? "unmute" : "mute"}
    >
      {muted ? "sound off" : "sound on"}
    </button>
  );
}
