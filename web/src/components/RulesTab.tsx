interface Rule {
  title: string;
  body: string;
}

const RULES: Rule[] = [
  {
    title: "Sowing",
    body: "Pick one of your own pits. Scoop all its seeds and drop them one by one anti-clockwise into the following pits. If you held 12 or more, skip the source pit when you lap.",
  },
  {
    title: "Capture",
    body: "If your last seed lands in an opponent pit that now totals 2 or 3, those seeds are yours. Walk backwards through the opponent's row, capturing every adjacent 2 or 3, stopping at the first non-2/3 or your own row.",
  },
  {
    title: "Grand slam",
    body: "If a capture would empty every seed on your opponent's side, the capture is forfeited. Sowing still happens; nothing enters your store.",
  },
  {
    title: "Must feed",
    body: "If your opponent has no seeds, you must play a move that delivers at least one seed to their row. If you can't, the game ends.",
  },
  {
    title: "Winning",
    body: "First player to capture 25 seeds wins. 24-24 is a draw. The game also ends if 100 plies pass with no capture — each player keeps the seeds on their own side.",
  },
];

export function RulesTab() {
  return (
    <div className="flex flex-col gap-3">
      <div className="font-mono text-xs uppercase tracking-wide text-muted">Abapa rules</div>
      <div className="flex flex-col gap-2.5">
        {RULES.map((r) => (
          <div key={r.title} className="border border-line bg-white/40 px-3 py-2.5">
            <div className="font-mono text-[11px] uppercase tracking-wider text-muted">
              {r.title}
            </div>
            <div className="mt-1 text-[12px] leading-snug text-ink">{r.body}</div>
          </div>
        ))}
      </div>
      <div className="text-[11px] leading-relaxed text-muted">
        Variant: Abapa, the tournament ruleset played across West Africa and the Caribbean (also
        known as Ayoayo, Awale, Warri, Adji-Boto).
      </div>
    </div>
  );
}
