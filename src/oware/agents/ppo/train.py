"""PPO training loop. Usage: python -m oware.agents.ppo.train"""

import dataclasses
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from tqdm import tqdm

from oware.agents.dqn.env import OwareEnv
from oware.agents.minimax import MinimaxAgent
from oware.agents.ppo.buffer import RolloutBuffer
from oware.agents.ppo.league import OpponentPool
from oware.agents.ppo.model import PPONetwork
from oware.agents.random_agent import RandomAgent
from oware.engine import NORTH, SOUTH, encode, legal_moves, terminal
from oware.training.logging import RunLogger


@dataclasses.dataclass
class Config:
  total_steps: int = 5_000_000
  n_envs: int = 8
  n_steps: int = 256          # agent transitions per env per rollout
  batch_size: int = 256
  n_epochs: int = 4
  lr: float = 3e-4
  gamma: float = 0.99
  lam: float = 0.95
  clip_eps: float = 0.2
  value_coef: float = 0.5
  entropy_coef_start: float = 0.05   # higher than the old 0.01: cf. CLEAN_CODE §IX.37
  entropy_coef_end: float = 0.005
  entropy_floor: float = 0.3
  entropy_boost_mult: float = 1.1
  entropy_boost_cap: float = 10.0
  max_grad_norm: float = 0.5
  warmup_random_steps: int = 200_000  # opponent = Random until this step
  snapshot_every_rollouts: int = 5
  pool_capacity: int = 10
  pool_latest_p: float = 0.6
  pool_random_p: float = 0.3          # remainder (0.1) is Minimax-d4
  eval_every: int = 50_000
  eval_games: int = 100
  seed: int = 42
  artifacts_dir: Path = Path("artifacts/ppo")
  tb_dir: Path = Path("artifacts/tb/ppo")


def _entropy_coef(step: int, cfg: Config) -> float:
  frac = min(step / cfg.total_steps, 1.0)
  return cfg.entropy_coef_start + frac * (cfg.entropy_coef_end - cfg.entropy_coef_start)


def _legal_mask(s) -> np.ndarray:
  m = np.zeros(6, dtype=np.float32)
  for a in legal_moves(s):
    m[a] = 1.0
  return m


def _snapshot_action(net: PPONetwork, s, device: torch.device) -> int:
  obs = torch.as_tensor(encode(s), device=device).unsqueeze(0)
  mask = torch.as_tensor(_legal_mask(s), device=device).unsqueeze(0)
  with torch.no_grad():
    log_probs, _, _ = net(obs, mask)
  return int(log_probs[0].argmax().item())


def _opponent_action(opp: Any, s, device: torch.device) -> int:
  if isinstance(opp, PPONetwork):
    return _snapshot_action(opp, s, device)
  action, _ = opp.choose_move(s)
  return action


def _pick_opponent(
  global_step: int, cfg: Config, pool: OpponentPool, random_opp, d4
) -> Any:
  """Returns an opponent: PPONetwork, MinimaxAgent, or RandomAgent."""
  if global_step < cfg.warmup_random_steps or len(pool) == 0:
    return random_opp
  r = random.random()
  if r < cfg.pool_latest_p:
    return pool.latest()
  if r < cfg.pool_latest_p + cfg.pool_random_p:
    return pool.sample()
  return d4


class _EnvWorker:
  """Per-env state container. Drives one environment forward to the agent's next decision point."""

  def __init__(self, env_id: int, seed_offset: int) -> None:
    self.env_id = env_id
    self.env = OwareEnv()
    self.game_count = env_id
    self.seed_offset = seed_offset
    self.agent_side = SOUTH
    self.opponent: Any = None

  def reset_game(self, cfg: Config, pool: OpponentPool, random_opp, d4, global_step: int) -> None:
    self.agent_side = SOUTH if self.game_count % 2 == 0 else NORTH
    self.env.reset(seed=self.game_count + self.seed_offset)
    self.opponent = _pick_opponent(global_step, cfg, pool, random_opp, d4)
    self.game_count += 1

  def advance_to_agent_turn(self, device: torch.device, max_steps: int = 200) -> bool:
    """Play opponent moves until it's the agent's turn or game ends.
    Returns True if the agent has a decision to make, False if game ended first."""
    for _ in range(max_steps):
      s = self.env.state
      done, _ = terminal(s)
      if done:
        return False
      if s.to_move == self.agent_side:
        return True
      action = _opponent_action(self.opponent, s, device)
      self.env.step(action)
    return False


