from __future__ import annotations

import math

import numpy as np
import torch

from oware.agents.az.model import AZNetwork
from oware.engine import State, encode, legal_moves, step, terminal

C_PUCT = 1.5


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
