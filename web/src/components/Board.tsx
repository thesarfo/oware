import { Seeds } from "./Seeds";
import { useBoardAnimation } from "../hooks/useBoardAnimation";
import type { GameState } from "../lib/protocol";

interface Props {
  state: GameState;
  onPlay: (pit: number) => void;
  disabled: boolean;
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
  clickable,
  onClick,
}: {
  cx: number;
  cy: number;
  count: number;
  highlight?: boolean;
  clickable: boolean;
  onClick: () => void;
}) {
  return (
    <g
      transform={`translate(${cx} ${cy})`}
      onClick={clickable ? onClick : undefined}
      className={clickable ? "cursor-pointer" : ""}
    >
      <circle
        r={PIT_R}
        fill={highlight ? "var(--pit-highlight-fill)" : "var(--pit-player-fill)"}
        stroke={clickable ? "var(--pit-player-stroke)" : "var(--pit-agent-stroke)"}
        strokeWidth={1.5}
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
  label: string;
}) {
  // Path designed in 230×150 space: x ±115, y from -120 to +30.
  // Scale to STORE_W × STORE_H.
  const sx = STORE_W / 230;
  const sy = STORE_H / 150;
  const colors = COLORS[kind];

  function p(px: number, py: number) { return `${px * sx} ${py * sy}`; }

  const d = [
    `M ${p(-100, 30)}`, `L ${p(100, 30)}`,
    `C ${p(108, 30)} ${p(115, 23)} ${p(115, 15)}`,
    `C ${p(115, -120)} ${p(-115, -120)} ${p(-115, 15)}`,
    `C ${p(-115, 23)} ${p(-108, 30)} ${p(-100, 30)}`,
    `Z`,
  ].join(" ");

  const transform = orientation === "top"
    ? `translate(${x} ${y}) scale(1,-1)`
    : `translate(${x} ${y})`;

  return (
    <g transform={transform}>
      <path d={d} fill={colors.fill} stroke={colors.stroke} strokeWidth={1.5} />
      <Seeds count={count} size="store" storeOffsetY={0} />
    </g>
  );
}

export function Board({ state, onPlay, disabled }: Props) {
  const anim = useBoardAnimation(state);
  const view = anim.displayed ?? state;
  const isAnimating = anim.animating;

  const w = ROW_WIDTH + 2 * SIDE_PAD;
  const topStoreY = TOP_PAD + STORE_H / 2;
  const topY = TOP_PAD + STORE_H + STORE_TO_ROW_GAP + PIT_R;
  const botY = topY + 2 * PIT_R + INTER_ROW_GAP;
  const botStoreY = botY + PIT_R + STORE_TO_ROW_GAP + STORE_H / 2;
  const h = botStoreY + STORE_H / 2 + TOP_PAD + 14;

  const xFor = (col: number) => SIDE_PAD + col * (2 * PIT_R + PIT_GAP) + PIT_R;

  const legal = new Set(view.legal_moves);
  const lastPit = view.last_move?.pit;
  const lastBy = view.last_move?.by;

  function centerFor(abs: number): { x: number; y: number } {
    const topIdx = TOP_ROW_ABS.indexOf(abs);
    if (topIdx >= 0) return { x: xFor(topIdx), y: topY };
    return { x: xFor(BOTTOM_ROW_ABS.indexOf(abs)), y: botY };
  }

  const flyingCenter =
    anim.flyingTo === "store-south"
      ? { x: w / 2, y: botStoreY }
      : anim.flyingTo === "store-north"
        ? { x: w / 2, y: topStoreY }
        : anim.flyingPit !== null
          ? centerFor(anim.flyingPit)
          : null;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="max-w-full select-none">
      <Store
        x={w / 2}
        y={topStoreY}
        count={view.stores.north}
        orientation="top"
        kind="agent"
        label="agent"
      />
      <Store
        x={w / 2}
        y={botStoreY}
        count={view.stores.south}
        orientation="bottom"
        kind="player"
        label="you"
      />

      {TOP_ROW_ABS.map((abs, col) => {
        const isHighlight = lastPit !== undefined && lastBy === "north" && abs === 6 + lastPit;
        return (
          <Pit
            key={abs}
            cx={xFor(col)}
            cy={topY}
            count={view.pits[abs]}
            highlight={isHighlight}
            clickable={false}
            onClick={() => undefined}
          />
        );
      })}

      {BOTTOM_ROW_ABS.map((abs, col) => {
        const humanAction = col;
        const isClickable = !disabled && !isAnimating && legal.has(humanAction);
        const isHighlight = lastPit !== undefined && lastBy === "south" && abs === lastPit;
        return (
          <Pit
            key={abs}
            cx={xFor(col)}
            cy={botY}
            count={view.pits[abs]}
            highlight={isHighlight}
            clickable={isClickable}
            onClick={() => onPlay(humanAction)}
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
