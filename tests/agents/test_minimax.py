from oware.agents.minimax import (
  MinimaxAgent,
  heuristic_eval,
  zobrist_hash,
)
from oware.engine import NORTH, SOUTH, State, initial_state, legal_moves, step


def test_hash_deterministic():
  s = initial_state()
  assert zobrist_hash(s) == zobrist_hash(s)


def test_hash_differs_by_side():
  s = initial_state()
  flipped = State(
    pits=s.pits,
    stores=s.stores,
    to_move=NORTH,
    ply=s.ply,
    plies_since_capture=s.plies_since_capture,
  )
  assert zobrist_hash(s) != zobrist_hash(flipped)


def test_hash_differs_after_move():
  s = initial_state()
  s2, _ = step(s, 0)
  assert zobrist_hash(s) != zobrist_hash(s2)


def test_heuristic_favours_more_seeds_in_store():
  # South has 10 seeds in store, north has 2
  s = State(pits=(4,) * 12, stores=(10, 2), to_move=SOUTH, ply=0, plies_since_capture=0)
  assert heuristic_eval(s, SOUTH) > heuristic_eval(s, NORTH)


def test_heuristic_symmetric_on_initial():
  s = initial_state()
  # Both sides equal — scores should be equal in magnitude
  assert abs(heuristic_eval(s, SOUTH) - heuristic_eval(s, NORTH)) < 1e-6


def test_returns_legal_move():
  s = initial_state()
  agent = MinimaxAgent(max_depth=2)
  action, extras = agent.choose_move(s)
  assert action in legal_moves(s)
  assert "depth_reached" in extras


def test_forced_win_found():
  # South has 24 seeds in store; one move captures 1 seed → wins.
  # Build a state where south can capture exactly 1 seed to reach 25.
  # North pit 6 has 2 seeds; south pit 0 sows into it.
  pits = [1] + [0] * 5 + [2] + [0] * 5  # south pit0=1, north pit6=2
  s = State(
    pits=tuple(pits), stores=(24, 0), to_move=SOUTH, ply=0, plies_since_capture=0
  )
  agent = MinimaxAgent(max_depth=4)
  action, _ = agent.choose_move(s)
  # The only legal move is pit 0; it should capture and win
  assert action == 0


def test_respects_tight_budget():
  """Agent must return within a very tight budget without crashing."""
  s = initial_state()
  agent = MinimaxAgent(max_depth=6, time_budget_ms=50)
  action, extras = agent.choose_move(s)
  assert action in legal_moves(s)
  assert extras["depth_reached"] >= 1


def test_d6_completes_on_initial_state():
  """Depth-6 on initial state must finish in reasonable time (< 30 s)."""
  import time

  s = initial_state()
  agent = MinimaxAgent(max_depth=6)
  t0 = time.perf_counter()
  action, _ = agent.choose_move(s)
  elapsed = time.perf_counter() - t0
  assert action in legal_moves(s)
  assert elapsed < 30.0
