import type { ReactNode } from "react";

interface Props {
  left?: ReactNode;
  right?: ReactNode;
  children: ReactNode; // title
}

/**
 * Responsive page header.
 * Mobile : title centred on its own row, left/right nav below it.
 * sm+    : single row — left | title | right, equal-width thirds.
 */
export function PageHeader({ left, right, children }: Props) {
  return (
    <header className="px-4 py-3 sm:px-6 sm:py-4">
      {/* ── Mobile layout ── */}
      <div className="flex flex-col gap-2 sm:hidden">
        <div className="text-center font-mono text-base font-semibold uppercase tracking-widest">
          {children}
        </div>
        {(left || right) && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">{left ?? <span />}</div>
            <div className="flex items-center gap-2">{right ?? <span />}</div>
          </div>
        )}
      </div>

      {/* ── Desktop layout ── */}
      <div className="hidden sm:flex sm:items-center sm:justify-between">
        <div className="flex flex-1 items-center gap-2">{left}</div>
        <div className="font-mono text-base font-semibold uppercase tracking-widest">
          {children}
        </div>
        <div className="flex flex-1 items-center justify-end gap-2">{right}</div>
      </div>
    </header>
  );
}
