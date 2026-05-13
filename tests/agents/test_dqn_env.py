import numpy as np
from gymnasium.utils.env_checker import check_env

from oware.agents.dqn.env import OwareEnv
from oware.engine import legal_moves, terminal


def test_env_checker():
  check_env(OwareEnv(), warn=True)


def test_action_mask_matches_legal_moves():
  env = OwareEnv()
  obs, _ = env.reset(seed=0)
  mask = obs["action_mask"]
  expected = legal_moves(env.state)
  assert list(np.where(mask)[0]) == expected


def test_reward_zero_on_non_terminal():
  env = OwareEnv()
  obs, _ = env.reset(seed=0)
  legal = list(np.where(obs["action_mask"])[0])
  _, reward, terminated, _, _ = env.step(legal[0])
  if not terminated:
    assert reward == 0.0


def test_reward_nonzero_on_terminal():
  """Play a full game and verify the final reward is ±1 or 0."""
  env = OwareEnv()
  obs, _ = env.reset(seed=7)
  final_reward = None
  for _ in range(1000):
    legal = list(np.where(obs["action_mask"])[0])
    if not legal:
      break
    action = legal[0]
    obs, reward, terminated, _, _ = env.step(action)
    if terminated:
      final_reward = reward
      break
  assert final_reward in (-1.0, 0.0, 1.0)


def test_seed_conservation():
  """Total seeds in pits + stores must always equal 48."""
  env = OwareEnv()
  env.reset(seed=0)
  for _ in range(200):
    s = env.state
    done, _ = terminal(s)
    if done:
      break
    legal = legal_moves(s)
    env.step(legal[0])
    s = env.state
    assert sum(s.pits) + s.stores[0] + s.stores[1] == 48


def test_reset_is_deterministic():
  env = OwareEnv()
  obs1, _ = env.reset(seed=42)
  obs2, _ = env.reset(seed=42)
  np.testing.assert_array_equal(obs1["observation"], obs2["observation"])
