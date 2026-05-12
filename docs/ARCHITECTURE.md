# Architecture

## Components

### 1. Engine (`src/oware/engine/`)

Pure Python, no NumPy in the hot path for the rules (a list of 12 ints is faster than a tiny ndarray here). Public API:

```python
class State:
    pits: tuple[int, ...]    # length 12, immutable
    stores: tuple[int, int]
    to_move: int             # 0=south, 1=north
    ply: int
    plies_since_capture: int

def initial_state() -> State: ...
def legal_moves(s: State) -> list[int]: ...     # 0..5 from side-to-move view
def step(s: State, action: int) -> tuple[State, int]:  # returns (next_state, seeds_captured)
def terminal(s: State) -> tuple[bool, int]:     # (done, winner: -1 draw / 0 south / 1 north)
def encode(s: State) -> np.ndarray:             # canonical obs for NNs
```

The engine is **stateless** (functions on immutable `State`) so it's trivially thread/process-safe — important for MCTS rollouts and self-play workers.

### 2. Gymnasium env (`src/oware/env/`)

Wraps the engine as a single-agent env where the opponent is configurable (Random / Minimax / a frozen NN). For self-play training the env exposes a two-agent mode that yields trajectories for both sides.

### 3. Agents (`src/oware/agents/`)

```python
class Agent(Protocol):
    def choose_move(self, state: State, *, time_budget_ms: int | None = None) -> int: ...
    name: str
    metadata: dict   # checkpoint id, training step, eval Elo, ...
```

Every agent — heuristic, search, or neural — implements this. The server doesn't care which family it is.

### 4. Server (`src/oware/server/`)

FastAPI app with a single WebSocket endpoint and a tiny REST surface for listing agents.

- **REST**
  - `GET /agents` → `[{id, name, family, est_elo, description}]`
  - `GET /healthz`
- **WebSocket** `/play`
  - Client → server messages: `new_game`, `move`, `resign`, `ping`.
  - Server → client messages: `game_started`, `state`, `agent_thinking`, `agent_move`, `game_over`, `error`.

See [WS_PROTOCOL.md](WS_PROTOCOL.md) for payload schemas.

**Sessions & multi-game support**: live game state lives in an in-memory dict keyed by a server-issued `game_id`. The dict is process-wide — one server happily holds thousands of concurrent games (each is ~1 KB). Each WebSocket connection tracks the set of `game_id`s it owns and the server rejects messages for `game_id`s it doesn't own. An LRU cap (default 10k completed games in memory; active games are never evicted) bounds memory; if the cap is hit with all-active, new games are refused with a 503.

**Persistence**: every move and every game outcome is written to a SQLite database (`artifacts/telemetry.db`) on a background task. The in-memory dict remains authoritative during play; the DB is for analytics, replay, and surviving restarts. See [TELEMETRY.md](TELEMETRY.md) for the schema and write path.

### 5. Frontend (`web/`)

React + Vite + TypeScript + Tailwind. Single page:

- Agent picker (cards with name, family, estimated strength).
- Board component — 12 pits laid out in two rows + two stores. Click own pit to play; illegal pits are disabled.
- Move history strip, capture counters, "agent is thinking…" indicator.
- WebSocket client wraps the protocol in a `useGame()` hook.

State management: `useReducer` for the local game state + a small Zustand store for the WS connection. No need for Redux on a single-page game.

## Concurrency model

- One Python process per server instance. FastAPI handles WS concurrency via asyncio.
- Inference for NN agents happens in a **threadpool executor** (`asyncio.to_thread`) so a slow MCTS rollout doesn't block the event loop. CPU-bound torch inference releases the GIL during forward passes.
- Minimax is synchronous but bounded by an iterative-deepening time budget so the server can always respond within UX limits.

## Inference budget

Default per-move budgets exposed to UI:

| Agent           | Budget         | Notes                                         |
|-----------------|----------------|-----------------------------------------------|
| Random          | <1 ms          | trivially fast                                |
| Minimax-d2/4/6  | 50 / 200 / 800 ms | iterative deepening, alpha-beta, TT       |
| DQN             | ~5 ms          | single forward pass                           |
| PPO             | ~5 ms          | single forward pass, argmax over masked logits|
| AlphaZero       | 400–800 ms     | configurable MCTS sims (default 200)          |

These are also the UX pacing knob — too fast feels like the AI cheated, too slow loses the player.

## Training infra

- Training scripts live under `src/oware/agents/<family>/train.py`, invoked via `python -m oware.agents.dqn.train --config configs/dqn_v1.yaml`.
- Configs are YAML; resolved into typed dataclasses via `pydantic`.
- Checkpoints saved as `artifacts/<agent>/<run_id>/step_<N>.pt` + a `latest.pt` symlink the server reads.
- Eval runs (round-robin tournaments) produce `artifacts/eval/<date>_<run>.json` with per-pair win rates; an Elo solver computes ratings and writes `artifacts/elo.json`, which the `/agents` endpoint surfaces to the UI.

## Observability

- Structured logging (`structlog`) on the server with `game_id` and `client_id_hash` as bound keys.
- Per-move and per-game telemetry persisted to SQLite (see [TELEMETRY.md](TELEMETRY.md)). Agent winrate, opening distributions, Elo trends, and individual game replays all derive from this.
- Training: TensorBoard scalars, histograms, and sampled-game text — full layout in [TRAINING.md](TRAINING.md). tqdm bars for live terminal progress.
- No production-grade metrics stack in v1 — Prometheus/Grafana can layer on later by exporting counters from the same SQLite.

## Deployment shape

- `docker-compose up` brings up the FastAPI server and a static-served frontend on one port via a reverse proxy (Caddy or nginx).
- Training is **not** in the compose; it runs locally with `uv run`.
- Artifacts dir is volume-mounted so the server picks up new checkpoints on restart.
