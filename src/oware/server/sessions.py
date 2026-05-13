import secrets
from dataclasses import dataclass, field
from typing import Any

from oware.agents.base import Agent
from oware.engine import State


@dataclass
class GameSession:
  game_id: str
  agent: Agent
  human_side: int  # 0=south, 1=north
  state: State
  seed: int | None
  client_id_hash: str | None
  ended: bool = False
  last_move_pit: int | None = None
  last_move_by: int | None = None
  last_move_captured: int = 0
  moves: list[dict[str, Any]] = field(default_factory=list)


class SessionStore:
  """Process-wide registry of active games.

  Each WebSocket connection is the sole owner of any game_id it creates.
  The store rejects look-ups from non-owners.
  """

  def __init__(self, *, max_games: int = 10_000) -> None:
    self._games: dict[str, GameSession] = {}
    self._owners: dict[str, int] = {}
    self._max_games = max_games

  def create(
    self,
    *,
    owner: int,
    agent: Agent,
    human_side: int,
    state: State,
    seed: int | None,
    client_id_hash: str | None,
  ) -> GameSession:
    if len(self._games) >= self._max_games:
      self._evict_one_ended()
      if len(self._games) >= self._max_games:
        raise RuntimeError("session cap reached")
    game_id = f"g_{secrets.token_urlsafe(9)}"
    session = GameSession(
      game_id=game_id,
      agent=agent,
      human_side=human_side,
      state=state,
      seed=seed,
      client_id_hash=client_id_hash,
    )
    self._games[game_id] = session
    self._owners[game_id] = owner
    return session

  def get(self, *, owner: int, game_id: str) -> GameSession | None:
    if self._owners.get(game_id) != owner:
      return None
    return self._games.get(game_id)

  def drop_connection(self, owner: int) -> list[GameSession]:
    dropped = [gid for gid, o in self._owners.items() if o == owner]
    sessions: list[GameSession] = []
    for gid in dropped:
      sessions.append(self._games[gid])
      self._owners.pop(gid, None)
    return sessions

  def remove(self, game_id: str) -> None:
    self._games.pop(game_id, None)
    self._owners.pop(game_id, None)

  def _evict_one_ended(self) -> None:
    for gid, sess in self._games.items():
      if sess.ended:
        self.remove(gid)
        return

  def __len__(self) -> int:
    return len(self._games)
