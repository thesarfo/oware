import asyncio
import hashlib
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Cookie, FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from oware.agents import get_agent, list_agents
from oware.agents.base import Agent
from oware.engine import (
  NORTH,
  SOUTH,
  IllegalMoveError,
  State,
  initial_state,
  legal_moves,
  step,
  terminal,
)
from oware.server.protocol import (
  AgentBrief,
  AgentMove,
  AgentThinking,
  ClientMove,
  ClientNewGame,
  ClientNewMatch,
  ClientPing,
  ClientResign,
  ErrorMessage,
  GameAnalysis,
  GameOver,
  GameStarted,
  GameState,
  LastMove,
  PongMessage,
  Stores,
)
from oware.server.sessions import GameSession, SessionStore
from oware.server.telemetry import Telemetry

logger = logging.getLogger("oware.server")

CLIENT_COOKIE = "oware_client"
CLIENT_SALT = os.environ.get("OWARE_CLIENT_SALT", "dev-salt-not-for-prod")
DB_PATH = Path(os.environ.get("OWARE_DB", "artifacts/telemetry.db"))

# Cross-site cookies (frontend on Vercel, API on Railway) require SameSite=None
# + Secure. Default to that in prod; allow "lax" locally over http via env.
COOKIE_SAMESITE = os.environ.get("OWARE_COOKIE_SAMESITE", "none").lower()
COOKIE_SECURE = os.environ.get("OWARE_COOKIE_SECURE", "1") == "1"

