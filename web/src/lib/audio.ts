let ctx: AudioContext | null = null;
let muted = (typeof localStorage !== "undefined" && localStorage.getItem("oware.muted") === "1") || false;
const subscribers = new Set<(m: boolean) => void>();

function getCtx(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!ctx) {
    const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return null;
    ctx = new Ctor();
  }
  if (ctx.state === "suspended") void ctx.resume();
  return ctx;
}

export function isMuted(): boolean {
  return muted;
}

export function setMuted(v: boolean): void {
  muted = v;
  try {
    localStorage.setItem("oware.muted", v ? "1" : "0");
  } catch {
    // ignore
  }
  subscribers.forEach((fn) => fn(v));
}

export function subscribeMuted(fn: (m: boolean) => void): () => void {
  subscribers.add(fn);
  return () => subscribers.delete(fn);
}

function vibrate(ms: number): void {
  if (typeof navigator !== "undefined" && typeof navigator.vibrate === "function") {
    navigator.vibrate(ms);
  }
}

export function tick(): void {
  if (muted) return;
  const c = getCtx();
  if (!c) return;
  const t = c.currentTime;
  const osc = c.createOscillator();
  const filt = c.createBiquadFilter();
  const gain = c.createGain();

  osc.type = "triangle";
  const f0 = 760 + Math.random() * 120;
  osc.frequency.setValueAtTime(f0, t);
  osc.frequency.exponentialRampToValueAtTime(180, t + 0.04);

  filt.type = "bandpass";
  filt.frequency.value = 1100;
  filt.Q.value = 1.2;

  gain.gain.setValueAtTime(0.0001, t);
  gain.gain.exponentialRampToValueAtTime(0.18, t + 0.003);
  gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.06);

  osc.connect(filt).connect(gain).connect(c.destination);
  osc.start(t);
  osc.stop(t + 0.08);
  vibrate(4);
}

export function thock(): void {
  if (muted) return;
  const c = getCtx();
  if (!c) return;
  const t = c.currentTime;
  const osc = c.createOscillator();
  const gain = c.createGain();

  osc.type = "sine";
  osc.frequency.setValueAtTime(220, t);
  osc.frequency.exponentialRampToValueAtTime(80, t + 0.12);

  gain.gain.setValueAtTime(0.0001, t);
  gain.gain.exponentialRampToValueAtTime(0.28, t + 0.005);
  gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.22);

  osc.connect(gain).connect(c.destination);
  osc.start(t);
  osc.stop(t + 0.25);
  vibrate(14);
}

export function primeAudio(): void {
  getCtx();
}
