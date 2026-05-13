"""SQLite telemetry writer. See docs/TELEMETRY.md for schema rationale."""

import asyncio
import json
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from oware.engine import State

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    game_id            TEXT PRIMARY KEY,
    created_at         INTEGER NOT NULL,
    ended_at           INTEGER,
    agent_id           TEXT NOT NULL,
    agent_checkpoint   TEXT,
    opponent_kind      TEXT NOT NULL,
    opponent_agent_id  TEXT,
    human_plays        TEXT,
    client_id_hash     TEXT,
    seed               INTEGER,
    initial_state_json TEXT NOT NULL,
    winner             TEXT,
    end_reason         TEXT,
    final_store_south  INTEGER,
    final_store_north  INTEGER,
    total_plies        INTEGER,
    schema_version     INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_games_agent_id ON games(agent_id);
CREATE INDEX IF NOT EXISTS idx_games_created_at ON games(created_at);

CREATE TABLE IF NOT EXISTS moves (
    game_id            TEXT NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    ply                INTEGER NOT NULL,
    side               TEXT NOT NULL,
    actor              TEXT NOT NULL,
    action             INTEGER NOT NULL,
    captured           INTEGER NOT NULL,
    pits_after_json    TEXT NOT NULL,
    store_south_after  INTEGER NOT NULL,
    store_north_after  INTEGER NOT NULL,
    thought_ms         INTEGER,
    agent_extras_json  TEXT,
    PRIMARY KEY (game_id, ply)
);

CREATE INDEX IF NOT EXISTS idx_moves_game_id ON moves(game_id);
"""


def _now_ms() -> int:
  return int(time.time() * 1000)


def _state_to_json(s: State) -> str:
  return json.dumps(
    {
      "pits": list(s.pits),
      "stores": list(s.stores),
      "to_move": s.to_move,
      "ply": s.ply,
    }
  )


class Telemetry:
  def __init__(self, db_path: Path) -> None:
    self._db_path = db_path
    self._db_path.parent.mkdir(parents=True, exist_ok=True)
    self._conn = sqlite3.connect(
      str(db_path), check_same_thread=False, isolation_level=None
    )
    self._conn.execute("PRAGMA journal_mode=WAL")
    self._conn.execute("PRAGMA synchronous=NORMAL")
    self._conn.executescript(SCHEMA)
    self._queue: asyncio.Queue[tuple[str, tuple] | None] = asyncio.Queue()
    self._worker: asyncio.Task | None = None

  async def start(self) -> None:
    if self._worker is None:
      self._worker = asyncio.create_task(self._run())

  async def stop(self) -> None:
    if self._worker is not None:
      await self._queue.put(None)
      await self._worker
      self._worker = None
    self._conn.close()

  async def _run(self) -> None:
    while True:
      item = await self._queue.get()
      if item is None:
        return
      sql, params = item
      await asyncio.to_thread(self._conn.execute, sql, params)

  def record_game_start(
    self,
    *,
    game_id: str,
    agent_id: str,
    opponent_kind: str,
    human_plays: str | None,
    client_id_hash: str | None,
    seed: int | None,
    initial_state: State,
  ) -> None:
    self._queue.put_nowait(
      (
        """
                INSERT INTO games
                    (game_id, created_at, agent_id, opponent_kind, human_plays,
                     client_id_hash, seed, initial_state_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
        (
          game_id,
          _now_ms(),
          agent_id,
          opponent_kind,
          human_plays,
          client_id_hash,
          seed,
          _state_to_json(initial_state),
        ),
      )
    )

  def record_move(
    self,
    *,
    game_id: str,
    ply: int,
    side: str,
    actor: str,
    action: int,
    captured: int,
    state_after: State,
    thought_ms: int | None,
    agent_extras: dict[str, Any] | None,
  ) -> None:
    self._queue.put_nowait(
      (
        """
                INSERT INTO moves
                    (game_id, ply, side, actor, action, captured,
                     pits_after_json, store_south_after, store_north_after,
                     thought_ms, agent_extras_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
        (
          game_id,
          ply,
          side,
          actor,
          action,
          captured,
          json.dumps(list(state_after.pits)),
          state_after.stores[0],
          state_after.stores[1],
          thought_ms,
          json.dumps(agent_extras) if agent_extras else None,
        ),
      )
    )

  def record_game_end(
    self,
    *,
    game_id: str,
    winner: str | None,
    end_reason: str,
    final_stores: tuple[int, int],
    total_plies: int,
  ) -> None:
    self._queue.put_nowait(
      (
        """
                UPDATE games
                   SET ended_at = ?,
                       winner = ?,
                       end_reason = ?,
                       final_store_south = ?,
                       final_store_north = ?,
                       total_plies = ?
                 WHERE game_id = ?
                """,
        (
          _now_ms(),
          winner,
          end_reason,
          final_stores[0],
          final_stores[1],
          total_plies,
          game_id,
        ),
      )
    )


@asynccontextmanager
async def telemetry_context(db_path: Path):
  t = Telemetry(db_path)
  await t.start()
  try:
    yield t
  finally:
    await t.stop()
