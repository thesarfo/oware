import numpy as np
import torch


class ReplayBuffer:
  def __init__(self, capacity: int = 200_000) -> None:
    self._cap = capacity
    self._pos = 0
    self._size = 0
    self._obs = np.zeros((capacity, 15), dtype=np.float32)
    self._actions = np.zeros(capacity, dtype=np.int64)
    self._rewards = np.zeros(capacity, dtype=np.float32)
    self._next_obs = np.zeros((capacity, 15), dtype=np.float32)
    self._dones = np.zeros(capacity, dtype=np.float32)
    self._next_masks = np.zeros((capacity, 6), dtype=np.float32)

  def push(
    self,
    obs: np.ndarray,
    action: int,
    reward: float,
    next_obs: np.ndarray,
    done: bool,
    next_mask: np.ndarray,
  ) -> None:
    i = self._pos
    self._obs[i] = obs
    self._actions[i] = action
    self._rewards[i] = reward
    self._next_obs[i] = next_obs
    self._dones[i] = float(done)
    self._next_masks[i] = next_mask
    self._pos = (i + 1) % self._cap
    self._size = min(self._size + 1, self._cap)

  def sample(self, batch_size: int, device: torch.device) -> tuple:
    idx = np.random.randint(0, self._size, size=batch_size)
    return (
      torch.as_tensor(self._obs[idx], device=device),
      torch.as_tensor(self._actions[idx], device=device),
      torch.as_tensor(self._rewards[idx], device=device),
      torch.as_tensor(self._next_obs[idx], device=device),
      torch.as_tensor(self._dones[idx], device=device),
      torch.as_tensor(self._next_masks[idx], device=device),
    )

  def __len__(self) -> int:
    return self._size
