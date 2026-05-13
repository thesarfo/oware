"""AlphaZero-lite training. Usage: python -m oware.agents.az.train"""

import copy
import dataclasses
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from tqdm import tqdm

from oware.agents.az.buffer import SelfPlayBuffer
from oware.agents.az.mcts import search
from oware.agents.az.model import AZNetwork
from oware.engine import NORTH, SOUTH, encode, initial_state, step, terminal
from oware.training.logging import RunLogger


@dataclasses.dataclass
class Config:
  total_games: int = 20_000
  selfplay_sims: int = 200
  eval_sims: int = 200
  batch_size: int = 512
  lr: float = 1e-3
  weight_decay: float = 1e-4
  eval_every_games: int = 200
  eval_games: int = 100
  warmup_positions: int = 1_000
  train_every_n_positions: int = 4
  buffer_capacity: int = 500_000
  tau_threshold: int = 15
  promote_threshold: float = 0.55
  seed: int = 42
  artifacts_dir: Path = Path("artifacts/az")
  tb_dir: Path = Path("artifacts/tb/az")


def _play_one_selfplay_game(
  net: AZNetwork,
  device: torch.device,
  cfg: Config,
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
  """Play one self-play game; return (obs, pi, z) arrays for the buffer, or None if it didn't terminate cleanly."""
  s = initial_state()
  obs_list: list[np.ndarray] = []
  pi_list: list[np.ndarray] = []
  side_list: list[int] = []
  ply = 0

  while True:
    done, _ = terminal(s)
    if done:
      break
    pi = search(s, net, device, cfg.selfplay_sims, add_noise=True)
    if ply < cfg.tau_threshold:
      probs = pi / (pi.sum() + 1e-8)
      action = int(np.random.choice(6, p=probs))
    else:
      action = int(np.argmax(pi))
    obs_list.append(encode(s))
    pi_list.append(pi)
    side_list.append(s.to_move)
    s, _ = step(s, action)
    ply += 1

  done, winner = terminal(s)
  if not done or not obs_list:
    return None

  # z[i] is the outcome from the perspective of the side to move at position i.
  # +1 if that side won, -1 if it lost, 0 for a draw.
  z = np.zeros(len(obs_list), dtype=np.float32)
  if winner != -1:
    for i, side in enumerate(side_list):
      z[i] = 1.0 if winner == side else -1.0

  return (
    np.array(obs_list, dtype=np.float32),
    np.array(pi_list, dtype=np.float32),
    z,
  )


def _eval_vs_net(
  candidate: AZNetwork,
  best: AZNetwork,
  games: int,
  sims: int,
  device: torch.device,
) -> float:
  """Candidate plays `games` matches vs. `best` at the given sim budget. Returns candidate winrate."""
  candidate.eval()
  best.eval()
  wins = 0
  for i in range(games):
    cand_side = SOUTH if i % 2 == 0 else NORTH
    s = initial_state()
    while True:
      done, _ = terminal(s)
      if done:
        break
      net = candidate if s.to_move == cand_side else best
      pi = search(s, net, device, sims, add_noise=False)
      s, _ = step(s, int(np.argmax(pi)))
    _, winner = terminal(s)
    if winner == cand_side:
      wins += 1
  return wins / games


def _save_ckpt(net: AZNetwork, path: Path, step_n: int, cfg: Config) -> None:
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
  print(f"[az] device={device}")
  print(f"[az] config={dataclasses.asdict(cfg)}")
  logger.text("meta/config", str(dataclasses.asdict(cfg)), 0)

  net = AZNetwork().to(device)
  best_net = copy.deepcopy(net)
  best_net.eval()
  optimizer = torch.optim.Adam(
    net.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay
  )
  buf = SelfPlayBuffer(cfg.buffer_capacity)

  _save_ckpt(net, cfg.artifacts_dir / "latest.pt", 0, cfg)
  _save_ckpt(net, cfg.artifacts_dir / "best.pt", 0, cfg)

  pbar = tqdm(
    total=cfg.total_games,
    desc=f"az [{device}]",
    unit="game",
    disable=not sys.stdout.isatty(),
  )

  train_step = 0
  positions_since_train = 0

  for game_n in range(1, cfg.total_games + 1):
    net.eval()
    result = _play_one_selfplay_game(net, device, cfg)
    if result is None:
      pbar.update(1)
      continue
    obs, pi, z = result
    buf.push_game(obs, pi, z)
    positions_since_train += len(obs)

    losses: list[float] = []
    pol_losses: list[float] = []
    val_losses: list[float] = []
    if len(buf) >= cfg.warmup_positions:
      net.train()
      while positions_since_train >= cfg.train_every_n_positions:
        positions_since_train -= cfg.train_every_n_positions
        train_step += 1
        b_obs, b_pi, b_z = buf.sample(cfg.batch_size)
        obs_t = torch.as_tensor(b_obs, device=device)
        pi_t = torch.as_tensor(b_pi, device=device)
        z_t = torch.as_tensor(b_z, device=device)
        mask = (pi_t > 0).float()
        log_probs, value = net(obs_t, mask)
        policy_loss = -(pi_t * log_probs).sum(dim=-1).mean()
        value_loss = F.mse_loss(value, z_t)
        loss = policy_loss + value_loss
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        optimizer.step()
        losses.append(loss.item())
        pol_losses.append(policy_loss.item())
        val_losses.append(value_loss.item())

    pbar.update(1)
    pbar.set_postfix(
      game=game_n,
      buf=len(buf),
      loss=f"{(sum(losses) / len(losses)) if losses else 0:.3f}",
    )

    if losses:
      logger.scalars(
        "train",
        {
          "loss": sum(losses) / len(losses),
          "policy_loss": sum(pol_losses) / len(pol_losses),
          "value_loss": sum(val_losses) / len(val_losses),
          "buffer_size": len(buf),
        },
        train_step,
      )
    logger.scalar("selfplay/game_plies", len(obs), game_n)

    _save_ckpt(net, cfg.artifacts_dir / "latest.pt", train_step, cfg)

    if game_n % cfg.eval_every_games == 0:
      wr = _eval_vs_net(net, best_net, cfg.eval_games, cfg.eval_sims, device)
      logger.scalar("eval/winrate_vs_best", wr, game_n)
      tqdm.write(f"[eval] game {game_n}: vs_best={wr:.1%}")
      if wr >= cfg.promote_threshold:
        best_net = copy.deepcopy(net)
        best_net.eval()
        _save_ckpt(net, cfg.artifacts_dir / "best.pt", train_step, cfg)
        logger.scalar("promotion/event", game_n, game_n)
        tqdm.write(f"  → promoted at game {game_n} (train_step {train_step})")

  pbar.close()
  logger.close()


if __name__ == "__main__":
  train()
