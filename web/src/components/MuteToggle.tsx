import { useEffect, useState } from "react";
import { isMuted, setMuted, subscribeMuted } from "../lib/audio";

export function MuteToggle() {
  const [muted, setLocal] = useState(isMuted());

  useEffect(() => subscribeMuted(setLocal), []);

  return (
    <button
      onClick={() => setMuted(!muted)}
      className="border border-line bg-white/40 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-muted hover:border-ink hover:text-ink"
      aria-label={muted ? "unmute" : "mute"}
    >
      {muted ? "sound off" : "sound on"}
    </button>
  );
}
