from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch

from oware.agents.base import AgentInfo
from oware.agents.dqn.model import QNetwork
from oware.engine import State, encode, legal_moves


class DQNAgent:
  info = AgentInfo(
    id="dqn",
    name="DQN",
    family="dqn",
    description="Deep Q-Network trained via self-play against Random and Minimax-d2.",
    est_elo=None,
  )

  def __init__(self, net: QNetwork, device: torch.device) -> None:
    self._net = net
    self._device = device

  @classmethod
  def load(cls, path: Path) -> "DQNAgent":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(path, map_location=device, weights_only=False)
    cfg = ckpt.get("config", {})
    net = QNetwork(dueling=cfg.get("dueling", True)).to(device)
    net.load_state_dict(ckpt["model"])
    net.eval()
    return cls(net, device)

  def choose_move(
    self,
    state: State,
    *,
    time_budget_ms: int | None = None,
  ) -> tuple[int, dict[str, Any]]:
    obs = encode(state)
    mask = np.zeros(6, dtype=np.float32)
    for m in legal_moves(state):
      mask[m] = 1.0
    with torch.no_grad():
      q = self._net(torch.as_tensor(obs, device=self._device).unsqueeze(0))[0]
    q = q.cpu().numpy()
    q[mask == 0] = -float("inf")
    action = int(np.argmax(q))
    scores = [float(q[i]) if mask[i] else None for i in range(6)]
    return action, {"scores": scores}
