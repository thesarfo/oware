"""DQN training loop.

Usage:
    python -m oware.agents.dqn.train
"""

import dataclasses
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from oware.agents.dqn.buffer import ReplayBuffer
from oware.agents.dqn.env import OwareEnv
from oware.agents.dqn.model import QNetwork
from oware.agents.minimax import MinimaxAgent
from oware.agents.random_agent import RandomAgent
from oware.engine import NORTH, SOUTH, encode, legal_moves, terminal
from oware.training.logging import RunLogger


@dataclasses.dataclass
class Config:
  total_steps: int = 1_300_000
  buffer_capacity: int = 200_000
  batch_size: int = 256
  lr: float = 1e-4
  gamma: float = 0.99
  eps_start: float = 1.0
  eps_end: float = 0.05
  eps_decay_steps: int = 200_000
  target_update_every: int = 2_000
  warmup_steps: int = 5_000
  eval_every: int = 10_000
  eval_games: int = 100
  opponent_switch_step: int = 50_000
  seed: int = 42
  dueling: bool = True
  artifacts_dir: Path = Path("artifacts/dqn")
  tb_dir: Path = Path("artifacts/tb/dqn")


def _epsilon(step: int, cfg: Config) -> float:
  frac = min(step / cfg.eps_decay_steps, 1.0)
  return cfg.eps_start + frac * (cfg.eps_end - cfg.eps_start)


def _obs_for(env: OwareEnv) -> dict:
  s = env.state
  mask = np.zeros(6, dtype=np.int8)
  for m in legal_moves(s):
    mask[m] = 1
  return {"observation": encode(s), "action_mask": mask}


def _eval_winrate(
  online: QNetwork, opponent, games: int, device: torch.device
) -> float:
  wins = 0
  env = OwareEnv()
  for i in range(games):
    agent_side = SOUTH if i % 2 == 0 else NORTH
    env.reset(seed=i)
    for _ in range(500):
      s = env.state
      done, _ = terminal(s)
      if done:
        break
      if s.to_move == agent_side:
        obs = _obs_for(env)
        with torch.no_grad():
          q = online(torch.as_tensor(obs["observation"], device=device).unsqueeze(0))[0]
        q = q.cpu().numpy()
        q[obs["action_mask"] == 0] = -float("inf")
        action = int(np.argmax(q))
      else:
        action, _ = opponent.choose_move(s)
      env.step(action)
    done, winner = terminal(env.state)
    if done and winner == agent_side:
      wins += 1
  return wins / games


def _pick_opponent(step: int, cfg: Config, random_opp, minimax_d2, minimax_d4):
  if step < cfg.opponent_switch_step:
    return random_opp
  r = random.random()
  if r < 0.34:
    return random_opp
  if r < 0.67:
    return minimax_d2
  return minimax_d4


