import gymnasium as gym
import numpy as np
from gymnasium import spaces

from oware.engine import (
  State,
  encode,
  initial_state,
  legal_moves,
  step,
  terminal,
)


class OwareEnv(gym.Env):
  """Single-player view: caller controls the side-to-move each step.

  The env presents the board from the current side-to-move's perspective
  via encode(). Both sides are driven by the caller — no opponent logic here.
  """

  metadata = {"render_modes": []}

  def __init__(self) -> None:
    super().__init__()
    # Pits: 0–48 seeds each; stores: 0–48; ply_norm: 0–1
    obs_low = np.zeros(15, dtype=np.float32)
    obs_high = np.array([48.0] * 12 + [48.0, 48.0, 1.0], dtype=np.float32)
    self.observation_space = spaces.Dict(
      {
        "observation": spaces.Box(obs_low, obs_high, dtype=np.float32),
        "action_mask": spaces.MultiBinary(6),
      }
    )
    self.action_space = spaces.Discrete(6)
    self._state: State = initial_state()

  def reset(
    self,
    *,
    seed: int | None = None,
    options: dict | None = None,
  ) -> tuple[dict, dict]:
    super().reset(seed=seed)
    self._state = initial_state()
    return self._obs(), {}

  def step(self, action: int) -> tuple[dict, float, bool, bool, dict]:
    side = self._state.to_move
    next_state, captured = step(self._state, action)
    self._state = next_state
    done, winner = terminal(next_state)
    if done:
      if winner == side:
        reward = 1.0
      elif winner == -1:
        reward = 0.0
      else:
        reward = -1.0
    else:
      reward = 0.0
    return self._obs(), reward, done, False, {"captured": captured}

  def _obs(self) -> dict:
    mask = np.zeros(6, dtype=np.int8)
    for m in legal_moves(self._state):
      mask[m] = 1
    return {
      "observation": encode(self._state),
      "action_mask": mask,
    }

  @property
  def state(self) -> State:
    return self._state
