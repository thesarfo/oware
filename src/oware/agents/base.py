from dataclasses import dataclass
from typing import Any, Protocol

from oware.engine import State


@dataclass(frozen=True, slots=True)
class AgentInfo:
  id: str
  name: str
  family: str
  description: str
  est_elo: int | None = None


class Agent(Protocol):
  info: AgentInfo

  def choose_move(
    self,
    state: State,
    *,
    time_budget_ms: int | None = None,
  ) -> tuple[int, dict[str, Any]]: ...
