"""T-EX1..T-EX11 — direct mapping to the worked examples in docs/GAME_SPEC.md."""

from oware.engine import NORTH, SOUTH, initial_state, legal_moves, step, terminal
from tests.engine.conftest import state_from


def test_ex1_opening_sow_no_capture():
    s = initial_state()
    s2, captured = step(s, 2)
    assert s2.pits == (4, 4, 0, 5, 5, 5, 5, 4, 4, 4, 4, 4)
    assert s2.stores == (0, 0)
    assert captured == 0
    assert s2.to_move == NORTH


def test_ex2_single_capture():
    s = state_from([4, 4, 4, 4, 4, 1, 1, 4, 4, 4, 4, 4])
    s2, captured = step(s, 5)
    assert captured == 2
    assert s2.pits[5] == 0
    assert s2.pits[6] == 0
    assert s2.stores == (2, 0)


def test_ex3_chained_capture():
    s = state_from([0, 0, 0, 0, 0, 2, 1, 1, 4, 0, 0, 0])
    s2, captured = step(s, 5)
    assert captured == 4
    assert s2.pits[6] == 0
    assert s2.pits[7] == 0
    assert s2.pits[8] == 4
    assert s2.stores == (4, 0)


def test_ex4_chain_stops_at_non_two_or_three():
    s = state_from([0, 0, 0, 4, 0, 2, 4, 1, 0, 0, 0, 0])
    s2, captured = step(s, 5)
    assert captured == 2
    assert s2.pits[6] == 5
    assert s2.pits[7] == 0
    assert s2.stores == (2, 0)


def test_ex5_mid_sow_two_does_not_capture():
    s = state_from([0, 0, 0, 4, 0, 5, 1, 0, 0, 0, 0, 0])
    s2, captured = step(s, 5)
    assert captured == 0
    assert s2.pits[6] == 2
    assert s2.pits[10] == 1
    assert s2.stores == (0, 0)


def test_ex6_grand_slam_forfeit():
    s = state_from([0, 0, 0, 4, 0, 2, 1, 1, 0, 0, 0, 0])
    s2, captured = step(s, 5)
    assert captured == 0
    assert s2.pits[6] == 2
    assert s2.pits[7] == 2
    assert s2.stores == (0, 0)


def test_ex7_long_sow_skips_source():
    s = state_from([12, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0])
    s2, captured = step(s, 0)
    assert s2.pits[0] == 0
    assert s2.pits[1] == 2
    assert all(s2.pits[i] == 1 for i in range(2, 6))
    assert s2.pits[6] == 2
    assert all(s2.pits[i] == 1 for i in range(7, 12))
    assert captured == 0


def test_ex8_must_feed_forces_only_legal_move():
    s = state_from([0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0])
    assert legal_moves(s) == [5]


def test_ex9_must_feed_impossible_ends_game():
    s = state_from(
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        stores=(24, 23),
        to_move=NORTH,
    )
    s2, captured = step(s, 5)
    assert captured == 0
    assert s2.pits == (0,) * 12
    assert s2.stores == (25, 23)
    done, winner = terminal(s2)
    assert done is True
    assert winner == SOUTH


def test_ex10_majority_ends_game_without_sweep():
    s = state_from(
        [0, 0, 0, 0, 0, 2, 1, 1, 4, 0, 0, 0],
        stores=(21, 0),
    )
    s2, captured = step(s, 5)
    assert captured == 4
    assert s2.stores == (25, 0)
    assert s2.pits[8] == 4  # seeds on board not swept on majority
    done, winner = terminal(s2)
    assert done is True
    assert winner == SOUTH


def test_north_wins_via_sweep():
    s = state_from(
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        stores=(20, 24),
        to_move=NORTH,
    )
    s2, _ = step(s, 5)
    assert s2.pits == (0,) * 12
    assert s2.stores == (21, 24)
    done, winner = terminal(s2)
    assert done is True
    assert winner == NORTH


def test_ex11_no_progress_cap_draw():
    s = state_from(
        [2, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0],
        stores=(22, 22),
        plies_since_capture=99,
    )
    s2, captured = step(s, 0)
    assert captured == 0
    assert s2.pits == (0,) * 12
    assert s2.stores == (24, 24)
    done, winner = terminal(s2)
    assert done is True
    assert winner == -1
