"""AlphaZero-lite training. Usage: python -m oware.agents.az.train"""

import copy
import dataclasses
import random
import sys
import threading
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from oware.agents.az.buffer import SelfPlayBuffer
from oware.agents.az.mcts import search
from oware.agents.az.model import AZNetwork
from oware.engine import NORTH, SOUTH, encode, step, terminal
from oware.training.logging import RunLogger


@dataclasses.dataclass
class Config:
  train_steps: int = 200_000
  selfplay_sims: int = 200
  eval_sims: int = 200
  server_sims: int = 100
  batch_size: int = 512
  lr: float = 1e-3
  weight_decay: float = 1e-4
  eval_every: int = 500
  eval_games: int = 100
  warmup_samples: int = 1_000
  buffer_capacity: int = 500_000
  tau_threshold: int = 15  # plies before switching to argmax
  seed: int = 42
  artifacts_dir: Path = Path("artifacts/az")
  tb_dir: Path = Path("artifacts/tb/az")


def _selfplay_worker(
  net: AZNetwork,
  buf: SelfPlayBuffer,
  cfg: Config,
  device: torch.device,
  stop: threading.Event,
  net_lock: threading.Lock,
) -> None:
  game = 0
  while not stop.is_set():
    agent_side = SOUTH if game % 2 == 0 else NORTH
    game += 1
    from oware.engine import initial_state

    s = initial_state()
    obs_list, pi_list = [], []
    ply = 0

    while True:
      done, _ = terminal(s)
      if done:
        break
      with net_lock:
        pi = search(s, net, device, cfg.selfplay_sims, add_noise=True)
      if ply < cfg.tau_threshold:
        counts = pi.copy()
        counts /= counts.sum() + 1e-8
        action = int(np.random.choice(6, p=counts))
      else:
        action = int(np.argmax(pi))
      obs_list.append(encode(s))
      pi_list.append(pi)
      s, _ = step(s, action)
      ply += 1

    done, winner = terminal(s)
    if not done:
      continue
    obs_arr = np.array(obs_list, dtype=np.float32)
    pi_arr = np.array(pi_list, dtype=np.float32)
    # z from each position's perspective
    z_arr = np.array(
      [
        (1.0 if winner == agent_side else (-1.0 if winner != -1 else 0.0))
        * (1 if i % 2 == 0 else -1)
        for i in range(len(obs_list))
      ],
      dtype=np.float32,
    )
    buf.push_game(obs_arr, pi_arr, z_arr)


def _eval_vs_net(
  candidate: AZNetwork,
  best: AZNetwork,
  games: int,
  sims: int,
  device: torch.device,
) -> float:
  wins = 0
  from oware.engine import initial_state

  for i in range(games):
    cand_side = SOUTH if i % 2 == 0 else NORTH
    s = initial_state()
    for _ in range(500):
      done, _ = terminal(s)
      if done:
        break
      net = candidate if s.to_move == cand_side else best
      pi = search(s, net, device, sims, add_noise=False)
      s, _ = step(s, int(np.argmax(pi)))
    done, winner = terminal(s)
    if done and winner == cand_side:
      wins += 1
  return wins / games


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
  net = AZNetwork().to(device)
  best_net = copy.deepcopy(net)
  best_net.eval()
  optimizer = torch.optim.Adam(
    net.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay
  )

  buf = SelfPlayBuffer(cfg.buffer_capacity)
  net_lock = threading.Lock()
  stop = threading.Event()

  sp_thread = threading.Thread(
    target=_selfplay_worker,
    args=(net, buf, cfg, device, stop, net_lock),
    daemon=True,
  )
  sp_thread.start()

  try:
    from tqdm import tqdm

    pbar = tqdm(
      total=cfg.train_steps, desc="az", unit="step", disable=not sys.stdout.isatty()
    )
  except ImportError:
    pbar = None

  # Save initial best
  torch.save(
    {
      "model": net.state_dict(),
      "step": 0,
      "config": {
        k: str(v) if isinstance(v, Path) else v
        for k, v in dataclasses.asdict(cfg).items()
      },
    },
    cfg.artifacts_dir / "latest.pt",
  )

  for train_step in range(1, cfg.train_steps + 1):
    while len(buf) < cfg.warmup_samples:
      time.sleep(0.1)

    obs, pi, z = buf.sample(cfg.batch_size)
    obs_t = torch.as_tensor(obs, device=device)
    pi_t = torch.as_tensor(pi, device=device)
    z_t = torch.as_tensor(z, device=device)

    mask = (pi_t > 0).float()
    with net_lock:
      log_probs, value = net(obs_t, mask)

    policy_loss = -(pi_t * log_probs).sum(dim=-1).mean()
    value_loss = F.mse_loss(value, z_t)
    loss = policy_loss + value_loss

    optimizer.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
    optimizer.step()

    if pbar:
      pbar.update(1)

    if train_step % 100 == 0:
      logger.scalars(
        "train",
        {
          "loss": loss.item(),
          "policy_loss": policy_loss.item(),
          "value_loss": value_loss.item(),
          "buffer_size": len(buf),
        },
        train_step,
      )

    if train_step % cfg.eval_every == 0:
      net.eval()
      wr = _eval_vs_net(net, best_net, cfg.eval_games, cfg.eval_sims, device)
      net.train()
      logger.scalar("eval/winrate_vs_best", wr, train_step)
      if pbar:
        tqdm.write(f"step {train_step}: vs_best={wr:.1%}")
      if wr >= 0.55:
        best_net = copy.deepcopy(net)
        best_net.eval()
        torch.save(
          {
            "model": net.state_dict(),
            "step": train_step,
            "config": {
              k: str(v) if isinstance(v, Path) else v
              for k, v in dataclasses.asdict(cfg).items()
            },
          },
          cfg.artifacts_dir / "latest.pt",
        )
        logger.scalar("promotion/event", train_step, train_step)
        if pbar:
          tqdm.write(f"  → promoted at step {train_step}")

  stop.set()
  if pbar:
    pbar.close()
  logger.close()


if __name__ == "__main__":
  train()
