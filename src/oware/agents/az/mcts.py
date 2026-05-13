from __future__ import annotations

import math
import queue
import threading
from typing import NamedTuple

import numpy as np
import torch

from oware.agents.az.model import AZNetwork
from oware.engine import State, encode, legal_moves, step, terminal

C_PUCT = 1.5


class _EvalRequest(NamedTuple):
  obs: np.ndarray      # shape (15,)
  mask: np.ndarray     # shape (6,)
  future: threading.Event
  result: list         # [log_probs np (6,), value float] filled by server


class InferenceServer:
  """Batches eval requests from self-play workers and runs one GPU forward pass per batch."""

  def __init__(self, net: AZNetwork, device: torch.device, max_batch: int = 64, timeout: float = 0.005) -> None:
    self._net = net
    self._device = device
    self._max_batch = max_batch
    self._timeout = timeout
    self._q: queue.Queue[_EvalRequest | None] = queue.Queue()
    self._thread = threading.Thread(target=self._run, daemon=True)
    self._thread.start()

  def eval(self, obs: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, float]:
    """Submit one position for evaluation; blocks until result is ready."""
    req = _EvalRequest(obs, mask, threading.Event(), [])
    self._q.put(req)
    req.future.wait()
    return req.result[0], req.result[1]

  def update_net(self, net: AZNetwork) -> None:
    self._net = net

  def stop(self) -> None:
    self._q.put(None)

  def _run(self) -> None:
    while True:
      # Block until at least one request arrives
      try:
        first = self._q.get(timeout=1.0)
      except queue.Empty:
        continue
      if first is None:
        return

      batch = [first]
      # Drain up to max_batch with a short timeout
      deadline = self._timeout
      while len(batch) < self._max_batch:
        try:
          req = self._q.get(timeout=deadline)
          if req is None:
            # Drain remaining batch then exit
            self._dispatch(batch)
            return
          batch.append(req)
          deadline = 0.0  # don't wait further once we have items
        except queue.Empty:
          break

      self._dispatch(batch)

  def _dispatch(self, batch: list[_EvalRequest]) -> None:
    obs_arr = np.stack([r.obs for r in batch])
    mask_arr = np.stack([r.mask for r in batch])
    obs_t = torch.as_tensor(obs_arr, device=self._device)
    mask_t = torch.as_tensor(mask_arr, device=self._device)
    with torch.no_grad():
      log_probs_t, values_t = self._net(obs_t, mask_t)
    log_probs_np = log_probs_t.cpu().numpy()
    values_np = values_t.cpu().numpy()
    for i, req in enumerate(batch):
      req.result.append(log_probs_np[i])
      req.result.append(float(values_np[i]))
      req.future.set()


class _Node:
  __slots__ = ("state", "prior", "children", "N", "W", "parent", "action")

  def __init__(
    self, state: State, prior: float, parent: "_Node | None", action: int | None
  ) -> None:
    self.state = state
    self.prior = prior
    self.parent = parent
    self.action = action
    self.children: dict[int, "_Node"] = {}
    self.N = 0
    self.W = 0.0

  @property
  def Q(self) -> float:
    return self.W / self.N if self.N > 0 else 0.0

  def is_leaf(self) -> bool:
    return len(self.children) == 0


def _net_eval(node: _Node, net: AZNetwork, device: torch.device) -> float:
  done, winner = terminal(node.state)
  if done:
    side = node.state.to_move
    if winner == side:
      return 1.0
    if winner == -1:
      return 0.0
    return -1.0

  obs = torch.as_tensor(encode(node.state), device=device).unsqueeze(0)
  moves = legal_moves(node.state)
  mask = torch.zeros(1, 6, device=device)
  for m in moves:
    mask[0, m] = 1.0
  with torch.no_grad():
    log_probs, value = net(obs, mask)
  probs = log_probs.exp()[0].cpu().numpy()
  for m in moves:
    node.children[m] = _Node(step(node.state, m)[0], float(probs[m]), node, m)
  return float(value.item())


def _server_eval(node: _Node, server: InferenceServer) -> float:
  """Like _net_eval but uses the inference server for batched GPU calls."""
  done, winner = terminal(node.state)
  if done:
    side = node.state.to_move
    if winner == side:
      return 1.0
    if winner == -1:
      return 0.0
    return -1.0

  moves = legal_moves(node.state)
  obs = encode(node.state).astype(np.float32)
  mask = np.zeros(6, dtype=np.float32)
  for m in moves:
    mask[m] = 1.0

  log_probs, value = server.eval(obs, mask)
  probs = np.exp(log_probs)
  for m in moves:
    node.children[m] = _Node(step(node.state, m)[0], float(probs[m]), node, m)
  return value


def _select(node: _Node) -> _Node:
  while not node.is_leaf():
    total_n = sum(c.N for c in node.children.values())
    best_score = -float("inf")
    best_child = None
    for child in node.children.values():
      score = child.Q + C_PUCT * child.prior * math.sqrt(total_n) / (1 + child.N)
      if score > best_score:
        best_score = score
        best_child = child
    node = best_child  # type: ignore[assignment]
  return node


def _backprop(node: _Node, value: float) -> None:
  while node is not None:
    node.N += 1
    node.W += value
    value = -value
    node = node.parent  # type: ignore[assignment]


def search(
  root_state: State,
  net: AZNetwork,
  device: torch.device,
  n_sims: int,
  add_noise: bool = False,
) -> np.ndarray:
  root = _Node(root_state, 1.0, None, None)
  _net_eval(root, net, device)

  if add_noise and root.children:
    moves = list(root.children.keys())
    noise = np.random.dirichlet([0.5] * len(moves))
    for i, m in enumerate(moves):
      c = root.children[m]
      c.prior = 0.75 * c.prior + 0.25 * noise[i]

  for _ in range(n_sims):
    leaf = _select(root)
    value = _net_eval(leaf, net, device)
    _backprop(leaf, value)

  pi = np.zeros(6, dtype=np.float32)
  for m, child in root.children.items():
    pi[m] = child.N
  if pi.sum() > 0:
    pi /= pi.sum()
  return pi


def search_with_server(
  root_state: State,
  server: InferenceServer,
  n_sims: int,
  add_noise: bool = False,
) -> np.ndarray:
  """Like search() but uses InferenceServer for batched GPU eval."""
  root = _Node(root_state, 1.0, None, None)
  _server_eval(root, server)

  if add_noise and root.children:
    moves = list(root.children.keys())
    noise = np.random.dirichlet([0.5] * len(moves))
    for i, m in enumerate(moves):
      c = root.children[m]
      c.prior = 0.75 * c.prior + 0.25 * noise[i]

  for _ in range(n_sims):
    leaf = _select(root)
    value = _server_eval(leaf, server)
    _backprop(leaf, value)

  pi = np.zeros(6, dtype=np.float32)
  for m, child in root.children.items():
    pi[m] = child.N
  if pi.sum() > 0:
    pi /= pi.sum()
  return pi
