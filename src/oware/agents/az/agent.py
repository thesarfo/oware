from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch

from oware.agents.az.mcts import search
from oware.agents.az.model import AZNetwork
from oware.agents.base import AgentInfo
from oware.engine import State


class AZAgent:
  info = AgentInfo(
    id="az",
    name="AlphaZero",
    family="az",
    description="MCTS with a policy-value ResNet, trained via self-play.",
    est_elo=None,
  )

  def __init__(self, net: AZNetwork, device: torch.device, n_sims: int = 100) -> None:
    self._net = net
    self._device = device
    self._n_sims = n_sims

  @classmethod
  def load(cls, path: Path, n_sims: int = 100) -> "AZAgent":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(path, map_location=device, weights_only=False)
    net = AZNetwork().to(device)
    net.load_state_dict(ckpt["model"])
    net.eval()
    return cls(net, device, n_sims)

  def choose_move(
    self,
    state: State,
    *,
    time_budget_ms: int | None = None,
  ) -> tuple[int, dict[str, Any]]:
    pi = search(state, self._net, self._device, self._n_sims, add_noise=False)
    action = int(np.argmax(pi))
    scores = [float(pi[i]) if pi[i] > 0 else None for i in range(6)]
    return action, {"scores": scores, "sims": self._n_sims}
