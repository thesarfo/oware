from collections.abc import Callable

from oware.agents.base import Agent, AgentInfo
from oware.agents.random_agent import RandomAgent


_FACTORIES: dict[str, Callable[[int | None], Agent]] = {
    RandomAgent.info.id: lambda seed: RandomAgent(seed=seed),
}

REGISTRY: list[AgentInfo] = [RandomAgent.info]


def list_agents() -> list[AgentInfo]:
    return list(REGISTRY)


def get_agent(agent_id: str, *, seed: int | None = None) -> Agent:
    if agent_id not in _FACTORIES:
        raise KeyError(f"unknown agent: {agent_id}")
    return _FACTORIES[agent_id](seed)
