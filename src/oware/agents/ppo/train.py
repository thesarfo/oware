"""PPO training loop. Usage: python -m oware.agents.ppo.train"""

import dataclasses
import random
import sys
import threading
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from oware.agents.dqn.env import OwareEnv
from oware.agents.minimax import MinimaxAgent
from oware.agents.ppo.buffer import RolloutBuffer
from oware.agents.ppo.model import PPONetwork
from oware.agents.random_agent import RandomAgent
from oware.engine import NORTH, SOUTH, encode, legal_moves, terminal
from oware.training.logging import RunLogger


@dataclasses.dataclass
class Config:
  total_steps: int = 5_000_000
  n_envs: int = 8
  n_steps: int = 256  # steps per env per rollout → 2048 total
  batch_size: int = 256
  n_epochs: int = 4
  lr: float = 3e-4
  gamma: float = 0.99
  lam: float = 0.95
  clip_eps: float = 0.2
  value_coef: float = 0.5
  entropy_coef_start: float = 0.01
  entropy_coef_end: float = 0.001
  max_grad_norm: float = 0.5
  opponent_switch_step: int = 500_000
  eval_every: int = 50_000
  eval_games: int = 100
  seed: int = 42
  artifacts_dir: Path = Path("artifacts/ppo")
  tb_dir: Path = Path("artifacts/tb/ppo")


def _entropy_coef(step: int, cfg: Config) -> float:
  frac = min(step / cfg.total_steps, 1.0)
  return cfg.entropy_coef_start + frac * (cfg.entropy_coef_end - cfg.entropy_coef_start)


def _pick_opponent(step: int, cfg: Config, random_opp, d2, d4):
  if step < cfg.opponent_switch_step:
    return random_opp
  r = random.random()
  if r < 0.34:
    return random_opp
  if r < 0.67:
    return d2
  return d4


def _eval_winrate(net: PPONetwork, opponent, games: int, device: torch.device) -> float:
  wins = 0
  env = OwareEnv()
  net.eval()
  for i in range(games):
    agent_side = SOUTH if i % 2 == 0 else NORTH
    env.reset(seed=i)
    for _ in range(500):
      s = env.state
      done, _ = terminal(s)
      if done:
        break
      if s.to_move == agent_side:
        obs = torch.as_tensor(encode(s), device=device).unsqueeze(0)
        mask = torch.zeros(1, 6, device=device)
        for m in legal_moves(s):
          mask[0, m] = 1.0
        with torch.no_grad():
          log_probs, _, _ = net(obs, mask)
        action = int(log_probs[0].argmax())
      else:
        action, _ = opponent.choose_move(s)
      env.step(action)
    done, winner = terminal(env.state)
    if done and winner == agent_side:
      wins += 1
  net.train()
  return wins / games


class _Worker:
  """Runs one env in a thread, fills a slot in the shared rollout arrays."""

  def __init__(
    self,
    env_id: int,
    cfg: Config,
    net: PPONetwork,
    device: torch.device,
    global_step_ref: list[int],
    random_opp,
    d2,
    d4,
  ) -> None:
    self.env_id = env_id
    self.cfg = cfg
    self.net = net
    self.device = device
    self.global_step_ref = global_step_ref
    self.opps = (random_opp, d2, d4)
    self.env = OwareEnv()
    self.game_count = env_id  # stagger starting sides
    self._reset_game()

  def _reset_game(self):
    self.agent_side = SOUTH if self.game_count % 2 == 0 else NORTH
    self.env.reset(seed=self.game_count)
    self.game_count += 1

  def collect(self, buf: RolloutBuffer, step: int) -> None:
    """Collect one step into buf[:, env_id]."""
    s = self.env.state
    done, _ = terminal(s)
    if done:
      self._reset_game()
      s = self.env.state

    if s.to_move != self.agent_side:
      opp = _pick_opponent(self.global_step_ref[0], self.cfg, *self.opps)
      action, _ = opp.choose_move(s)
      self.env.step(action)
      s = self.env.state
      done, _ = terminal(s)
      if done:
        self._reset_game()
      # Fill a dummy step (opponent turn — no gradient)
      buf.obs[step, self.env_id] = encode(s)
      mask = np.zeros(6, dtype=np.float32)
      for m in legal_moves(s):
        mask[m] = 1.0
      buf.masks[step, self.env_id] = mask
      buf.actions[step, self.env_id] = 0
      buf.rewards[step, self.env_id] = 0.0
      buf.values[step, self.env_id] = 0.0
      buf.log_probs[step, self.env_id] = 0.0
      buf.dones[step, self.env_id] = float(done)
      return

    obs_arr = encode(s)
    mask_arr = np.zeros(6, dtype=np.float32)
    for m in legal_moves(s):
      mask_arr[m] = 1.0

    obs_t = torch.as_tensor(obs_arr, device=self.device).unsqueeze(0)
    mask_t = torch.as_tensor(mask_arr, device=self.device).unsqueeze(0)
    with torch.no_grad():
      log_probs, value, _ = self.net(obs_t, mask_t)
    action = int(torch.multinomial(log_probs.exp(), 1).item())
    log_prob = log_probs[0, action].item()
    val = value.item()

    _, reward, terminated, _, _ = self.env.step(action)

    # Opponent responds
    if not terminated:
      s2 = self.env.state
      done2, _ = terminal(s2)
      if not done2 and s2.to_move != self.agent_side:
        opp = _pick_opponent(self.global_step_ref[0], self.cfg, *self.opps)
        opp_action, _ = opp.choose_move(s2)
        _, _, terminated, _, _ = self.env.step(opp_action)
        if terminated:
          done2, winner = terminal(self.env.state)
          if done2:
            reward = (
              1.0 if winner == self.agent_side else (-1.0 if winner != -1 else 0.0)
            )

    buf.obs[step, self.env_id] = obs_arr
    buf.masks[step, self.env_id] = mask_arr
    buf.actions[step, self.env_id] = action
    buf.rewards[step, self.env_id] = reward
    buf.values[step, self.env_id] = val
    buf.log_probs[step, self.env_id] = log_prob
    buf.dones[step, self.env_id] = float(terminated)

    if terminated:
      self._reset_game()


