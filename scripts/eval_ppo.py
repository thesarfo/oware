#!/usr/bin/env python
"""Eval: PPO vs Minimax-d2 (>=80%) and Minimax-d4 (>=55%) over 200 games each."""

import sys
from pathlib import Path

sys.path.insert(0, "src")

from oware.agents.dqn.env import OwareEnv
from oware.agents.minimax import MinimaxAgent
from oware.agents.ppo.agent import PPOAgent
from oware.engine import NORTH, SOUTH, terminal

CHECKPOINT = Path("artifacts/ppo/latest.pt")
GAMES = 200
D2_THRESHOLD = 0.80
D4_THRESHOLD = 0.55


def eval_winrate(agent: PPOAgent, opponent, games: int) -> float:
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
        action, _ = agent.choose_move(s)
      else:
        action, _ = opponent.choose_move(s)
      env.step(action)
    done, winner = terminal(env.state)
    if done and winner == agent_side:
      wins += 1
  return wins / games


def main() -> None:
  if not CHECKPOINT.exists():
    print(f"Checkpoint not found: {CHECKPOINT}")
    sys.exit(1)

  agent = PPOAgent.load(CHECKPOINT)
  wr_d2 = eval_winrate(agent, MinimaxAgent(max_depth=2), GAMES)
  wr_d4 = eval_winrate(agent, MinimaxAgent(max_depth=4), GAMES)

  print(f"vs Minimax-d2: {wr_d2:.1%}  (threshold >= {D2_THRESHOLD:.0%})")
  print(f"vs Minimax-d4: {wr_d4:.1%}  (threshold >= {D4_THRESHOLD:.0%})")

  passed = wr_d2 >= D2_THRESHOLD and wr_d4 >= D4_THRESHOLD
  print("\nRESULT:", "PASS" if passed else "FAIL")
  sys.exit(0 if passed else 1)


if __name__ == "__main__":
  main()
