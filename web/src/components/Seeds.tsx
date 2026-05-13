interface Props {
  count: number;
  size?: "pit" | "store";
  storeOffsetY?: number;
}

const PIT_LAYOUT: ReadonlyArray<readonly [number, number]> = [
  [0, -10],
  [-9, -3],
  [9, -3],
  [-5, 8],
  [5, 8],
  [0, 0],
  [-12, 6],
  [12, 6],
  [-8, -8],
  [8, -8],
  [0, 12],
  [0, -16],
];

const STORE_LAYOUT: ReadonlyArray<readonly [number, number]> = (() => {
  const pts: Array<[number, number]> = [];
  const rows = 3;
  const cols = 10;
  const dx = 11;
  const dy = 10;
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const offsetX = row === 1 ? dx / 2 : 0;
      pts.push([(col - (cols - 1) / 2) * dx + offsetX, (row - (rows - 1) / 2) * dy]);
    }
  }
  return pts;
})();

export function Seeds({ count, size = "pit", storeOffsetY = 0 }: Props) {
  if (count <= 0) return null;
  const layout = size === "pit" ? PIT_LAYOUT : STORE_LAYOUT;
  const dotR = size === "pit" ? 4 : 3.2;
  const visible = Math.min(count, layout.length);
  const yShift = size === "store" ? storeOffsetY : 0;

  return (
    <g transform={`translate(0 ${yShift})`}>
      {Array.from({ length: visible }, (_, i) => {
        const [dx, dy] = layout[i];
        return <circle key={i} cx={dx} cy={dy} r={dotR} fill="var(--seed-color)" />;
      })}
      {count > layout.length && (
        <text
          x={size === "pit" ? 0 : layout[layout.length - 1][0] + 16}
          y={size === "pit" ? 28 : 4}
          textAnchor={size === "pit" ? "middle" : "start"}
          fill="var(--seed-color)"
          className="font-mono text-[10px]"
        >
          {size === "pit" ? count : `+${count - layout.length}`}
        </text>
      )}
    </g>
  );
}
