from collections.abc import Sequence

from oware.engine import SOUTH, State


def state_from(
  pits: Sequence[int],
  *,
  stores: tuple[int, int] = (0, 0),
  to_move: int = SOUTH,
  ply: int = 0,
  plies_since_capture: int = 0,
) -> State:
  assert len(pits) == 12
  return State(
    pits=tuple(pits),
    stores=stores,
    to_move=to_move,
    ply=ply,
    plies_since_capture=plies_since_capture,
  )
