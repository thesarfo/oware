import numpy as np
import pytest
import torch

from oware.agents.az.agent import AZAgent
from oware.agents.az.buffer import SelfPlayBuffer
from oware.agents.az.mcts import search
from oware.agents.az.model import AZNetwork
from oware.engine import initial_state, legal_moves


def _net():
  net = AZNetwork()
  net.eval()
  return net


def test_model_output_shapes():
  net = _net()
  obs = torch.randn(4, 15)
  mask = torch.ones(4, 6)
  lp, val = net(obs, mask)
  assert lp.shape == (4, 6)
  assert val.shape == (4,)
  assert (val.abs() <= 1.0).all()


def test_model_param_count():
  net = _net()
  n = sum(p.numel() for p in net.parameters())
  assert 50_000 < n < 300_000


def test_model_masked_action_excluded():
  net = _net()
  obs = torch.randn(1, 15)
  mask = torch.zeros(1, 6)
  mask[0, 3] = 1.0
  lp, _ = net(obs, mask)
  assert int(lp[0].argmax()) == 3


def test_mcts_pi_sums_to_one():
  net = _net()
  device = torch.device("cpu")
  s = initial_state()
  pi = search(s, net, device, n_sims=10, add_noise=False)
  assert abs(pi.sum() - 1.0) < 1e-5


def test_mcts_only_legal_actions():
  net = _net()
  device = torch.device("cpu")
  s = initial_state()
  pi = search(s, net, device, n_sims=10, add_noise=False)
  legal = set(legal_moves(s))
  for i in range(6):
    if i not in legal:
      assert pi[i] == 0.0


def test_buffer_capacity_wrap():
  buf = SelfPlayBuffer(capacity=10)
  obs = np.zeros((6, 15), dtype=np.float32)
  pi = np.ones((6, 6), dtype=np.float32) / 6
  z = np.zeros(6, dtype=np.float32)
  buf.push_game(obs, pi, z)
  buf.push_game(obs, pi, z)
  assert len(buf) == 10


def test_buffer_sample_shapes():
  buf = SelfPlayBuffer(capacity=100)
  obs = np.zeros((20, 15), dtype=np.float32)
  pi = np.ones((20, 6), dtype=np.float32) / 6
  z = np.zeros(20, dtype=np.float32)
  buf.push_game(obs, pi, z)
  o, p, zz = buf.sample(8)
  assert o.shape == (8, 15)
  assert p.shape == (8, 6)
  assert zz.shape == (8,)


def test_az_agent_returns_legal_move():
  net = _net()
  agent = AZAgent(net, torch.device("cpu"), n_sims=5)
  s = initial_state()
  action, extras = agent.choose_move(s)
  assert action in legal_moves(s)
  assert sum(v for v in extras["scores"] if v is not None) == pytest.approx(
    1.0, abs=1e-4
  )
