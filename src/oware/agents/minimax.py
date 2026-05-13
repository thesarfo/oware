"""Minimax agent with alpha-beta pruning, iterative deepening, and Zobrist TT."""

import time
from typing import Any

import numpy as np

from oware.agents.base import AgentInfo
from oware.engine import NORTH, SOUTH, State, legal_moves, step, terminal

_rng = np.random.default_rng(0xDEADBEEF)
_ZOB_PITS = _rng.integers(0, 2**63, size=(12, 49), dtype=np.int64)
_ZOB_PITS.flags.writeable = False
_ZOB_SIDE: int = int(_rng.integers(0, 2**63))
del _rng


def zobrist_hash(s: State) -> int:
  h = np.int64(0)
  for i, count in enumerate(s.pits):
    h ^= _ZOB_PITS[i, count]
  if s.to_move == NORTH:
    h ^= _ZOB_SIDE
  return int(h)


def heuristic_eval(s: State, side: int) -> float:
  opp = 1 - side
  own_pits = s.pits[0:6] if side == SOUTH else s.pits[6:12]
  own_mobility = len(legal_moves(s))
  opp_mobility = len(
    legal_moves(
      State(
        pits=s.pits,
        stores=s.stores,
        to_move=opp,
        ply=s.ply,
        plies_since_capture=s.plies_since_capture,
      )
    )
  )
  return (
    s.stores[side]
    - s.stores[opp]
    + 0.5 * (own_mobility - opp_mobility)
    + 0.1 * sum(own_pits[3:6])
  )


_EXACT = 0
_LOWER = 1
_UPPER = 2


def _negamax(
  s: State,
  depth: int,
  alpha: float,
  beta: float,
  side: int,
  tt: dict[int, tuple[int, int, float]],
  nodes: list[int],
) -> float:
  nodes[0] += 1
  done, winner = terminal(s)
  if done:
    if winner == side:
      return 1000.0
    if winner == -1:
      return 0.0
    return -1000.0

  if depth == 0:
    return heuristic_eval(s, side)

  key = zobrist_hash(s)
  tt_entry = tt.get(key)
  if tt_entry is not None:
    tt_depth, tt_flag, tt_val = tt_entry
    if tt_depth >= depth:
      if tt_flag == _EXACT:
        return tt_val
      if tt_flag == _LOWER:
        alpha = max(alpha, tt_val)
      elif tt_flag == _UPPER:
        beta = min(beta, tt_val)
      if alpha >= beta:
        return tt_val

  moves = legal_moves(s)
  moves.sort(key=lambda a: step(s, a)[1], reverse=True)

  orig_alpha = alpha
  best = -float("inf")
  for action in moves:
    child, _ = step(s, action)
    val = -_negamax(child, depth - 1, -beta, -alpha, 1 - side, tt, nodes)
    if val > best:
      best = val
    alpha = max(alpha, val)
    if alpha >= beta:
      break

  flag = _EXACT if orig_alpha < best < beta else (_LOWER if best >= beta else _UPPER)
  tt[key] = (depth, flag, best)
  return best


def iterative_deepening(
  s: State,
  max_depth: int,
  budget_ms: int,
) -> tuple[int, dict[str, Any]]:
  deadline = time.perf_counter() + budget_ms / 1000.0
  moves = legal_moves(s)
  best_action = moves[0]
  best_score = -float("inf")
  best_scores: dict[int, float] = {}
  depth_reached = 0
  tt: dict[int, tuple[int, int, float]] = {}
  nodes: list[int] = [0]
  side = s.to_move

  for depth in range(1, max_depth + 1):
    if time.perf_counter() >= deadline:
      break
    current_best_action = best_action
    current_best_score = -float("inf")
    current_scores: dict[int, float] = {}
    ordered = [best_action] + [m for m in moves if m != best_action]
    for action in ordered:
      if time.perf_counter() >= deadline:
        break
      child, _ = step(s, action)
      val = -_negamax(
        child, depth - 1, -float("inf"), float("inf"), 1 - side, tt, nodes
      )
      current_scores[action] = val
      if val > current_best_score:
        current_best_score = val
        current_best_action = action
    else:
      # Only promote results from a fully-searched depth; a partial depth
      # may have missed the best move and would regress quality.
      best_action = current_best_action
      best_score = current_best_score
      best_scores = current_scores
      depth_reached = depth
      continue
    break

  scores = [best_scores.get(i) for i in range(6)]
  return best_action, {
    "depth_reached": depth_reached,
    "score": best_score,
    "nodes": nodes[0],
    "scores": scores,
  }


class MinimaxAgent:
  def __init__(self, max_depth: int, time_budget_ms: int = 5000) -> None:
    self._max_depth = max_depth
    self._budget_ms = time_budget_ms
    self.info = AgentInfo(
      id=f"minimax_d{max_depth}",
      name=f"Minimax d{max_depth}",
      family="minimax",
      description=f"Alpha-beta minimax, iterative deepening to depth {max_depth}.",
      est_elo={2: 600, 4: 900, 6: 1100}.get(max_depth, 900),
    )

  def choose_move(
    self,
    state: State,
    *,
    time_budget_ms: int | None = None,
  ) -> tuple[int, dict[str, Any]]:
    budget = time_budget_ms if time_budget_ms is not None else self._budget_ms
    return iterative_deepening(state, self._max_depth, budget)
