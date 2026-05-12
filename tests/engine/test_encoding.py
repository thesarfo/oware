from oware.engine import NORTH, SOUTH, encode, initial_state
from tests.engine.conftest import state_from


def test_encode_initial_state_shape_and_dtype():
    obs = encode(initial_state())
    assert obs.shape == (15,)
    assert obs.dtype.name == "float32"


def test_encode_is_from_side_to_move_perspective():
    pits = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    south_obs = encode(state_from(pits, stores=(3, 5), to_move=SOUTH))
    north_obs = encode(state_from(pits, stores=(3, 5), to_move=NORTH))

    assert list(south_obs[:6]) == [1, 2, 3, 4, 5, 6]
    assert list(south_obs[6:12]) == [7, 8, 9, 10, 11, 12]
    assert south_obs[12] == 3
    assert south_obs[13] == 5

    assert list(north_obs[:6]) == [7, 8, 9, 10, 11, 12]
    assert list(north_obs[6:12]) == [1, 2, 3, 4, 5, 6]
    assert north_obs[12] == 5
    assert north_obs[13] == 3


def test_encode_ply_is_normalized():
    obs0 = encode(initial_state())
    obs_late = encode(state_from([4] * 12, ply=400))
    assert obs0[14] == 0.0
    assert obs_late[14] == 1.0
