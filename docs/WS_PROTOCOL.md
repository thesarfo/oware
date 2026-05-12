# WebSocket Protocol

All messages are JSON with a top-level `type` discriminator. Server is authoritative — clients send intents, server publishes resulting state.

## Client → server

### `new_game`

```json
{
  "type": "new_game",
  "agent_id": "minimax-d4",
  "human_plays": "south",
  "seed": 42
}
```

- `human_plays`: `"south"` (moves first) or `"north"`.
- `seed`: optional; only meaningful for stochastic agents.

### `move`

```json
{ "type": "move", "game_id": "g_abc123", "pit": 3 }
```

- `pit` is 0–5 from the **human's perspective**. Server validates legality and rejects illegal moves with an `error`.

### `resign`

```json
{ "type": "resign", "game_id": "g_abc123" }
```

### `ping`

```json
{ "type": "ping", "t": 1715500000000 }
```

## Server → client

### `game_started`

```json
{
  "type": "game_started",
  "game_id": "g_abc123",
  "agent": { "id": "minimax-d4", "name": "Minimax (depth 4)" },
  "state": { ... see `state` ... }
}
```

### `state`

Authoritative snapshot after any state change.

```json
{
  "type": "state",
  "game_id": "g_abc123",
  "pits": [4,4,4,4,4,4, 4,4,4,4,4,4],
  "stores": { "south": 0, "north": 0 },
  "to_move": "south",
  "ply": 0,
  "legal_moves": [0,1,2,3,4,5],
  "last_move": null
}
```

- `last_move`: `{ "by": "south", "pit": 2, "captured": 0 }` or `null` for the opening state.
- Pits are always in **absolute** coordinates (0–5 south, 6–11 north); the client rotates for display if the human is north.

### `agent_thinking`

```json
{ "type": "agent_thinking", "game_id": "g_abc123", "since": 1715500000123 }
```

Sent immediately when it becomes the agent's turn so the UI can show a spinner. Useful when MCTS takes ~800 ms.

### `agent_move`

Sent right before the resulting `state`, carrying any introspection the agent wants to expose (purely cosmetic — UI can ignore).

```json
{
  "type": "agent_move",
  "game_id": "g_abc123",
  "pit": 4,
  "thought_ms": 612,
  "extras": { "search_depth": 6, "nodes": 248311 }
}
```

### `game_over`

```json
{
  "type": "game_over",
  "game_id": "g_abc123",
  "winner": "south",       // "south" | "north" | "draw"
  "reason": "majority",    // "majority" | "must_feed" | "no_progress" | "resign"
  "final_stores": { "south": 28, "north": 20 }
}
```

### `error`

```json
{ "type": "error", "code": "illegal_move", "message": "pit 1 is empty" }
```

Non-fatal; the connection stays open.

## Connection lifecycle

1. Client opens WS to `/play`.
2. Sends `new_game`. Server responds with `game_started` + initial `state`.
3. If human moves first: client sends `move`; server responds with `state`, then (if agent's turn) `agent_thinking` → `agent_move` → `state`.
4. Loop until `game_over`.
5. Client may immediately send a new `new_game` over the same socket.

Heartbeat: server sends a `ping` every 20 s; if no pong within 10 s, it drops the socket and the session.
