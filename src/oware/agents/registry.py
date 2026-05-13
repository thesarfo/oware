from collections.abc import Callable
from pathlib import Path

from oware.agents.base import Agent, AgentInfo
from oware.agents.minimax import MinimaxAgent
from oware.agents.random_agent import RandomAgent

_DQN_CHECKPOINT = Path("artifacts/dqn/latest.pt")

_FACTORIES: dict[str, Callable[[int | None], Agent]] = {
  RandomAgent.info.id: lambda seed: RandomAgent(seed=seed),
  "minimax_d2": lambda _: MinimaxAgent(max_depth=2),
  "minimax_d4": lambda _: MinimaxAgent(max_depth=4),
  "minimax_d6": lambda _: MinimaxAgent(max_depth=6),
}

REGISTRY: list[AgentInfo] = [
  RandomAgent.info,
  MinimaxAgent(max_depth=2).info,
  MinimaxAgent(max_depth=4).info,
  MinimaxAgent(max_depth=6).info,
]

if _DQN_CHECKPOINT.exists():
  from oware.agents.dqn.agent import DQNAgent

  _FACTORIES["dqn"] = lambda _: DQNAgent.load(_DQN_CHECKPOINT)
  REGISTRY.append(DQNAgent.info)


def list_agents() -> list[AgentInfo]:
  return list(REGISTRY)


def get_agent(agent_id: str, *, seed: int | None = None) -> Agent:
  if agent_id not in _FACTORIES:
    raise KeyError(f"unknown agent: {agent_id}")
  return _FACTORIES[agent_id](seed)