# Comma-separated list of allowed CORS origins. With credentials the browser
# rejects "*", so we echo specific origins set by the operator.
_RAW_ORIGINS = os.environ.get("OWARE_ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [o.strip() for o in _RAW_ORIGINS.split(",") if o.strip()]


def _hash_client(cookie: str | None) -> str | None:
  if cookie is None:
    return None
  return hashlib.sha256(f"{cookie}{CLIENT_SALT}".encode()).hexdigest()[:16]


def _side_name(side: int) -> str:
  return "south" if side == SOUTH else "north"


def _state_message(session: GameSession) -> GameState:
  s = session.state
  last = None
  if session.last_move_pit is not None and session.last_move_by is not None:
    last = LastMove(
      by=_side_name(session.last_move_by),  # type: ignore[arg-type]
      pit=session.last_move_pit,
      captured=session.last_move_captured,
    )
  return GameState(
    game_id=session.game_id,
    pits=list(s.pits),
    stores=Stores(south=s.stores[0], north=s.stores[1]),
    to_move=_side_name(s.to_move),  # type: ignore[arg-type]
    ply=s.ply,
    legal_moves=legal_moves(s),
    last_move=last,
  )


def _determine_winner(s: State) -> tuple[bool, str | None, str]:
  done, winner_id = terminal(s)
  if not done:
    return False, None, ""
  if winner_id == SOUTH:
    winner = "south"
  elif winner_id == NORTH:
    winner = "north"
  else:
    winner = "draw"
  if s.stores[0] >= 25 or s.stores[1] >= 25:
    reason = "majority"
  elif s.plies_since_capture >= 100:
    reason = "no_progress"
  else:
    reason = "must_feed"
  return True, winner, reason


@asynccontextmanager
async def lifespan(app: FastAPI):
  app.state.telemetry = Telemetry(DB_PATH)
  await app.state.telemetry.start()
  app.state.sessions = SessionStore()
  elo_path = Path(os.environ.get("OWARE_ELO", "artifacts/elo.json"))
  app.state.elo: dict[str, int] = {}
  if elo_path.exists():
    import json
    app.state.elo = json.loads(elo_path.read_text())
  try:
    yield
  finally:
    await app.state.telemetry.stop()


def create_app() -> FastAPI:
  app = FastAPI(lifespan=lifespan, title="Oware Server")
  cors_kwargs: dict[str, Any] = {
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "allow_credentials": True,
  }
  if ALLOWED_ORIGINS == ["*"]:
    # Browsers refuse "*" with credentials. Match any origin via regex and let
    # the middleware echo it back, which is credentials-compatible.
    cors_kwargs["allow_origin_regex"] = ".*"
  else:
    cors_kwargs["allow_origins"] = ALLOWED_ORIGINS
  app.add_middleware(CORSMiddleware, **cors_kwargs)

  @app.get("/healthz")
  async def healthz() -> dict[str, str]:
    return {"status": "ok"}

  @app.get("/stats")
  async def stats(
    scope: str = "all",
    kind: str = "human",
    oware_client: str | None = Cookie(default=None),
  ) -> dict[str, Any]:
    import sqlite3

    if scope == "mine":
      if oware_client is None:
        scope_where = "1=0"
        scope_params: tuple = ()
      else:
        scope_where = "client_id_hash = ?"
        scope_params = (_hash_client(oware_client),)
    else:
      scope_where = "1=1"
      scope_params = ()

    if kind == "human":
      kind_where = "opponent_kind = 'human'"
    elif kind == "match":
      kind_where = "opponent_kind = 'agent'"
    else:
      kind_where = "1=1"

    base_where = f"ended_at IS NOT NULL AND {kind_where} AND {scope_where}"

    conn = sqlite3.connect(str(DB_PATH))
    try:
      totals = conn.execute(
        f"""
                SELECT COUNT(*),
                       COALESCE(AVG(total_plies), 0),
                       SUM(CASE WHEN winner = human_plays THEN 1 ELSE 0 END),
                       SUM(CASE WHEN winner = 'draw' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN winner IS NOT NULL AND winner != 'draw' AND winner != human_plays THEN 1 ELSE 0 END),
                       COUNT(DISTINCT client_id_hash)
                FROM games WHERE {base_where}
                """,
        scope_params,
      ).fetchone()
      by_agent = conn.execute(
        f"""
                SELECT agent_id,
                       COUNT(*) AS games,
                       SUM(CASE WHEN winner = human_plays THEN 1 ELSE 0 END) AS human_wins,
                       SUM(CASE WHEN winner IS NOT NULL AND winner != 'draw' AND winner != human_plays THEN 1 ELSE 0 END) AS agent_wins,
                       SUM(CASE WHEN winner = 'draw' THEN 1 ELSE 0 END) AS draws,
                       SUM(CASE WHEN end_reason = 'resign' THEN 1 ELSE 0 END) AS resigns,
                       COALESCE(AVG(total_plies), 0) AS avg_plies,
                       COALESCE(AVG(final_store_south + final_store_north), 0) AS avg_seeds_captured
                FROM games
                WHERE {base_where}
                GROUP BY agent_id
                ORDER BY games DESC
                """,
        scope_params,
      ).fetchall()
      by_reason = conn.execute(
        f"""
                SELECT end_reason, COUNT(*) AS games
                FROM games WHERE {base_where}
                GROUP BY end_reason ORDER BY games DESC
                """,
        scope_params,
      ).fetchall()
      recent = conn.execute(
        f"""
                SELECT game_id, agent_id, opponent_agent_id, winner, end_reason, total_plies,
                       final_store_south, final_store_north, created_at
                FROM games
                WHERE {base_where}
                ORDER BY ended_at DESC
                LIMIT 12
                """,
        scope_params,
      ).fetchall()
      leaderboard: list[dict] = []
      standings: list[dict] = []
      if kind == "match":
        lb_rows = conn.execute(
          f"""
                  SELECT agent_id, opponent_agent_id,
                         COUNT(*) AS games,
                         SUM(CASE WHEN winner = 'south' THEN 1 ELSE 0 END) AS south_wins,
                         SUM(CASE WHEN winner = 'north' THEN 1 ELSE 0 END) AS north_wins,
                         SUM(CASE WHEN winner = 'draw'  THEN 1 ELSE 0 END) AS draws,
                         COALESCE(AVG(total_plies), 0) AS avg_plies
                  FROM games
                  WHERE {base_where} AND opponent_agent_id IS NOT NULL
                  GROUP BY agent_id, opponent_agent_id
                  ORDER BY games DESC
                  """,
          scope_params,
        ).fetchall()
        leaderboard = [
          {
            "south": r[0],
            "north": r[1],
            "games": r[2],
            "south_wins": r[3] or 0,
            "north_wins": r[4] or 0,
            "draws": r[5] or 0,
            "avg_plies": round(r[6], 1),
          }
          for r in lb_rows
        ]
        # Per-agent standings: union south-side and north-side appearances
        st_rows = conn.execute(
          f"""
                  SELECT agent,
                         SUM(games) AS games,
                         SUM(wins)  AS wins,
                         SUM(losses) AS losses,
                         SUM(draws) AS draws,
                         COALESCE(AVG(avg_plies), 0) AS avg_plies
                  FROM (
                    SELECT agent_id AS agent,
                           COUNT(*) AS games,
                           SUM(CASE WHEN winner = 'south' THEN 1 ELSE 0 END) AS wins,
                           SUM(CASE WHEN winner = 'north' THEN 1 ELSE 0 END) AS losses,
                           SUM(CASE WHEN winner = 'draw'  THEN 1 ELSE 0 END) AS draws,
                           COALESCE(AVG(total_plies), 0) AS avg_plies
                    FROM games
                    WHERE {base_where} AND opponent_agent_id IS NOT NULL
                    GROUP BY agent_id
                    UNION ALL
                    SELECT opponent_agent_id AS agent,
                           COUNT(*) AS games,
                           SUM(CASE WHEN winner = 'north' THEN 1 ELSE 0 END) AS wins,
                           SUM(CASE WHEN winner = 'south' THEN 1 ELSE 0 END) AS losses,
                           SUM(CASE WHEN winner = 'draw'  THEN 1 ELSE 0 END) AS draws,
                           COALESCE(AVG(total_plies), 0) AS avg_plies
                    FROM games
                    WHERE {base_where} AND opponent_agent_id IS NOT NULL
                    GROUP BY opponent_agent_id
                  )
                  GROUP BY agent
                  ORDER BY CAST(wins AS REAL) / NULLIF(games, 0) DESC, wins DESC
                  """,
          scope_params + scope_params,
        ).fetchall()
        standings = [
          {
            "agent": r[0],
            "games": r[1] or 0,
            "wins": r[2] or 0,
            "losses": r[3] or 0,
            "draws": r[4] or 0,
            "win_pct": round((r[2] or 0) / r[1] * 100, 1) if r[1] else 0,
            "avg_plies": round(r[5], 1),
          }
          for r in st_rows
        ]
    finally:
      conn.close()

    return {
      "scope": scope,
      "kind": kind,
      "totals": {
        "games": totals[0] or 0,
        "avg_plies": round(totals[1] or 0, 1),
        "human_wins": totals[2] or 0,
        "draws": totals[3] or 0,
        "agent_wins": totals[4] or 0,
        "unique_clients": totals[5] or 0,
      },
      "by_agent": [
        {
          "agent_id": r[0],
          "games": r[1],
          "human_wins": r[2] or 0,
          "agent_wins": r[3] or 0,
          "draws": r[4] or 0,
          "resigns": r[5] or 0,
          "avg_plies": round(r[6], 1),
          "avg_seeds_captured": round(r[7], 1),
        }
        for r in by_agent
      ],
      "by_reason": [{"reason": r[0], "games": r[1]} for r in by_reason],
      "leaderboard": leaderboard,
      "standings": standings,
      "recent": [
        {
          "game_id": r[0],
          "agent_id": r[1],
          "opponent_agent_id": r[2],
          "winner": r[3],
          "reason": r[4],
          "plies": r[5],
          "south": r[6],
          "north": r[7],
          "created_at": r[8],
        }
        for r in recent
      ],
    }

  @app.get("/games")
  async def games_list(
    scope: str = "mine",
    kind: str = "all",
    page: int = 1,
    page_size: int = 24,
    oware_client: str | None = Cookie(default=None),
  ):
    import json as _json
    import sqlite3

    page = max(1, page)
    page_size = max(1, min(100, page_size))
    offset = (page - 1) * page_size

    where_parts: list[str] = ["g.ended_at IS NOT NULL"]
    params_list: list[Any] = []
    if scope == "mine":
      if oware_client is None:
        return {"total": 0, "page": page, "page_size": page_size, "items": []}
      where_parts.append("g.client_id_hash = ?")
      params_list.append(_hash_client(oware_client))
    if kind == "human":
      where_parts.append("g.opponent_kind = 'human'")
    elif kind == "match":
      where_parts.append("g.opponent_kind = 'agent'")
    where = " AND ".join(where_parts)

    conn = sqlite3.connect(str(DB_PATH))
    try:
      total = conn.execute(
        f"SELECT COUNT(*) FROM games g WHERE {where}", tuple(params_list)
      ).fetchone()[0]
      rows = conn.execute(
        f"""
                SELECT g.game_id, g.agent_id, g.winner, g.end_reason, g.total_plies,
                       g.final_store_south, g.final_store_north, g.created_at, g.ended_at,
                       g.opponent_kind, g.opponent_agent_id,
                       (SELECT m.pits_after_json FROM moves m
                          WHERE m.game_id = g.game_id ORDER BY m.ply DESC LIMIT 1)
                          AS final_pits_json
                FROM games g
                WHERE {where}
                ORDER BY g.ended_at DESC
                LIMIT ? OFFSET ?
                """,
        tuple(params_list) + (page_size, offset),
      ).fetchall()
    finally:
      conn.close()
    return {
      "total": total,
      "page": page,
      "page_size": page_size,
      "items": [
        {
          "game_id": r[0],
          "agent_id": r[1],
          "winner": r[2],
          "reason": r[3],
          "plies": r[4],
          "final_stores": {"south": r[5], "north": r[6]},
          "created_at": r[7],
          "ended_at": r[8],
          "opponent_kind": r[9],
          "opponent_agent_id": r[10],
          "final_pits": _json.loads(r[11]) if r[11] else [0] * 12,
        }
        for r in rows
      ],
    }

  @app.get("/games/{game_id}")
  async def game_detail(
    game_id: str,
    response: Response,
    scope: str = "mine",
    oware_client: str | None = Cookie(default=None),
  ):
    import json as _json
    import sqlite3

    if scope == "all":
      where_clause = "game_id = ?"
      params: tuple = (game_id,)
    else:
      if oware_client is None:
        response.status_code = 404
        return {"error": "not_found"}
      where_clause = "game_id = ? AND client_id_hash = ?"
      params = (game_id, _hash_client(oware_client))

    conn = sqlite3.connect(str(DB_PATH))
    try:
      meta = conn.execute(
        f"""
                SELECT agent_id, winner, end_reason, total_plies,
                       final_store_south, final_store_north,
                       created_at, ended_at, human_plays, initial_state_json,
                       opponent_kind, opponent_agent_id
                FROM games
                WHERE {where_clause}
                """,
        params,
      ).fetchone()
      if meta is None:
        response.status_code = 404
        return {"error": "not_found"}
      moves = conn.execute(
        """
                SELECT ply, side, actor, action, captured,
                       pits_after_json, store_south_after, store_north_after,
                       thought_ms, az_hint
                FROM moves
                WHERE game_id = ?
                ORDER BY ply ASC
                """,
        (game_id,),
      ).fetchall()
    finally:
      conn.close()
    return {
      "game_id": game_id,
      "agent_id": meta[0],
      "winner": meta[1],
      "reason": meta[2],
      "plies": meta[3],
      "final_stores": {"south": meta[4], "north": meta[5]},
      "created_at": meta[6],
      "ended_at": meta[7],
      "human_plays": meta[8],
      "initial_state": _json.loads(meta[9]),
      "opponent_kind": meta[10],
      "opponent_agent_id": meta[11],
      "moves": [
        {
          "ply": m[0],
          "side": m[1],
          "actor": m[2],
          "action": m[3],
          "captured": m[4],
          "pits_after": _json.loads(m[5]),
          "store_south_after": m[6],
          "store_north_after": m[7],
          "thought_ms": m[8],
          "az_hint": m[9],
        }
        for m in moves
      ],
    }

  @app.get("/agents")
  async def agents(response: Response, oware_client: str | None = Cookie(default=None)):
    if oware_client is None:
      response.set_cookie(
        CLIENT_COOKIE,
        secrets.token_urlsafe(16),
        max_age=60 * 60 * 24 * 365,
        samesite=COOKIE_SAMESITE,  # type: ignore[arg-type]
        secure=COOKIE_SECURE,
        httponly=False,
      )
    agents_out = [
      {
        "id": a.id,
        "name": a.name,
        "family": a.family,
        "description": a.description,
        "est_elo": app.state.elo.get(a.id, a.est_elo),
      }
      for a in list_agents()
    ]
    agents_out.sort(key=lambda a: a["est_elo"] if a["est_elo"] is not None else -1, reverse=True)
    return agents_out

  @app.websocket("/play")
  async def play(ws: WebSocket) -> None:
    await ws.accept()
    owner = id(ws)
    sessions: SessionStore = app.state.sessions
    telemetry: Telemetry = app.state.telemetry
    client_cookie = ws.cookies.get(CLIENT_COOKIE)
    client_hash = _hash_client(client_cookie)

    try:
      while True:
        raw = await ws.receive_json()
        await _dispatch(ws, raw, owner, sessions, telemetry, client_hash)
    except WebSocketDisconnect:
      for sess in sessions.drop_connection(owner):
        if not sess.ended:
          sess.ended = True
          telemetry.record_game_end(
            game_id=sess.game_id,
            winner=None,
            end_reason="disconnect",
            final_stores=sess.state.stores,
            total_plies=sess.state.ply,
          )

  return app


async def _dispatch(
  ws: WebSocket,
  raw: dict[str, Any],
  owner: int,
  sessions: SessionStore,
  telemetry: Telemetry,
  client_hash: str | None,
) -> None:
  msg_type = raw.get("type")
  try:
    if msg_type == "new_game":
      await _handle_new_game(
        ws,
        ClientNewGame.model_validate(raw),
        owner,
        sessions,
        telemetry,
        client_hash,
      )
    elif msg_type == "new_match":
      await _handle_new_match(
        ws,
        ClientNewMatch.model_validate(raw),
        owner,
        sessions,
        telemetry,
        client_hash,
      )
    elif msg_type == "move":
      await _handle_move(ws, ClientMove.model_validate(raw), owner, sessions, telemetry)
    elif msg_type == "resign":
      await _handle_resign(
        ws, ClientResign.model_validate(raw), owner, sessions, telemetry
      )
    elif msg_type == "ping":
      ping = ClientPing.model_validate(raw)
      await ws.send_json(PongMessage(t=ping.t).model_dump())
    else:
      await ws.send_json(
        ErrorMessage(
          code="unknown_type", message=f"unknown type: {msg_type!r}"
        ).model_dump()
      )
  except ValidationError as e:
    await ws.send_json(ErrorMessage(code="bad_payload", message=str(e)).model_dump())


async def _handle_new_game(
  ws: WebSocket,
  msg: ClientNewGame,
  owner: int,
  sessions: SessionStore,
  telemetry: Telemetry,
  client_hash: str | None,
) -> None:
  try:
    agent: Agent = get_agent(msg.agent_id, seed=msg.seed)
  except KeyError:
    await ws.send_json(
      ErrorMessage(
        code="unknown_agent", message=f"no such agent: {msg.agent_id}"
      ).model_dump()
    )
    return

  human_side = SOUTH if msg.human_plays == "south" else NORTH
  session = sessions.create(
    owner=owner,
    agent=agent,
    human_side=human_side,
    state=initial_state(),
    seed=msg.seed,
    client_id_hash=client_hash,
  )
  telemetry.record_game_start(
    game_id=session.game_id,
    agent_id=agent.info.id,
    opponent_kind="human",
    human_plays=msg.human_plays,
    client_id_hash=client_hash,
    seed=msg.seed,
    initial_state=session.state,
  )

  await ws.send_json(
    GameStarted(
      game_id=session.game_id,
      agent=AgentBrief(id=agent.info.id, name=agent.info.name),
      state=_state_message(session),
    ).model_dump()
  )

  if session.state.to_move != human_side:
    await _play_agent_turns(ws, session, telemetry)


async def _handle_new_match(
  ws: WebSocket,
  msg: ClientNewMatch,
  owner: int,
  sessions: SessionStore,
  telemetry: Telemetry,
  client_hash: str | None,
) -> None:
  try:
    south_agent: Agent = get_agent(msg.south_agent_id, seed=msg.seed)
  except KeyError:
    await ws.send_json(
      ErrorMessage(
        code="unknown_agent",
        message=f"no such agent: {msg.south_agent_id}",
      ).model_dump()
    )
    return
  try:
    north_agent: Agent = get_agent(
      msg.north_agent_id,
      seed=(msg.seed + 1) if msg.seed is not None else None,
    )
  except KeyError:
    await ws.send_json(
      ErrorMessage(
        code="unknown_agent",
        message=f"no such agent: {msg.north_agent_id}",
      ).model_dump()
    )
    return

  session = sessions.create(
    owner=owner,
    agent=south_agent,
    north_agent=north_agent,
    human_side=None,
    state=initial_state(),
    seed=msg.seed,
    client_id_hash=client_hash,
    step_delay_ms=msg.step_delay_ms,
  )
  telemetry.record_game_start(
    game_id=session.game_id,
    agent_id=south_agent.info.id,
    opponent_kind="agent",
    opponent_agent_id=north_agent.info.id,
    human_plays=None,
    client_id_hash=client_hash,
    seed=msg.seed,
    initial_state=session.state,
  )

  await ws.send_json(
    GameStarted(
      game_id=session.game_id,
      agent=AgentBrief(id=south_agent.info.id, name=south_agent.info.name),
      north_agent=AgentBrief(id=north_agent.info.id, name=north_agent.info.name),
      state=_state_message(session),
    ).model_dump()
  )

  await _play_agent_turns(ws, session, telemetry)


async def _handle_move(
  ws: WebSocket,
  msg: ClientMove,
  owner: int,
  sessions: SessionStore,
  telemetry: Telemetry,
) -> None:
  session = sessions.get(owner=owner, game_id=msg.game_id)
  if session is None:
    await ws.send_json(
      ErrorMessage(
        code="unknown_game", message=f"no such game: {msg.game_id}"
      ).model_dump()
    )
    return
  if session.ended:
    await ws.send_json(
      ErrorMessage(code="game_over", message="game has already ended").model_dump()
    )
    return
  if session.state.to_move != session.human_side:
    await ws.send_json(
      ErrorMessage(code="not_your_turn", message="not the human's turn").model_dump()
    )
    return

  try:
    next_state, captured = step(session.state, msg.pit)
  except IllegalMoveError as e:
    await ws.send_json(ErrorMessage(code="illegal_move", message=str(e)).model_dump())
    return

  session.state = next_state
  session.last_move_pit = msg.pit
  session.last_move_by = session.human_side
  session.last_move_captured = captured
  session.moves.append({
    "ply": next_state.ply - 1,
    "by": _side_name(session.human_side),
    "pit": msg.pit,
    "captured": captured,
  })
  telemetry.record_move(
    game_id=session.game_id,
    ply=next_state.ply - 1,
    side=_side_name(session.human_side),
    actor="human",
    action=msg.pit,
    captured=captured,
    state_after=next_state,
    thought_ms=None,
    agent_extras=None,
  )

  await ws.send_json(_state_message(session).model_dump())

  if await _maybe_finish(ws, session, telemetry):
    return
  await _play_agent_turns(ws, session, telemetry)


async def _handle_resign(
  ws: WebSocket,
  msg: ClientResign,
  owner: int,
  sessions: SessionStore,
  telemetry: Telemetry,
) -> None:
  session = sessions.get(owner=owner, game_id=msg.game_id)
  if session is None or session.ended:
    return
  session.ended = True
  winner = "north" if session.human_side == SOUTH else "south"
  telemetry.record_game_end(
    game_id=session.game_id,
    winner=winner,
    end_reason="resign",
    final_stores=session.state.stores,
    total_plies=session.state.ply,
  )
  await ws.send_json(
    GameOver(
      game_id=session.game_id,
      winner=winner,  # type: ignore[arg-type]
      reason="resign",
      final_stores=Stores(south=session.state.stores[0], north=session.state.stores[1]),
    ).model_dump()
  )


async def _play_agent_turns(
  ws: WebSocket, session: GameSession, telemetry: Telemetry
) -> None:
  is_match = session.human_side is None
  while not session.ended and (
    is_match or session.state.to_move != session.human_side
  ):
    mover_side = session.state.to_move
    agent_for_turn = session.agent_for_side(mover_side)

    await ws.send_json(
      AgentThinking(game_id=session.game_id, since=int(time.time() * 1000)).model_dump()
    )
    t0 = time.perf_counter()
    action, extras = await asyncio.to_thread(agent_for_turn.choose_move, session.state)
    thought_ms = int((time.perf_counter() - t0) * 1000)

    try:
      next_state, captured = step(session.state, action)
    except IllegalMoveError as e:
      await ws.send_json(
        ErrorMessage(
          code="agent_bug", message=f"agent chose illegal move: {e}"
        ).model_dump()
      )
      return

    session.state = next_state
    session.last_move_pit = action
    session.last_move_by = mover_side
    session.last_move_captured = captured
    session.moves.append({
      "ply": next_state.ply - 1,
      "by": _side_name(mover_side),
      "pit": action,
      "captured": captured,
    })
    telemetry.record_move(
      game_id=session.game_id,
      ply=next_state.ply - 1,
      side=_side_name(mover_side),
      actor="agent",
      action=action,
      captured=captured,
      state_after=next_state,
      thought_ms=thought_ms,
      agent_extras=extras,
    )

    await ws.send_json(
      AgentMove(
        game_id=session.game_id,
        pit=action,
        thought_ms=thought_ms,
        extras=extras,
      ).model_dump()
    )
    await ws.send_json(_state_message(session).model_dump())

    if await _maybe_finish(ws, session, telemetry):
      return

    if is_match and session.step_delay_ms > 0:
      await asyncio.sleep(session.step_delay_ms / 1000)


async def _maybe_finish(
  ws: WebSocket, session: GameSession, telemetry: Telemetry
) -> bool:
  done, winner, reason = _determine_winner(session.state)
  if not done:
    return False
  session.ended = True
  telemetry.record_game_end(
    game_id=session.game_id,
    winner=winner,
    end_reason=reason,
    final_stores=session.state.stores,
    total_plies=session.state.ply,
  )
  # Send game_over immediately with plain history (no hints yet)
  history = [dict(m) for m in session.moves]
  await ws.send_json(
    GameOver(
      game_id=session.game_id,
      winner=winner,  # type: ignore[arg-type]
      reason=reason,  # type: ignore[arg-type]
      final_stores=Stores(south=session.state.stores[0], north=session.state.stores[1]),
      history=history,
    ).model_dump()
  )
  # Compute AZ hints asynchronously and send as a follow-up message
  asyncio.create_task(_send_analysis(ws, session, history))
  return True


async def _send_analysis(ws: WebSocket, session: GameSession, history: list[dict]) -> None:
  enriched = await _compute_history_with_hints(session, history)
  try:
    await ws.send_json(
      GameAnalysis(game_id=session.game_id, history=enriched).model_dump()
    )
  except Exception:
    pass
  hint_pairs = [(e["ply"], e["az_hint"]) for e in enriched if "az_hint" in e]
  if hint_pairs:
    session_telemetry: Telemetry = ws.app.state.telemetry  # type: ignore[attr-defined]
    session_telemetry.record_hints(game_id=session.game_id, hints=hint_pairs)


async def _compute_history_with_hints(session: GameSession, history: list[dict]) -> list[dict]:
  try:
    from oware.agents.registry import get_agent as _get
    az = _get("az")
  except KeyError:
    return history

  # Replay game to get state at each ply, cap at 60 to bound latency
  capped = history[:60]

  def _replay():
    s = initial_state()
    for entry in capped:
      try:
        hint_action, _ = az.choose_move(s)
        entry["az_hint"] = hint_action
        s, _ = step(s, entry["pit"])
      except Exception:
        break

  await asyncio.to_thread(_replay)
  return history


app = create_app()