def _eval_winrate(net: PPONetwork, opponent, games: int, device: torch.device) -> float:
  wins = 0
  env = OwareEnv()
  net.eval()
  for i in range(games):
    agent_side = SOUTH if i % 2 == 0 else NORTH
    env.reset(seed=i)
    while True:
      s = env.state
      done, _ = terminal(s)
      if done:
        break
      if s.to_move == agent_side:
        obs = torch.as_tensor(encode(s), device=device).unsqueeze(0)
        mask = torch.as_tensor(_legal_mask(s), device=device).unsqueeze(0)
        with torch.no_grad():
          log_probs, _, _ = net(obs, mask)
        action = int(log_probs[0].argmax().item())
      else:
        action = _opponent_action(opponent, s, device)
      env.step(action)
    _, winner = terminal(env.state)
    if winner == agent_side:
      wins += 1
  net.train()
  return wins / games


def _save_ckpt(net: PPONetwork, path: Path, step_n: int, cfg: Config) -> None:
  torch.save(
    {
      "model": net.state_dict(),
      "step": step_n,
      "config": {
        k: str(v) if isinstance(v, Path) else v
        for k, v in dataclasses.asdict(cfg).items()
      },
    },
    path,
  )


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
  print(f"[ppo] device={device}")
  print(f"[ppo] config={dataclasses.asdict(cfg)}")
  logger.text("meta/config", str(dataclasses.asdict(cfg)), 0)

  net = PPONetwork().to(device)
  optimizer = torch.optim.Adam(net.parameters(), lr=cfg.lr)

  random_opp = RandomAgent(seed=cfg.seed)
  d4 = MinimaxAgent(max_depth=4)
  pool = OpponentPool(capacity=cfg.pool_capacity)

  workers = [_EnvWorker(i, seed_offset=cfg.seed * 1000) for i in range(cfg.n_envs)]
  for w in workers:
    w.reset_game(cfg, pool, random_opp, d4, global_step=0)

  _save_ckpt(net, cfg.artifacts_dir / "latest.pt", 0, cfg)
  _save_ckpt(net, cfg.artifacts_dir / "best.pt", 0, cfg)

  best_score = -float("inf")
  global_step = 0
  rollout_n = 0
  entropy_ema = 1.0
  ent_adapt_mult = 1.0
  n_updates = cfg.total_steps // (cfg.n_steps * cfg.n_envs)

  pbar = tqdm(
    total=cfg.total_steps,
    desc=f"ppo [{device}]",
    unit="step",
    disable=not sys.stdout.isatty(),
  )

  for _ in range(n_updates):
    rollout_n += 1
    buf = RolloutBuffer(cfg.n_steps, cfg.n_envs, cfg.gamma, cfg.lam)
    net.eval()

    for step_idx in range(cfg.n_steps):
      # Phase 1: advance each env to its next agent-decision point.
      ready: list[int] = []
      obs_batch = np.zeros((cfg.n_envs, 15), dtype=np.float32)
      mask_batch = np.zeros((cfg.n_envs, 6), dtype=np.float32)
      for i, w in enumerate(workers):
        # Game-end at entry → reset and pick a new opponent.
        done, _ = terminal(w.env.state)
        if done:
          w.reset_game(cfg, pool, random_opp, d4, global_step)
        ok = w.advance_to_agent_turn(device)
        if not ok:
          # Game ended during opponent moves before agent decided this step.
          w.reset_game(cfg, pool, random_opp, d4, global_step)
          ok = w.advance_to_agent_turn(device)
          if not ok:
            continue
        obs_batch[i] = encode(w.env.state)
        mask_batch[i] = _legal_mask(w.env.state)
        ready.append(i)

      # Phase 2: one batched forward across all ready envs.
      obs_t = torch.as_tensor(obs_batch[ready], device=device)
      mask_t = torch.as_tensor(mask_batch[ready], device=device)
      with torch.no_grad():
        log_probs_t, values_t, _ = net(obs_t, mask_t)
      probs_t = log_probs_t.exp()
      sampled = torch.multinomial(probs_t, 1).squeeze(-1).cpu().numpy()
      log_probs_np = log_probs_t.cpu().numpy()
      values_np = values_t.cpu().numpy()

      # Phase 3: apply agent action, play opponent response if any, push.
      for slot, env_i in enumerate(ready):
        w = workers[env_i]
        action = int(sampled[slot])
        log_prob = float(log_probs_np[slot, action])
        value = float(values_np[slot])

        _, reward, terminated, _, _ = w.env.step(action)

        # Opponent's response (single move). If it ends the game, rewrite reward
        # from the agent's perspective.
        if not terminated:
          s2 = w.env.state
          done2, _ = terminal(s2)
          if not done2 and s2.to_move != w.agent_side:
            opp_action = _opponent_action(w.opponent, s2, device)
            _, _, terminated, _, _ = w.env.step(opp_action)
            if terminated:
              _, winner = terminal(w.env.state)
              if winner == w.agent_side:
                reward = 1.0
              elif winner == -1:
                reward = 0.0
              else:
                reward = -1.0

        buf.obs[step_idx, env_i] = obs_batch[env_i]
        buf.masks[step_idx, env_i] = mask_batch[env_i]
        buf.actions[step_idx, env_i] = action
        buf.rewards[step_idx, env_i] = reward
        buf.values[step_idx, env_i] = value
        buf.log_probs[step_idx, env_i] = log_prob
        buf.dones[step_idx, env_i] = float(terminated)

    global_step += cfg.n_steps * cfg.n_envs
    pbar.update(cfg.n_steps * cfg.n_envs)

    # Bootstrap last values.
    last_obs = np.stack([encode(w.env.state) for w in workers]).astype(np.float32)
    last_masks = np.stack([_legal_mask(w.env.state) for w in workers]).astype(np.float32)
    last_dones = np.array(
      [float(terminal(w.env.state)[0]) for w in workers], dtype=np.float32
    )
    with torch.no_grad():
      _, last_vals_t, _ = net(
        torch.as_tensor(last_obs, device=device),
        torch.as_tensor(last_masks, device=device),
      )
    buf.compute_gae(last_vals_t.cpu().numpy(), last_dones)

    # PPO update with adaptive entropy.
    ent_coef = _entropy_coef(global_step, cfg) * ent_adapt_mult
    net.train()
    pg_losses: list[float] = []
    v_losses: list[float] = []
    ents: list[float] = []
    clip_fracs: list[float] = []
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
        pg_losses.append(pg_loss.item())
        v_losses.append(v_loss.item())
        ents.append(entropy.mean().item())
        clip_fracs.append(
          ((ratio - 1.0).abs() > cfg.clip_eps).float().mean().item()
        )

    mean_ent = sum(ents) / len(ents)
    entropy_ema = 0.95 * entropy_ema + 0.05 * mean_ent
    if entropy_ema < cfg.entropy_floor:
      ent_adapt_mult = min(ent_adapt_mult * cfg.entropy_boost_mult, cfg.entropy_boost_cap)
    elif entropy_ema > 1.5 * cfg.entropy_floor:
      ent_adapt_mult = max(ent_adapt_mult * 0.95, 1.0)

    logger.scalars(
      "train",
      {
        "policy_loss": sum(pg_losses) / len(pg_losses),
        "value_loss": sum(v_losses) / len(v_losses),
        "entropy": mean_ent,
        "entropy_ema": entropy_ema,
        "entropy_coef": ent_coef,
        "entropy_adapt_mult": ent_adapt_mult,
        "clip_fraction": sum(clip_fracs) / len(clip_fracs),
        "pool_size": len(pool),
      },
      global_step,
    )
    pbar.set_postfix(
      pg=f"{pg_losses[-1]:.3f}",
      v=f"{v_losses[-1]:.3f}",
      ent=f"{mean_ent:.3f}",
      pool=len(pool),
    )

    if rollout_n % cfg.snapshot_every_rollouts == 0:
      pool.add(net)

    if global_step % cfg.eval_every == 0 or global_step >= cfg.total_steps:
      wr_random = _eval_winrate(net, random_opp, cfg.eval_games, device)
      wr_d4 = _eval_winrate(net, d4, cfg.eval_games, device)
      logger.scalars(
        "eval",
        {
          "winrate_vs_random": wr_random,
          "winrate_vs_minimax_d4": wr_d4,
        },
        global_step,
      )
      tqdm.write(
        f"step {global_step}: vs_random={wr_random:.1%} vs_d4={wr_d4:.1%} "
        f"ent={mean_ent:.2f} mult={ent_adapt_mult:.2f}"
      )
      _save_ckpt(net, cfg.artifacts_dir / "latest.pt", global_step, cfg)
      score = wr_random + wr_d4
      if score > best_score:
        best_score = score
        _save_ckpt(net, cfg.artifacts_dir / "best.pt", global_step, cfg)
        logger.scalar("promotion/event", global_step, global_step)

  pbar.close()
  logger.close()


if __name__ == "__main__":
  train()
