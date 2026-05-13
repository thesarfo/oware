import numpy as np
import torch

from oware.agents.dqn.buffer import ReplayBuffer
from oware.agents.dqn.model import QNetwork


def test_qnetwork_output_shape_dueling():
  net = QNetwork(dueling=True)
  x = torch.randn(8, 15)
  assert net(x).shape == (8, 6)


def test_qnetwork_output_shape_standard():
  net = QNetwork(dueling=False)
  x = torch.randn(8, 15)
  assert net(x).shape == (8, 6)


def test_replay_buffer_wraps_at_capacity():
  buf = ReplayBuffer(capacity=10)
  obs = np.zeros(15, dtype=np.float32)
  mask = np.ones(6, dtype=np.float32)
  for i in range(15):
    buf.push(obs, i % 6, 0.0, obs, False, mask)
  assert len(buf) == 10


def test_replay_buffer_sample_shapes():
  buf = ReplayBuffer(capacity=100)
  obs = np.random.rand(15).astype(np.float32)
  mask = np.ones(6, dtype=np.float32)
  for _ in range(50):
    buf.push(obs, 0, 1.0, obs, False, mask)
  device = torch.device("cpu")
  b_obs, b_act, b_rew, b_next, b_done, b_nmask = buf.sample(16, device)
  assert b_obs.shape == (16, 15)
  assert b_act.shape == (16,)
  assert b_rew.shape == (16,)
  assert b_next.shape == (16, 15)
  assert b_done.shape == (16,)
  assert b_nmask.shape == (16, 6)
