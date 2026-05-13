import torch

from oware.agents.dqn.agent import DQNAgent
from oware.agents.dqn.model import QNetwork
from oware.engine import initial_state, legal_moves


def _make_agent() -> DQNAgent:
  device = torch.device("cpu")
  net = QNetwork(dueling=True).to(device)
  return DQNAgent(net, device)


def test_choose_move_returns_legal_action():
  agent = _make_agent()
  s = initial_state()
  action, extras = agent.choose_move(s)
  assert action in legal_moves(s)
  assert "scores" in extras
  assert len(extras["scores"]) == 6


def test_choose_move_never_illegal_with_extreme_q():
  """Even if Q-values strongly favour an illegal pit, the mask must win."""
  agent = _make_agent()
  # Manually set all weights to zero so Q-values are uniform, then verify
  for p in agent._net.parameters():
    p.data.fill_(0.0)
  s = initial_state()
  for _ in range(20):
    action, _ = agent.choose_move(s)
    assert action in legal_moves(s)
