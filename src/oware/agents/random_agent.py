import random
from typing import Any

from oware.agents.base import AgentInfo
from oware.engine import State, legal_moves


class RandomAgent:
  info = AgentInfo(
    id="random",
    name="Random",
    family="baseline",
    description="Plays a uniformly random legal move. Useful as a sanity baseline.",
    est_elo=0,
  )

  def __init__(self, seed: int | None = None) -> None:
    self._rng = random.Random(seed)

  def choose_move(
    self,
    state: State,
    *,
    time_budget_ms: int | None = None,
  ) -> tuple[int, dict[str, Any]]:
    moves = legal_moves(state)
    chosen = self._rng.choice(moves)
    scores = [1.0 if i in moves else None for i in range(6)]
    return chosen, {"scores": scores}
