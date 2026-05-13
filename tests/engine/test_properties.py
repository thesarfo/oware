"""Property-based tests on reachable states (see docs/TEST_PLAN.md)."""

import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from oware.engine import (
  SOUTH,
  IllegalMoveError,
  State,
  initial_state,
  legal_moves,
  step,
  terminal,
)


def _own_row(s: State) -> range:
  return range(0, 6) if s.to_move == SOUTH else range(6, 12)


def _opp_row(s: State) -> range:
  return range(6, 12) if s.to_move == SOUTH else range(0, 6)


@st.composite
def reachable_state(draw) -> State:
  seed = draw(st.integers(min_value=0, max_value=2**31 - 1))
  plies = draw(st.integers(min_value=0, max_value=120))
  rng = random.Random(seed)
  s = initial_state()
  for _ in range(plies):
    done, _ = terminal(s)
    if done:
      break
    moves = legal_moves(s)
    if not moves:
      break
    s, _ = step(s, rng.choice(moves))
  return s


@given(s=reachable_state())
def test_seed_conservation(s: State):
  assert sum(s.pits) + sum(s.stores) == 48


@given(s=reachable_state())
def test_non_negativity(s: State):
  assert all(p >= 0 for p in s.pits)
  assert all(c >= 0 for c in s.stores)
  assert s.plies_since_capture >= 0


@given(s=reachable_state())
def test_turn_alternation_on_non_terminal_step(s: State):
  done, _ = terminal(s)
  if done:
    return
  moves = legal_moves(s)
  if not moves:
    return
  s2, _ = step(s, moves[0])
  done2, _ = terminal(s2)
  if not done2:
    assert s2.to_move == 1 - s.to_move


@given(s=reachable_state())
def test_legal_move_soundness(s: State):
  done, _ = terminal(s)
  if done:
    return
  for a in legal_moves(s):
    step(s, a)


@given(s=reachable_state())
def test_legal_move_completeness(s: State):
  done, _ = terminal(s)
  if done:
    return
  legal = set(legal_moves(s))
  for a in range(6):
    if a not in legal:
      with pytest.raises(IllegalMoveError):
        step(s, a)


@given(s=reachable_state())
def test_must_feed_contract(s: State):
  done, _ = terminal(s)
  if done:
    return
  opp = _opp_row(s)
  if sum(s.pits[i] for i in opp) > 0:
    return
  for a in legal_moves(s):
    s2, _ = step(s, a)
    assert sum(s2.pits[i] for i in opp) > 0


@given(s=reachable_state())
def test_grand_slam_invariant(s: State):
  done, _ = terminal(s)
  if done:
    return
  for a in legal_moves(s):
    s2, _ = step(s, a)
    done2, _ = terminal(s2)
    if done2:
      continue
    own_new = _own_row(s2)
    assert sum(s2.pits[i] for i in own_new) > 0


@given(s=reachable_state())
def test_capture_bound(s: State):
  done, _ = terminal(s)
  if done:
    return
  for a in legal_moves(s):
    _, captured = step(s, a)
    assert 0 <= captured <= 15


@given(s=reachable_state())
def test_determinism(s: State):
  done, _ = terminal(s)
  if done:
    return
  for a in legal_moves(s):
    s_a, c_a = step(s, a)
    s_b, c_b = step(s, a)
    assert s_a == s_b
    assert c_a == c_b


@settings(max_examples=20)
@given(seed=st.integers(min_value=0, max_value=2**31 - 1))
def test_random_self_play_terminates(seed: int):
  rng = random.Random(seed)
  s = initial_state()
  for _ in range(2000):
    assert sum(s.pits) + sum(s.stores) == 48
    done, _ = terminal(s)
    if done:
      return
    moves = legal_moves(s)
    assert moves, "non-terminal state must have at least one legal move"
    s, _ = step(s, rng.choice(moves))
  pytest.fail(f"self-play did not terminate within 2000 plies (seed={seed})")
