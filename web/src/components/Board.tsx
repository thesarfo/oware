import { Seeds } from "./Seeds";
import { useBoardAnimation } from "../hooks/useBoardAnimation";
import type { GameState } from "../lib/protocol";

interface Props {
  state: GameState;
  onPlay: (pit: number) => void;
  disabled: boolean;
}

const PIT_R = 44;
const PIT_GAP = 28;
const ROW_WIDTH = 6 * (2 * PIT_R) + 5 * PIT_GAP;
const STORE_W = ROW_WIDTH * 0.62;
const STORE_H = 84;
const STORE_TO_ROW_GAP = 56;
const INTER_ROW_GAP = 36;
const TOP_PAD = 28;
const SIDE_PAD = 40;
const STORE_SEED_INSET = 10;

const TOP_ROW_ABS = [11, 10, 9, 8, 7, 6];
const BOTTOM_ROW_ABS = [0, 1, 2, 3, 4, 5];

const COLORS = {
  player: { fill: "#ece4d2", stroke: "#a89368" },
  agent: { fill: "#dde2e8", stroke: "#7b8794" },
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
        fill={highlight ? "#ececea" : "transparent"}
        stroke={clickable ? "#7a7a7a" : "#c4c4c4"}
        strokeWidth={1.5}
        className={clickable ? "transition-colors hover:fill-[#ececea]" : ""}
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
  label,
}: {
  x: number;
  y: number;
  count: number;
  orientation: "top" | "bottom";
  kind: "player" | "agent";
  label: string;
}) {
  const halfW = STORE_W / 2;
  const halfH = STORE_H / 2;
  const d =
    orientation === "top"
      ? `M ${-halfW} ${halfH} A ${halfW} ${STORE_H} 0 0 1 ${halfW} ${halfH} Z`
      : `M ${-halfW} ${-halfH} A ${halfW} ${STORE_H} 0 0 0 ${halfW} ${-halfH} Z`;
  const seedOffset = orientation === "top" ? STORE_SEED_INSET : -STORE_SEED_INSET;
  const colors = COLORS[kind];
  const labelY = orientation === "top" ? halfH + 16 : -halfH - 8;
  return (
    <g transform={`translate(${x} ${y})`}>
      <path d={d} fill={colors.fill} stroke={colors.stroke} strokeWidth={1.5} />
      <Seeds count={count} size="store" storeOffsetY={seedOffset} />
      <text
        x={0}
        y={labelY}
        textAnchor="middle"
        className="fill-muted font-mono text-[10px] uppercase tracking-wider"
      >
        {label}
      </text>
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
          fill="#3a3a3a"
          style={{ transition: "cx 110ms ease-out, cy 110ms ease-out" }}
        />
      )}
    </svg>
  );
}
