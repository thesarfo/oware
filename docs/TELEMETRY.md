# Telemetry & Persistence

Every game played on the server — human-vs-agent or agent-vs-agent eval — is logged to a single SQLite database. The same schema feeds three downstream uses:

1. **Agent performance tracking** — winrates, Elo, regressions after a new checkpoint promotes.
2. **Human play analytics** — opening distributions, accuracy vs. an oracle, where humans tend to blunder, average game length.
3. **Replay & debugging** — any past game can be reconstructed move-by-move from the `moves` table alone.

## Why SQLite

- One file on disk, no daemon, no ops. Volume-mount it like the artifacts dir.
- Writes are tiny (~100 bytes per move, ~50 moves per game → 5 KB/game). A million games is 5 GB; we will not hit this.
- WAL mode handles a single writer + many readers comfortably. Our server is one process, so one writer is what we have.
- Migrating to Postgres later is mechanical — the schema below uses only portable types.

The one limitation worth flagging: if we ever scale to multiple server processes (horizontal pod autoscaling) we'll need to move to Postgres because SQLite's single-writer model breaks across processes. Not a v1 concern.

## Schema

```sql
-- One row per session/game.
CREATE TABLE games (
    game_id            TEXT PRIMARY KEY,         -- e.g. "g_01HXYZ..."
    created_at         INTEGER NOT NULL,         -- unix epoch ms
    ended_at           INTEGER,                  -- null while in progress
    agent_id           TEXT NOT NULL,            -- "minimax-d4" | "dqn-step-500k" | ...
    agent_checkpoint   TEXT,                     -- artifact path or null for non-NN
    opponent_kind      TEXT NOT NULL,            -- "human" | "agent" (for eval matches)
    opponent_agent_id  TEXT,                     -- set when opponent_kind = 'agent'
    human_plays        TEXT,                     -- "south" | "north" | null for agent-vs-agent
    client_id_hash     TEXT,                     -- sha256(session_cookie+salt), 16 chars, or null
    seed               INTEGER,                  -- agent rng seed, for replay
    initial_state_json TEXT NOT NULL,            -- so we can replay even if rules change
    winner             TEXT,                     -- "south" | "north" | "draw" | null while ongoing
    end_reason         TEXT,                     -- "majority" | "must_feed" | "no_progress" | "resign" | "disconnect"
    final_store_south  INTEGER,
    final_store_north  INTEGER,
    total_plies        INTEGER,
    schema_version     INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX idx_games_agent_id ON games(agent_id);
CREATE INDEX idx_games_created_at ON games(created_at);
CREATE INDEX idx_games_ended_at ON games(ended_at) WHERE ended_at IS NOT NULL;

-- One row per move, in order.
CREATE TABLE moves (
    game_id            TEXT NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
    ply                INTEGER NOT NULL,         -- 0-indexed
    side               TEXT NOT NULL,            -- "south" | "north"
    actor              TEXT NOT NULL,            -- "human" | "agent"
    action             INTEGER NOT NULL,         -- pit 0..5 from side's perspective
    captured           INTEGER NOT NULL,
    pits_after_json    TEXT NOT NULL,            -- 12-int array as JSON
    store_south_after  INTEGER NOT NULL,
    store_north_after  INTEGER NOT NULL,
    thought_ms         INTEGER,                  -- wall-clock spent deciding (null for human if we don't time them)
    agent_extras_json  TEXT,                     -- search depth, nodes, mcts visit counts, top-k Q-values, ...
    PRIMARY KEY (game_id, ply)
);

CREATE INDEX idx_moves_game_id ON moves(game_id);

-- Tournament results, written by the eval runner. Optional — uses the same games/moves tables for the actual games.
CREATE TABLE eval_runs (
    run_id        TEXT PRIMARY KEY,
    started_at    INTEGER NOT NULL,
    ended_at      INTEGER,
    config_json   TEXT NOT NULL,   -- which agents, how many games, etc.
    notes         TEXT
);

CREATE TABLE elo_ratings (
    run_id        TEXT NOT NULL REFERENCES eval_runs(run_id) ON DELETE CASCADE,
    agent_id      TEXT NOT NULL,
    rating        REAL NOT NULL,
    games_played  INTEGER NOT NULL,
    PRIMARY KEY (run_id, agent_id)
);
```