def train(cfg: Config | None = None) -> None:
  if cfg is None:
    cfg = Config()

  cfg.artifacts_dir.mkdir(parents=True, exist_ok=True)
  run_id = f"{int(time.time())}"
  logger = RunLogger(cfg.tb_dir / run_id)

  torch.manual_seed(cfg.seed)
  np.random.seed(cfg.seed)
  random.seed(cfg.seed)

  device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
  net = PPONetwork().to(device)
  optimizer = torch.optim.Adam(net.parameters(), lr=cfg.lr)

  random_opp = RandomAgent(seed=cfg.seed)
  d2 = MinimaxAgent(max_depth=2)
  d4 = MinimaxAgent(max_depth=4)

  global_step_ref = [0]
  workers = [
    _Worker(i, cfg, net, device, global_step_ref, random_opp, d2, d4)
    for i in range(cfg.n_envs)
  ]

  best_score = 0.0
  global_step = 0
  n_updates = cfg.total_steps // (cfg.n_steps * cfg.n_envs)

  try:
    from tqdm import tqdm

    pbar = tqdm(
      total=cfg.total_steps, desc="ppo", unit="step", disable=not sys.stdout.isatty()
    )
  except ImportError:
    pbar = None

  for _ in range(n_updates):
    buf = RolloutBuffer(cfg.n_steps, cfg.n_envs, cfg.gamma, cfg.lam)

    # Collect rollout across all envs (threaded)
    for step in range(cfg.n_steps):
      threads = [threading.Thread(target=w.collect, args=(buf, step)) for w in workers]
      for t in threads:
        t.start()
      for t in threads:
        t.join()

    global_step += cfg.n_steps * cfg.n_envs
    global_step_ref[0] = global_step
    if pbar:
      pbar.update(cfg.n_steps * cfg.n_envs)

    # Bootstrap last values
    last_obs = np.array([encode(w.env.state) for w in workers], dtype=np.float32)
    last_dones = np.array(
      [float(terminal(w.env.state)[0]) for w in workers], dtype=np.float32
    )
    last_masks = np.zeros((cfg.n_envs, 6), dtype=np.float32)
    for i, w in enumerate(workers):
      for m in legal_moves(w.env.state):
        last_masks[i, m] = 1.0
    with torch.no_grad():
      _, last_vals, _ = net(
        torch.as_tensor(last_obs, device=device),
        torch.as_tensor(last_masks, device=device),
      )
    buf.compute_gae(last_vals.cpu().numpy(), last_dones)

    # PPO update
    ent_coef = _entropy_coef(global_step, cfg)
    for _ in range(cfg.n_epochs):
      for obs_b, mask_b, act_b, old_lp_b, adv_b, ret_b in buf.get_minibatches(
        cfg.batch_size, device
      ):
        new_lp, values, entropy = net(obs_b, mask_b)
        new_lp_a = new_lp.gather(1, act_b.unsqueeze(1)).squeeze(1)
        ratio = (new_lp_a - old_lp_b).exp()
        pg_loss = -torch.min(
          ratio * adv_b,
          ratio.clamp(1 - cfg.clip_eps, 1 + cfg.clip_eps) * adv_b,
        ).mean()
        v_loss = F.mse_loss(values, ret_b)
        loss = pg_loss + cfg.value_coef * v_loss - ent_coef * entropy.mean()
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), cfg.max_grad_norm)
        optimizer.step()

    logger.scalars(
      "train",
      {
        "loss": loss.item(),
        "policy_loss": pg_loss.item(),
        "value_loss": v_loss.item(),
        "entropy": entropy.mean().item(),
        "entropy_coef": ent_coef,
      },
      global_step,
    )

    if global_step % cfg.eval_every == 0:
      wr_d2 = _eval_winrate(net, d2, cfg.eval_games, device)
      wr_d4 = _eval_winrate(net, d4, cfg.eval_games, device)
      logger.scalars(
        "eval",
        {
          "winrate_vs_minimax_d2": wr_d2,
          "winrate_vs_minimax_d4": wr_d4,
        },
        global_step,
      )
      if pbar:
        tqdm.write(f"step {global_step}: vs_d2={wr_d2:.1%} vs_d4={wr_d4:.1%}")
      score = wr_d2 + wr_d4
      if score > best_score:
        best_score = score
        torch.save(
          {
            "model": net.state_dict(),
            "step": global_step,
            "config": {
              k: str(v) if isinstance(v, Path) else v
              for k, v in dataclasses.asdict(cfg).items()
            },
          },
          cfg.artifacts_dir / "latest.pt",
        )

  if pbar:
    pbar.close()
  logger.close()


if __name__ == "__main__":
  train()
