from dataclasses import dataclass

import numpy as np

SOUTH = 0
NORTH = 1

_SOUTH_PITS = range(0, 6)
_NORTH_PITS = range(6, 12)

NO_PROGRESS_CAP = 100
PLY_NORMALIZER = 200.0


class IllegalMoveError(ValueError):
  pass


@dataclass(frozen=True, slots=True)
class State:
  pits: tuple[int, ...]
  stores: tuple[int, int]
  to_move: int
  ply: int
  plies_since_capture: int


def initial_state() -> State:
  return State(
    pits=(4,) * 12,
    stores=(0, 0),
    to_move=SOUTH,
    ply=0,
    plies_since_capture=0,
  )


def _own_indices(side: int) -> range:
  return _SOUTH_PITS if side == SOUTH else _NORTH_PITS


def _opp_indices(side: int) -> range:
  return _NORTH_PITS if side == SOUTH else _SOUTH_PITS


def _abs_pit(side: int, action: int) -> int:
  return action if side == SOUTH else 6 + action


def _sow_destinations(src: int, seeds: int) -> list[int]:
  dests: list[int] = []
  idx = src
  while len(dests) < seeds:
    idx = (idx + 1) % 12
    if idx == src:
      continue
    dests.append(idx)
  return dests


def _move_feeds(s: State, action: int) -> bool:
  side = s.to_move
  src = _abs_pit(side, action)
  seeds = s.pits[src]
  opp = _opp_indices(side)
  return any(d in opp for d in _sow_destinations(src, seeds))


def legal_moves(s: State) -> list[int]:
  side = s.to_move
  own = _own_indices(side)
  opp = _opp_indices(side)
  candidates = [i - own.start for i in own if s.pits[i] > 0]
  if sum(s.pits[i] for i in opp) == 0:
    return [a for a in candidates if _move_feeds(s, a)]
  return candidates


def step(s: State, action: int) -> tuple[State, int]:
  if action not in legal_moves(s):
    raise IllegalMoveError(f"action {action} not legal for side {s.to_move}")

  side = s.to_move
  src = _abs_pit(side, action)
  seeds = s.pits[src]
  dests = _sow_destinations(src, seeds)

  new_pits = list(s.pits)
  new_pits[src] = 0
  for d in dests:
    new_pits[d] += 1

  captured = _apply_captures(new_pits, last=dests[-1], side=side)

  new_stores = list(s.stores)
  new_stores[side] += captured

  next_state = State(
    pits=tuple(new_pits),
    stores=(new_stores[0], new_stores[1]),
    to_move=1 - side,
    ply=s.ply + 1,
    plies_since_capture=0 if captured > 0 else s.plies_since_capture + 1,
  )
  return _maybe_finalize(next_state), captured


def _apply_captures(pits: list[int], last: int, side: int) -> int:
  opp = _opp_indices(side)
  if last not in opp or pits[last] not in (2, 3):
    return 0

  chain: list[int] = []
  i = last
  while i in opp and pits[i] in (2, 3):
    chain.append(i)
    i = (i - 1) % 12

  opp_remaining = sum(pits[j] for j in opp if j not in chain)
  if opp_remaining == 0:
    return 0

  captured = sum(pits[j] for j in chain)
  for j in chain:
    pits[j] = 0
  return captured


def _maybe_finalize(s: State) -> State:
  if s.stores[0] >= 25 or s.stores[1] >= 25:
    return s
  if not legal_moves(s):
    return _sweep(s)
  if s.plies_since_capture >= NO_PROGRESS_CAP:
    return _sweep(s)
  return s


def _sweep(s: State) -> State:
  south_side = sum(s.pits[i] for i in _SOUTH_PITS)
  north_side = sum(s.pits[i] for i in _NORTH_PITS)
  return State(
    pits=(0,) * 12,
    stores=(s.stores[0] + south_side, s.stores[1] + north_side),
    to_move=s.to_move,
    ply=s.ply,
    plies_since_capture=s.plies_since_capture,
  )


def terminal(s: State) -> tuple[bool, int]:
  south, north = s.stores
  if south >= 25:
    return True, SOUTH
  if north >= 25:
    return True, NORTH
  if sum(s.pits) == 0:
    if south > north:
      return True, SOUTH
    if north > south:
      return True, NORTH
    return True, -1
  return False, 0


def encode(s: State) -> np.ndarray:
  side = s.to_move
  if side == SOUTH:
    my_pits = s.pits[0:6]
    opp_pits = s.pits[6:12]
    my_store, opp_store = s.stores[0], s.stores[1]
  else:
    my_pits = s.pits[6:12]
    opp_pits = s.pits[0:6]
    my_store, opp_store = s.stores[1], s.stores[0]
  ply_norm = min(s.ply / PLY_NORMALIZER, 1.0)
  return np.array(
    [*my_pits, *opp_pits, my_store, opp_store, ply_norm],
    dtype=np.float32,
  )
