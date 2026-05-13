import sqlite3

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
  db = tmp_path / "telemetry.db"
  monkeypatch.setenv("OWARE_DB", str(db))
  from oware.server import app as app_module

  app_module.DB_PATH = db
  app_module.app = app_module.create_app()
  with TestClient(app_module.app) as c:
    yield c, db


def _recv_until(ws, predicate):
  while True:
    msg = ws.receive_json()
    if predicate(msg):
      return msg


def test_agents_endpoint_includes_random(client):
  c, _ = client
  r = c.get("/agents")
  assert r.status_code == 200
  ids = [a["id"] for a in r.json()]
  assert "random" in ids


def test_full_random_game_ends(client):
  c, db_path = client
  with c.websocket_connect("/play") as ws:
    ws.send_json(
      {
        "type": "new_game",
        "agent_id": "random",
        "human_plays": "south",
        "seed": 0,
      }
    )
    started = ws.receive_json()
    assert started["type"] == "game_started"
    game_id = started["game_id"]

    for _ in range(2000):
      state = started["state"] if started["type"] == "game_started" else None
      if state is None:
        state = _recv_until(ws, lambda m: m["type"] == "state")
      if not state["legal_moves"]:
        break
      if state["to_move"] != "south":
        started = ws.receive_json()
        continue
      ws.send_json({"type": "move", "game_id": game_id, "pit": state["legal_moves"][0]})
      msg = ws.receive_json()
      if msg["type"] == "game_over":
        break
      if msg["type"] == "state":
        started = {"type": "state", "state": msg}
        if msg.get("legal_moves") == []:
          break
        if msg["to_move"] == "south":
          started = {"type": "state", "state": msg}
          continue
        started = {"type": "agent_turn", "state": msg}
        continue
    else:
      pytest.fail("game did not terminate")


def test_illegal_move_returns_error_but_keeps_connection(client):
  c, _ = client
  with c.websocket_connect("/play") as ws:
    ws.send_json({"type": "new_game", "agent_id": "random", "seed": 0})
    ws.receive_json()
    ws.send_json({"type": "move", "game_id": "g_does_not_exist", "pit": 0})
    err = ws.receive_json()
    assert err["type"] == "error"
    assert err["code"] == "unknown_game"


def test_unknown_agent_returns_error(client):
  c, _ = client
  with c.websocket_connect("/play") as ws:
    ws.send_json({"type": "new_game", "agent_id": "nope"})
    err = ws.receive_json()
    assert err["type"] == "error"
    assert err["code"] == "unknown_agent"


def test_game_written_to_telemetry(client):
  c, db_path = client
  with c.websocket_connect("/play") as ws:
    ws.send_json({"type": "new_game", "agent_id": "random", "seed": 0})
    started = ws.receive_json()
    game_id = started["game_id"]
    ws.send_json({"type": "resign", "game_id": game_id})
    over = ws.receive_json()
    assert over["type"] == "game_over"
    assert over["reason"] == "resign"

  import time

  for _ in range(50):
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
      "SELECT game_id, end_reason FROM games WHERE game_id = ?", (game_id,)
    ).fetchall()
    conn.close()
    if rows and rows[0][1] == "resign":
      return
    time.sleep(0.05)
  pytest.fail("telemetry row not written within timeout")


def test_agents_endpoint_includes_minimax(client):
  c, _ = client
  r = c.get("/agents")
  ids = [a["id"] for a in r.json()]
  assert "minimax_d2" in ids
  assert "minimax_d4" in ids
  assert "minimax_d6" in ids
  families = {a["id"]: a["family"] for a in r.json()}
  assert families["minimax_d2"] == "minimax"


def test_minimax_d2_game_ends(client):
  """A full game vs minimax_d2 must complete without error."""
  c, _ = client
  with c.websocket_connect("/play") as ws:
    ws.send_json(
      {
        "type": "new_game",
        "agent_id": "minimax_d2",
        "human_plays": "south",
        "seed": 1,
      }
    )
    msg = ws.receive_json()
    assert msg["type"] == "game_started"
    game_id = msg["game_id"]
    state = msg["state"]

    for _ in range(500):
      while state["to_move"] != "south":
        msg = ws.receive_json()
        if msg["type"] == "game_over":
          return
        if msg["type"] == "state":
          state = msg
      if not state["legal_moves"]:
        break
      ws.send_json({"type": "move", "game_id": game_id, "pit": state["legal_moves"][0]})
      msg = ws.receive_json()
      if msg["type"] == "game_over":
        return
      if msg["type"] == "state":
        state = msg
    else:
      pytest.fail("minimax_d2 game did not terminate")