def train(cfg: Config | None = None) -> None:
  if cfg is None:
    cfg = Config()

  cfg.artifacts_dir.mkdir(parents=True, exist_ok=True)
  run_id = f"{int(time.time())}"
  logger = RunLogger(cfg.tb_dir / run_id)
  logger.text("meta/config", str(dataclasses.asdict(cfg)), 0)

  torch.manual_seed(cfg.seed)
  np.random.seed(cfg.seed)
  random.seed(cfg.seed)

  device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
  online = QNetwork(dueling=cfg.dueling).to(device)
  target = QNetwork(dueling=cfg.dueling).to(device)
  target.load_state_dict(online.state_dict())
  target.eval()
  optimizer = torch.optim.Adam(online.parameters(), lr=cfg.lr)
  buffer = ReplayBuffer(cfg.buffer_capacity)

  random_opp = RandomAgent(seed=cfg.seed)
  minimax_d2 = MinimaxAgent(max_depth=2)
  minimax_d4 = MinimaxAgent(max_depth=4)

  env = OwareEnv()
  best_winrate = 0.0
  global_step = 0
  game_count = 0

  try:
    from tqdm import tqdm

    pbar = tqdm(
      total=cfg.total_steps, desc="dqn", unit="step", disable=not sys.stdout.isatty()
    )
  except ImportError:
    pbar = None

  while global_step < cfg.total_steps:
    # Alternate which side the agent plays each game to train both perspectives.
    agent_side = SOUTH if game_count % 2 == 0 else NORTH
    env.reset(seed=game_count)
    game_count += 1
    episode_return = 0.0

    for _ in range(500):
      s = env.state
      done, _ = terminal(s)
      if done:
        break

      if s.to_move != agent_side:
        opp = _pick_opponent(global_step, cfg, random_opp, minimax_d2, minimax_d4)
        opp_action, _ = opp.choose_move(s)
        env.step(opp_action)
        continue

      # Agent's turn — collect a full transition including opponent's response.
      obs = _obs_for(env)
      eps = _epsilon(global_step, cfg)
      if random.random() < eps:
        action = int(np.random.choice(np.where(obs["action_mask"])[0]))
      else:
        with torch.no_grad():
          q = online(torch.as_tensor(obs["observation"], device=device).unsqueeze(0))[0]
        q_np = q.cpu().numpy()
        q_np[obs["action_mask"] == 0] = -float("inf")
        action = int(np.argmax(q_np))

      # Apply agent move.
      _, agent_reward, terminated, _, _ = env.step(action)

      if not terminated:
        # Apply opponent response so s' is the next state the agent faces.
        s_mid = env.state
        done_mid, _ = terminal(s_mid)
        if not done_mid and s_mid.to_move != agent_side:
          opp = _pick_opponent(global_step, cfg, random_opp, minimax_d2, minimax_d4)
          opp_action, _ = opp.choose_move(s_mid)
          _, _, terminated, _, _ = env.step(opp_action)
          # If opponent's move ends the game, agent gets -1.
          if terminated:
            done_final, winner = terminal(env.state)
            if done_final:
              agent_reward = (
                1.0 if winner == agent_side else (-1.0 if winner != -1 else 0.0)
              )

      next_obs = _obs_for(env)
      buffer.push(
        obs["observation"].copy(),
        action,
        agent_reward,
        next_obs["observation"].copy(),
        terminated,
        next_obs["action_mask"].copy(),
      )
      episode_return += agent_reward

      global_step += 1
      if pbar:
        pbar.update(1)
        if global_step % 500 == 0:
          pbar.set_postfix(eps=f"{_epsilon(global_step, cfg):.2f}", buf=len(buffer))

      if terminated:
        logger.scalar("train/episode_return", episode_return, global_step)
        break

      # Training update every 4 agent steps.
      if len(buffer) >= cfg.warmup_steps and global_step % 4 == 0:
        b_obs, b_act, b_rew, b_next, b_done, b_nmask = buffer.sample(
          cfg.batch_size, device
        )

        with torch.no_grad():
          q_next = online(b_next)
          q_next[b_nmask == 0] = -float("inf")
          best_actions = q_next.argmax(dim=1, keepdim=True)
          q_target_vals = target(b_next).gather(1, best_actions).squeeze(1)
          td_target = b_rew + cfg.gamma * q_target_vals * (1 - b_done)

        q_pred = online(b_obs).gather(1, b_act.unsqueeze(1)).squeeze(1)
        loss = F.huber_loss(q_pred, td_target)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if global_step % 500 == 0:
          logger.scalars(
            "train",
            {
              "loss": loss.item(),
              "epsilon": _epsilon(global_step, cfg),
              "replay_buffer_size": len(buffer),
              "td_error_mean": (q_pred - td_target).abs().mean().item(),
            },
            global_step,
          )

      if global_step % cfg.target_update_every == 0:
        target.load_state_dict(online.state_dict())

      if global_step % cfg.eval_every == 0:
        wr_random = _eval_winrate(online, random_opp, cfg.eval_games, device)
        wr_d2 = _eval_winrate(online, minimax_d2, cfg.eval_games, device)
        wr_d4 = _eval_winrate(online, minimax_d4, cfg.eval_games, device)
        logger.scalars(
          "eval",
          {
            "winrate_vs_random": wr_random,
            "winrate_vs_minimax_d2": wr_d2,
            "winrate_vs_minimax_d4": wr_d4,
          },
          global_step,
        )
        if pbar:
          tqdm.write(
            f"step {global_step}: vs_random={wr_random:.1%} vs_d2={wr_d2:.1%} vs_d4={wr_d4:.1%}"
          )
        if wr_random + wr_d2 > best_winrate:
          best_winrate = wr_random + wr_d2
          torch.save(
            {
              "model": online.state_dict(),
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
