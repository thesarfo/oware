import os
from collections.abc import Callable
from pathlib import Path

from oware.agents.base import Agent, AgentInfo
from oware.agents.minimax import MinimaxAgent
from oware.agents.random_agent import RandomAgent

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DQN_CHECKPOINT = Path(
  os.environ.get("OWARE_DQN_CHECKPOINT", _PROJECT_ROOT / "artifacts/dqn/latest.pt")
)

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

_PPO_CHECKPOINT = Path(
  os.environ.get("OWARE_PPO_CHECKPOINT", _PROJECT_ROOT / "artifacts/ppo/latest.pt")
)

if _PPO_CHECKPOINT.exists():
  from oware.agents.ppo.agent import PPOAgent

  _FACTORIES["ppo"] = lambda _: PPOAgent.load(_PPO_CHECKPOINT)
  REGISTRY.append(PPOAgent.info)

_AZ_CHECKPOINT = Path(
  os.environ.get("OWARE_AZ_CHECKPOINT", _PROJECT_ROOT / "artifacts/az/latest.pt")
)

if _AZ_CHECKPOINT.exists():
  from oware.agents.az.agent import AZAgent

  _FACTORIES["az"] = lambda _: AZAgent.load(_AZ_CHECKPOINT, n_sims=100)
  REGISTRY.append(AZAgent.info)


def list_agents() -> list[AgentInfo]:
  return list(REGISTRY)


def get_agent(agent_id: str, *, seed: int | None = None) -> Agent:
  if agent_id not in _FACTORIES:
    raise KeyError(f"unknown agent: {agent_id}")
  return _FACTORIES[agent_id](seed)
