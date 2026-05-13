#!/usr/bin/env python
"""Round-robin tournament. Writes artifacts/elo.json."""

import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

from oware.agents.dqn.env import OwareEnv
from oware.agents.registry import get_agent, list_agents
from oware.engine import NORTH, SOUTH, terminal

GAMES_PER_PAIR = 100
ELO_K = 32
ELO_PASSES = 10
OUT = Path("artifacts/elo.json")


def play_pair(a_id: str, b_id: str, games: int) -> tuple[float, float]:
  """Returns (a_score, b_score) where score = wins + 0.5*draws."""
  a = get_agent(a_id)
  b = get_agent(b_id)
  a_score = 0.0
  env = OwareEnv()
  for i in range(games):
    a_side = SOUTH if i % 2 == 0 else NORTH
    env.reset(seed=i)
    for _ in range(500):
      s = env.state
      done, _ = terminal(s)
      if done:
        break
      agent = a if s.to_move == a_side else b
      action, _ = agent.choose_move(s)
      env.step(action)
    done, winner = terminal(env.state)
    if done:
      if winner == a_side:
        a_score += 1.0
      elif winner == -1:
        a_score += 0.5
  return a_score, games - a_score


def expected(ra: float, rb: float) -> float:
  return 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))


def main() -> None:
  agents = [a.id for a in list_agents()]
  print(f"Agents: {agents}")
  elo = {a: 1000.0 for a in agents}

  # Collect all pair results first
  results: dict[tuple[str, str], tuple[float, float]] = {}
  pairs = [(a, b) for i, a in enumerate(agents) for b in agents[i + 1 :]]
  for a_id, b_id in pairs:
    print(f"  {a_id} vs {b_id} ...", end=" ", flush=True)
    sa, sb = play_pair(a_id, b_id, GAMES_PER_PAIR)
    results[(a_id, b_id)] = (sa, sb)
    print(f"{sa:.0f}-{sb:.0f}")

  # Iterative Elo convergence
  for _ in range(ELO_PASSES):
    for (a_id, b_id), (sa, sb) in results.items():
      ea = expected(elo[a_id], elo[b_id])
      actual_a = sa / GAMES_PER_PAIR
      elo[a_id] += ELO_K * (actual_a - ea)
      elo[b_id] += ELO_K * ((1 - actual_a) - (1 - ea))

  elo_int = {k: round(v) for k, v in sorted(elo.items(), key=lambda x: -x[1])}
  OUT.parent.mkdir(parents=True, exist_ok=True)
  OUT.write_text(json.dumps(elo_int, indent=2))

  print("\nFinal Elo:")
  for agent_id, rating in elo_int.items():
    print(f"  {agent_id:20s} {rating}")
  print(f"\nWritten to {OUT}")


if __name__ == "__main__":
  main()
