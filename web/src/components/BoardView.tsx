import { Seeds } from "./Seeds";

export interface BoardFrame {
  pits: number[];
  stores: { south: number; north: number };
  last_move?: { by: "south" | "north"; pit: number } | null;
}

interface Props {
  frame: BoardFrame;
  legalMoves?: number[];
  onPlay?: (pit: number) => void;
  disabled?: boolean;
  flyingPit?: number | null;
  flyingTo?: "store-south" | "store-north" | null;
  hintPit?: number | null;
}

const PIT_R = 52;
const PIT_GAP = 20;
const ROW_WIDTH = 6 * (2 * PIT_R) + 5 * PIT_GAP;
const STORE_W = ROW_WIDTH * 0.52;
const STORE_H = 150;
const STORE_TO_ROW_GAP = 28;
const INTER_ROW_GAP = 36;
const TOP_PAD = 28;
const SIDE_PAD = 40;

const TOP_ROW_ABS = [11, 10, 9, 8, 7, 6];
const BOTTOM_ROW_ABS = [0, 1, 2, 3, 4, 5];

const COLORS = {
  player: { fill: "var(--store-player-fill)", stroke: "var(--store-player-stroke)" },
  agent: { fill: "var(--store-agent-fill)", stroke: "var(--store-agent-stroke)" },
};

function Pit({
  cx,
  cy,
  count,
  highlight,
  hint,
  clickable,
  onClick,
}: {
  cx: number;
  cy: number;
  count: number;
  highlight?: boolean;
  hint?: boolean;
  clickable: boolean;
  onClick: () => void;
}) {
  const fill = highlight
    ? "var(--pit-highlight-fill)"
    : "var(--pit-player-fill)";
  const stroke = hint
    ? "var(--seed-color)"
    : clickable
      ? "var(--pit-player-stroke)"
      : "var(--pit-agent-stroke)";
  return (
    <g
      transform={`translate(${cx} ${cy})`}
      onClick={clickable ? onClick : undefined}
      className={clickable ? "cursor-pointer" : ""}
    >
      <circle
        r={PIT_R}
        fill={fill}
        stroke={stroke}
        strokeWidth={hint ? 2.5 : 1.5}
        strokeDasharray={hint ? "4 3" : undefined}
        className={clickable ? "transition-colors hover:fill-[var(--pit-hover-fill)]" : ""}
      />
      <Seeds count={count} size="pit" />
    </g>
  );
}

function Store({
  x,
  y,
  count,
  orientation,
  kind,
}: {
  x: number;
  y: number;
  count: number;
  orientation: "top" | "bottom";
  kind: "player" | "agent";
}) {
  const sx = STORE_W / 230;
  const sy = STORE_H / 150;
  const colors = COLORS[kind];
  const p = (px: number, py: number) => `${px * sx} ${py * sy}`;
  const d = [
    `M ${p(-100, 30)}`, `L ${p(100, 30)}`,
    `C ${p(108, 30)} ${p(115, 23)} ${p(115, 15)}`,
    `C ${p(115, -120)} ${p(-115, -120)} ${p(-115, 15)}`,
    `C ${p(-115, 23)} ${p(-108, 30)} ${p(-100, 30)}`,
    `Z`,
  ].join(" ");
  const transform =
    orientation === "top"
      ? `translate(${x} ${y}) scale(1,-1)`
      : `translate(${x} ${y})`;
  return (
    <g transform={transform}>
      <path d={d} fill={colors.fill} stroke={colors.stroke} strokeWidth={1.5} />
      <Seeds count={count} size="store" storeOffsetY={0} />
    </g>
  );
}

export function BoardView({
  frame,
  legalMoves,
  onPlay,
  disabled,
  flyingPit,
  flyingTo,
  hintPit,
}: Props) {
  const w = ROW_WIDTH + 2 * SIDE_PAD;
  const topStoreY = TOP_PAD + STORE_H / 2;
  const topY = TOP_PAD + STORE_H + STORE_TO_ROW_GAP + PIT_R;
  const botY = topY + 2 * PIT_R + INTER_ROW_GAP;
  const botStoreY = botY + PIT_R + STORE_TO_ROW_GAP + STORE_H / 2;
  const h = botStoreY + STORE_H / 2 + TOP_PAD + 14;

  const xFor = (col: number) => SIDE_PAD + col * (2 * PIT_R + PIT_GAP) + PIT_R;

  const legal = new Set(legalMoves ?? []);
  const lastPit = frame.last_move?.pit;
  const lastBy = frame.last_move?.by;

  function centerFor(abs: number) {
    const topIdx = TOP_ROW_ABS.indexOf(abs);
    if (topIdx >= 0) return { x: xFor(topIdx), y: topY };
    return { x: xFor(BOTTOM_ROW_ABS.indexOf(abs)), y: botY };
  }

  const flyingCenter =
    flyingTo === "store-south"
      ? { x: w / 2, y: botStoreY }
      : flyingTo === "store-north"
        ? { x: w / 2, y: topStoreY }
        : flyingPit !== null && flyingPit !== undefined
          ? centerFor(flyingPit)
          : null;

  // hintPit is in human-action coordinates (0..5 from south's perspective)
  const hintAbs = hintPit !== null && hintPit !== undefined ? hintPit : null;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="max-w-full select-none">
      <Store x={w / 2} y={topStoreY} count={frame.stores.north} orientation="top" kind="agent" />
      <Store x={w / 2} y={botStoreY} count={frame.stores.south} orientation="bottom" kind="player" />

      {TOP_ROW_ABS.map((abs, col) => {
        const isHighlight =
          lastPit !== undefined && lastBy === "north" && abs === 6 + lastPit;
        return (
          <Pit
            key={abs}
            cx={xFor(col)}
            cy={topY}
            count={frame.pits[abs]}
            highlight={isHighlight}
            clickable={false}
            onClick={() => undefined}
          />
        );
      })}

      {BOTTOM_ROW_ABS.map((abs, col) => {
        const humanAction = col;
        const isClickable = !disabled && (legal.has(humanAction) || false) && !!onPlay;
        const isHighlight =
          lastPit !== undefined && lastBy === "south" && abs === lastPit;
        const isHint = hintAbs !== null && humanAction === hintAbs;
        return (
          <Pit
            key={abs}
            cx={xFor(col)}
            cy={botY}
            count={frame.pits[abs]}
            highlight={isHighlight}
            hint={isHint}
            clickable={isClickable}
            onClick={() => onPlay?.(humanAction)}
          />
        );
      })}

      {flyingCenter && (
        <circle
          cx={flyingCenter.x}
          cy={flyingCenter.y}
          r={6}
          fill="var(--seed-color)"
          style={{ transition: "cx 110ms ease-out, cy 110ms ease-out" }}
        />
      )}
    </svg>
  );
}
