# Project: Oware Mancala

A web platform for playing Oware against a ladder of AI agents (Random → Minimax → DQN → PPO → AlphaZero-lite).

## Required reading before touching code

**`docs/CLEAN_CODE.md` is the zen of this project.** Read it before writing or reviewing any code. If a rule there conflicts with what you're about to do, the rule wins until the exception is justified out loud.

## Doc index

All planning lives in [docs/](docs/):

- [PLAN.md](docs/PLAN.md) — top-level project plan, goals, repo layout.
- [CLEAN_CODE.md](docs/CLEAN_CODE.md) — **the zen; always referenced.**
- [GAME_SPEC.md](docs/GAME_SPEC.md) — Abapa rules, edge cases, worked examples.
- [TEST_PLAN.md](docs/TEST_PLAN.md) — engine test strategy and coverage matrix.
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — server, agents, sessions, concurrency.
- [WS_PROTOCOL.md](docs/WS_PROTOCOL.md) — WebSocket message schemas.
- [TELEMETRY.md](docs/TELEMETRY.md) — SQLite schema, analytics, privacy.
- [RL_APPROACHES.md](docs/RL_APPROACHES.md) — DQN, PPO, AlphaZero design.
- [TRAINING.md](docs/TRAINING.md) — TensorBoard + tqdm conventions, run reproducibility.
- [ROADMAP.md](docs/ROADMAP.md) — milestones and risks.

## House rules (quick summary; full version in CLEAN_CODE.md)

- Do less. No premature abstraction, no speculative generality, no half-finished work.
- The engine is pure, immutable, deterministic. Stateless functions on immutable `State`.
- Validate at boundaries; trust internal types. No defensive nulls inside the engine or agents.
- Every stochastic component takes a seed. Games must be replay-deterministic.
- Tests are not optional. Engine coverage ≥ 95%. Bug fixes ship with a regression test.
- Single `Agent` protocol for every agent family. The server never special-cases an agent.
- WebSocket protocol and SQLite schema are additive-only after first launch.

## Stack

- Python ≥3.13, `uv` for env/deps.
- FastAPI + WebSockets for the server.
- PyTorch for NN agents.
- SQLite for telemetry (`artifacts/telemetry.db`).
- React + Vite + TypeScript + Tailwind for the frontend.

## Commands

- `uv run pytest` — engine + server tests.
- `uv run pytest tests/engine -q --cov=src/oware/engine --cov-fail-under=95` — engine CI gate.
- `uv run python -m oware.server` — start the dev server.
- `uv run python -m oware.agents.<family>.train --config configs/<family>_v1.yaml` — training.
