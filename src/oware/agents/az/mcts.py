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
VIRTUAL_LOSS = 3  # penalty applied during traversal to steer workers to different leaves


class _EvalRequest(NamedTuple):
  obs: np.ndarray      # shape (15,)
  mask: np.ndarray     # shape (6,)
  future: threading.Event
  result: list         # [log_probs np (6,), value float] filled by server


class InferenceServer:
  """Batches eval requests from self-play workers and runs one GPU forward pass per batch."""

  def __init__(self, net: AZNetwork, device: torch.device, max_batch: int = 256) -> None:
    self._net = net
    self._device = device
    self._max_batch = max_batch
    self._q: queue.Queue[_EvalRequest | None] = queue.Queue()
    self._thread = threading.Thread(target=self._run, daemon=True)
    self._thread.start()

  def eval(self, obs: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, float]:
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
      try:
        first = self._q.get(timeout=1.0)
      except queue.Empty:
        continue
      if first is None:
        return
      batch = [first]
      # Drain everything currently in the queue up to max_batch (no extra waiting)
      while len(batch) < self._max_batch:
        try:
          req = self._q.get_nowait()
          if req is None:
            self._dispatch(batch)
            return
          batch.append(req)
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
  __slots__ = ("state", "prior", "children", "N", "W", "parent", "action", "_lock")

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
    self._lock = threading.Lock()

  @property
  def Q(self) -> float:
    return self.W / self.N if self.N > 0 else 0.0

  def is_leaf(self) -> bool:
    return len(self.children) == 0


def _net_eval(node: _Node, net: AZNetwork, device: torch.device) -> float:
  """Single-threaded eval used by the standalone search() function."""
  done, winner = terminal(node.state)
  if done:
    side = node.state.to_move
    return 1.0 if winner == side else (0.0 if winner == -1 else -1.0)

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
  """Eval via inference server; expands node if it's still a leaf after the call."""
  done, winner = terminal(node.state)
  if done:
    side = node.state.to_move
    return 1.0 if winner == side else (0.0 if winner == -1 else -1.0)

  moves = legal_moves(node.state)
  obs = encode(node.state).astype(np.float32)
  mask = np.zeros(6, dtype=np.float32)
  for m in moves:
    mask[m] = 1.0

  log_probs, value = server.eval(obs, mask)  # blocks until GPU batch fires
  probs = np.exp(log_probs)
  with node._lock:
    if node.is_leaf():  # another worker may have expanded already
      for m in moves:
        node.children[m] = _Node(step(node.state, m)[0], float(probs[m]), node, m)
  return value


def _select_with_virtual_loss(root: _Node) -> tuple[_Node, list[_Node]]:
  """Select a leaf, applying virtual loss along the path to deter concurrent workers."""
  path: list[_Node] = []
  node = root
  while not node.is_leaf():
    with node._lock:
      total_n = sum(c.N for c in node.children.values())
      best_score = -float("inf")
      best_child = None
      for child in node.children.values():
        score = child.Q + C_PUCT * child.prior * math.sqrt(total_n + 1) / (1 + child.N)
        if score > best_score:
          best_score = score
          best_child = child
      best_child.N += VIRTUAL_LOSS
      best_child.W -= VIRTUAL_LOSS
    path.append(best_child)
    node = best_child
  return node, path


def _backprop_with_virtual_loss(path: list[_Node], leaf: _Node, value: float) -> None:
  """Undo virtual loss and apply real value."""
  with leaf._lock:
    leaf.N += 1
    leaf.W += value
  value = -value
  for node in reversed(path):
    with node._lock:
      node.N -= VIRTUAL_LOSS - 1  # undo VL, add real visit
      node.W += VIRTUAL_LOSS + value
    value = -value


def _select(node: _Node) -> _Node:
  """Single-threaded selection used by standalone search()."""
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
  """Single-threaded MCTS (used by agent.py for inference)."""
  root = _Node(root_state, 1.0, None, None)
  _net_eval(root, net, device)

  if add_noise and root.children:
    moves = list(root.children.keys())
    noise = np.random.dirichlet([0.5] * len(moves))
    for i, m in enumerate(moves):
      root.children[m].prior = 0.75 * root.children[m].prior + 0.25 * noise[i]

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
  parallel_leaves: int = 8,
) -> np.ndarray:
  """MCTS with virtual loss: selects parallel_leaves simultaneously per round,
  submitting them all to the inference server so they fire as one GPU batch."""
  root = _Node(root_state, 1.0, None, None)
  _server_eval(root, server)

  if add_noise and root.children:
    moves = list(root.children.keys())
    noise = np.random.dirichlet([0.5] * len(moves))
    for i, m in enumerate(moves):
      root.children[m].prior = 0.75 * root.children[m].prior + 0.25 * noise[i]

  sims_done = 0
  while sims_done < n_sims:
    batch_size = min(parallel_leaves, n_sims - sims_done)
    results: list[tuple[_Node, list[_Node], float] | None] = [None] * batch_size

    def _work(idx: int) -> None:
      leaf, path = _select_with_virtual_loss(root)
      value = _server_eval(leaf, server)  # all batch_size workers block here together
      results[idx] = (leaf, path, value)

    threads = [threading.Thread(target=_work, args=(i,)) for i in range(batch_size)]
    for t in threads:
      t.start()
    for t in threads:
      t.join()

    for item in results:
      leaf, path, value = item  # type: ignore[misc]
      _backprop_with_virtual_loss(path, leaf, value)
    sims_done += batch_size

  pi = np.zeros(6, dtype=np.float32)
  for m, child in root.children.items():
    pi[m] = child.N
  if pi.sum() > 0:
    pi /= pi.sum()
  return pi