`schema_version` on `games` lets us version-gate future migrations without touching past rows.

## What gets logged when

- **`new_game`** received → INSERT into `games` with `ended_at=NULL`, store the initial state JSON.
- **Each move** (human or agent) → INSERT into `moves`. The pit/store snapshot lets us answer "what did the board look like at ply N?" without re-running the engine.
- **Game ends** (any `end_reason`) → UPDATE `games` SET `ended_at`, `winner`, `final_store_*`, `total_plies`, `end_reason`.
- **Disconnect mid-game** → after the 60s reconnect grace period expires, UPDATE `games` SET `end_reason='disconnect'`, `ended_at=now()`, `winner=NULL`.

Writes happen on a background `asyncio.Task` consuming from a `asyncio.Queue`, so a slow disk fsync never blocks a player's move ack. WAL mode + `synchronous=NORMAL` is fine here — at worst we lose the last few moves on a crash, and the in-memory game state stays authoritative until the game ends.

## Multi-session implications

The schema does not change for multi-session — `game_id` already disambiguates. What needs to change on the **server** side:

- The session dict is keyed by `game_id`, which we already do.
- Each WebSocket connection holds a list of `game_ids` it owns (set on `new_game`, checked on every `move`/`resign`). Reject messages for `game_id`s not owned by this socket.
- LRU cap: e.g. 10k concurrent games per process; evict the least-recently-active completed game. Active (`ended_at IS NULL`) games are never evicted; if we hit the cap with all active, reject new games with a 503.
- A `client_id_hash` (`sha256(session_cookie + server_salt)[:16]`) is set on the connection from a `Set-Cookie` issued on first HTTP handshake. Same human across sessions gets a consistent hash; no PII.

## Privacy & consent

- We hash the client identifier with a server-side salt so the database never holds a value that maps back to a person.
- Show a one-line notice in the UI footer: "Games are logged anonymously to improve the AI." Link to a short data-use page.
- Provide a `DELETE /me` endpoint that takes the client cookie and removes all rows with the matching `client_id_hash`. Trivial to implement; important for GDPR-style compliance even if we never expect EU traffic.
- Eval matches (agent-vs-agent) have `client_id_hash=NULL` — nothing personal to protect there.

## Useful queries

```sql
-- Agent winrate vs. humans, last 30 days.
SELECT agent_id,
       SUM(CASE WHEN winner = human_plays THEN 0
                WHEN winner = 'draw' THEN 0.5
                ELSE 1 END) * 1.0 / COUNT(*) AS agent_winrate,
       COUNT(*) AS games
FROM games
WHERE opponent_kind = 'human'
  AND ended_at IS NOT NULL
  AND created_at > strftime('%s','now','-30 days') * 1000
GROUP BY agent_id
ORDER BY agent_winrate DESC;

-- Human opening-move distribution (first move played by the human, when human plays south).
SELECT m.action, COUNT(*) AS n
FROM games g
JOIN moves m ON m.game_id = g.game_id AND m.ply = 0
WHERE g.opponent_kind = 'human' AND g.human_plays = 'south'
GROUP BY m.action
ORDER BY n DESC;

-- Average plies per game by agent.
SELECT agent_id, AVG(total_plies) AS avg_plies, COUNT(*) AS games
FROM games
WHERE ended_at IS NOT NULL
GROUP BY agent_id;

-- Replay a specific game.
SELECT ply, side, action, captured, pits_after_json
FROM moves WHERE game_id = ? ORDER BY ply;
```

## Migrations

- Migrations live in `src/oware/server/migrations/NNNN_*.sql`.
- On server boot, run pending migrations inside a transaction.
- We use `schema_version` on `games` rather than a global Alembic-style version because most migrations will be additive (new columns default to NULL) and the engine can read mixed-version rows safely.

## Retention

- Keep all eval rows forever — they're tiny and define agent strength history.
- Keep human-played games for 90 days by default. A nightly job deletes `games` (and cascades to `moves`) older than that with `opponent_kind = 'human'`. Configurable via env var; can be disabled for personal/dev instances.

## File location

- `artifacts/telemetry.db` for dev.
- In docker-compose, mounted at `/data/telemetry.db` on a named volume so a container rebuild doesn't lose history.
