import numpy as np
import torch


class RolloutBuffer:
  def __init__(self, n_steps: int, n_envs: int, gamma: float, lam: float) -> None:
    self.n_steps = n_steps
    self.n_envs = n_envs
    self.gamma = gamma
    self.lam = lam
    n, e = n_steps, n_envs
    self.obs = np.zeros((n, e, 15), dtype=np.float32)
    self.masks = np.zeros((n, e, 6), dtype=np.float32)
    self.actions = np.zeros((n, e), dtype=np.int64)
    self.rewards = np.zeros((n, e), dtype=np.float32)
    self.values = np.zeros((n, e), dtype=np.float32)
    self.log_probs = np.zeros((n, e), dtype=np.float32)
    self.dones = np.zeros((n, e), dtype=np.float32)
    self.advantages = np.zeros((n, e), dtype=np.float32)
    self.returns = np.zeros((n, e), dtype=np.float32)
    self.ptr = 0

  def push(
    self, step: int, obs, masks, actions, rewards, values, log_probs, dones
  ) -> None:
    self.obs[step] = obs
    self.masks[step] = masks
    self.actions[step] = actions
    self.rewards[step] = rewards
    self.values[step] = values
    self.log_probs[step] = log_probs
    self.dones[step] = dones

  def compute_gae(self, last_values: np.ndarray, last_dones: np.ndarray) -> None:
    gae = np.zeros(self.n_envs, dtype=np.float32)
    for t in reversed(range(self.n_steps)):
      next_val = last_values if t == self.n_steps - 1 else self.values[t + 1]
      next_done = last_dones if t == self.n_steps - 1 else self.dones[t + 1]
      delta = self.rewards[t] + self.gamma * next_val * (1 - next_done) - self.values[t]
      gae = delta + self.gamma * self.lam * (1 - next_done) * gae
      self.advantages[t] = gae
    self.returns = self.advantages + self.values

  def get_minibatches(self, batch_size: int, device: torch.device):
    n = self.n_steps * self.n_envs
    obs = torch.as_tensor(self.obs.reshape(n, 15), device=device)
    masks = torch.as_tensor(self.masks.reshape(n, 6), device=device)
    actions = torch.as_tensor(self.actions.reshape(n), device=device)
    log_probs = torch.as_tensor(self.log_probs.reshape(n), device=device)
    advantages = torch.as_tensor(self.advantages.reshape(n), device=device)
    returns = torch.as_tensor(self.returns.reshape(n), device=device)

    advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

    idx = torch.randperm(n, device=device)
    for start in range(0, n, batch_size):
      b = idx[start : start + batch_size]
      yield obs[b], masks[b], actions[b], log_probs[b], advantages[b], returns[b]
