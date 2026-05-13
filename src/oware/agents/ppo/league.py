"""League play for PPO: a bounded FIFO pool of frozen policy snapshots."""

from __future__ import annotations

import copy
import random

from oware.agents.ppo.model import PPONetwork


class OpponentPool:
  """A circular buffer of frozen PPONetwork snapshots used as league opponents."""

  def __init__(self, capacity: int = 10) -> None:
    self._capacity = capacity
    self._snapshots: list[PPONetwork] = []

  def add(self, net: PPONetwork) -> None:
    snap = copy.deepcopy(net)
    snap.eval()
    for p in snap.parameters():
      p.requires_grad_(False)
    self._snapshots.append(snap)
    if len(self._snapshots) > self._capacity:
      self._snapshots.pop(0)

  def latest(self) -> PPONetwork | None:
    return self._snapshots[-1] if self._snapshots else None

  def sample(self) -> PPONetwork | None:
    return random.choice(self._snapshots) if self._snapshots else None

  def __len__(self) -> int:
    return len(self._snapshots)
