import torch
import numpy as np
import pytest
from oware.agents.ppo.model import PPONetwork
from oware.agents.ppo.buffer import RolloutBuffer
from oware.agents.ppo.agent import PPOAgent
from oware.engine import initial_state, legal_moves


def _net():
    return PPONetwork()


def test_output_shapes():
    net = _net()
    obs = torch.randn(4, 15)
    mask = torch.ones(4, 6)
    lp, val, ent = net(obs, mask)
    assert lp.shape == (4, 6)
    assert val.shape == (4,)
    assert ent.shape == (4,)


def test_masked_logits_never_sampled():
    net = _net()
    obs = torch.randn(1, 15)
    mask = torch.zeros(1, 6)
    mask[0, 2] = 1.0  # only pit 2 legal
    lp, _, _ = net(obs, mask)
    action = int(lp[0].argmax())
    assert action == 2


def test_entropy_zero_single_action():
    net = _net()
    obs = torch.randn(1, 15)
    mask = torch.zeros(1, 6)
    mask[0, 0] = 1.0
    _, _, ent = net(obs, mask)
    assert ent.item() < 0.01


def test_gae_monte_carlo():
    """With γ=1, λ=1, undiscounted 2-step episode: returns equal cumulative reward."""
    buf = RolloutBuffer(n_steps=2, n_envs=1, gamma=1.0, lam=1.0)
    buf.rewards[0, 0] = 0.0
    buf.rewards[1, 0] = 1.0
    buf.values[0, 0] = 0.0
    buf.values[1, 0] = 0.0
    buf.dones[0, 0] = 0.0
    buf.dones[1, 0] = 0.0  # not done yet — bootstrap from last_values
    buf.compute_gae(np.array([0.0]), np.array([1.0]))  # last step is terminal
    # returns[1] = reward[1] + 0 (terminal) = 1.0
    # returns[0] = reward[0] + returns[1] = 1.0
    assert abs(buf.returns[1, 0] - 1.0) < 1e-5
    assert abs(buf.returns[0, 0] - 1.0) < 1e-5


def test_minibatch_sizes():
    buf = RolloutBuffer(n_steps=8, n_envs=4, gamma=0.99, lam=0.95)
    buf.obs[:] = np.random.rand(8, 4, 15).astype(np.float32)
    buf.masks[:] = 1.0
    buf.compute_gae(np.zeros(4), np.zeros(4))
    total = sum(b[0].shape[0] for b in buf.get_minibatches(8, torch.device("cpu")))
    assert total == 32


def test_ppo_agent_returns_legal_move():
    device = torch.device("cpu")
    net = PPONetwork()
    agent = PPOAgent(net, device)
    s = initial_state()
    action, extras = agent.choose_move(s)
    assert action in legal_moves(s)
    assert len(extras["scores"]) == 6
