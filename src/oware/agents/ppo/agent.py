from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch

from oware.agents.base import AgentInfo
from oware.agents.ppo.model import PPONetwork
from oware.engine import State, encode, legal_moves


class PPOAgent:
  info = AgentInfo(
    id="ppo",
    name="PPO",
    family="ppo",
    description="Proximal Policy Optimisation trained via self-play against Random and Minimax.",
    est_elo=None,
  )

  def __init__(self, net: PPONetwork, device: torch.device) -> None:
    self._net = net
    self._device = device

  @classmethod
  def load(cls, path: Path) -> "PPOAgent":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(path, map_location=device, weights_only=False)
    net = PPONetwork().to(device)
    net.load_state_dict(ckpt["model"])
    net.eval()
    return cls(net, device)

  def choose_move(
    self,
    state: State,
    *,
    time_budget_ms: int | None = None,
  ) -> tuple[int, dict[str, Any]]:
    obs = torch.as_tensor(encode(state), device=self._device).unsqueeze(0)
    mask = torch.zeros(1, 6, device=self._device)
    for m in legal_moves(state):
      mask[0, m] = 1.0
    with torch.no_grad():
      log_probs, _, _ = self._net(obs, mask)
    lp = log_probs[0].cpu().numpy()
    action = int(np.argmax(lp))
    scores = [float(lp[i]) if mask[0, i].item() else None for i in range(6)]
    return action, {"scores": scores}
