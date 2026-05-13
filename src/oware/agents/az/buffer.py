import threading

import numpy as np


class SelfPlayBuffer:
  def __init__(self, capacity: int = 500_000) -> None:
    self._cap = capacity
    self._obs = np.zeros((capacity, 15), dtype=np.float32)
    self._pi = np.zeros((capacity, 6), dtype=np.float32)
    self._z = np.zeros(capacity, dtype=np.float32)
    self._pos = 0
    self._size = 0
    self._lock = threading.Lock()

  def push_game(self, obs: np.ndarray, pi: np.ndarray, z: np.ndarray) -> None:
    with self._lock:
      n = len(obs)
      for i in range(n):
        p = self._pos
        self._obs[p] = obs[i]
        self._pi[p] = pi[i]
        self._z[p] = z[i]
        self._pos = (p + 1) % self._cap
      self._size = min(self._size + n, self._cap)

  def sample(self, batch_size: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with self._lock:
      idx = np.random.randint(0, self._size, size=batch_size)
      return self._obs[idx].copy(), self._pi[idx].copy(), self._z[idx].copy()

  def __len__(self) -> int:
    with self._lock:
      return self._size
