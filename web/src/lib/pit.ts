/**
 * Pits are 0-indexed in the protocol/engine, but humans count from 1.
 * Use this helper anywhere a pit number is rendered to the user.
 * Never use this when sending data back to the server — the wire format stays 0-indexed.
 */
export function humanPit(action: number | null | undefined): string {
  if (action === null || action === undefined) return "—";
  return String(action + 1);
}
