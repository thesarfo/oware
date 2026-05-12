"""Parameterized coverage of the capture decision space."""

import pytest

from oware.engine import step
from tests.engine.conftest import state_from


@pytest.mark.parametrize(
    "pits,action,expected_captured",
    [
        ([0, 0, 0, 0, 0, 1, 0, 4, 4, 4, 4, 4], 5, 0),
        ([4, 4, 4, 4, 4, 1, 1, 4, 4, 4, 4, 4], 5, 2),
        ([4, 4, 4, 4, 4, 1, 2, 4, 4, 4, 4, 4], 5, 3),
        ([4, 4, 4, 4, 4, 1, 3, 4, 4, 4, 4, 4], 5, 0),
        ([0, 0, 0, 0, 0, 2, 1, 1, 4, 0, 0, 0], 5, 4),
        ([0, 0, 0, 0, 0, 2, 2, 1, 4, 0, 0, 0], 5, 5),
        ([0, 0, 0, 0, 0, 3, 1, 2, 2, 4, 0, 0], 5, 8),
        ([0, 0, 0, 0, 0, 2, 4, 1, 4, 0, 0, 0], 5, 2),
        ([0, 0, 0, 1, 1, 0, 4, 4, 4, 4, 4, 4], 3, 0),
        ([0, 0, 0, 0, 0, 2, 1, 1, 0, 0, 0, 0], 5, 0),
    ],
)
def test_capture_matrix(pits, action, expected_captured):
    s = state_from(pits)
    _, captured = step(s, action)
    assert captured == expected_captured


def test_capture_does_not_walk_into_own_row():
    s = state_from([0, 0, 0, 0, 0, 7, 0, 0, 0, 0, 0, 0])
    _, captured = step(s, 5)
    assert captured == 0


def test_capture_chain_stops_at_first_non_two_or_three():
    s = state_from([0, 0, 0, 0, 0, 3, 4, 1, 1, 4, 0, 0])
    s2, captured = step(s, 5)
    assert captured == 4
    assert s2.pits[6] == 5
    assert s2.pits[7] == 0
    assert s2.pits[8] == 0
    assert s2.stores == (4, 0)
