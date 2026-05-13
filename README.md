# Oware

Play Oware (Abapa ruleset) against a ladder of AI agents — from a random baseline up to an AlphaZero-lite agent trained via MCTS self-play.

## Quick start

```bash
# Install dependencies
uv sync

# Start the server
uv run python -m oware.server

# In a separate terminal, start the frontend
cd web && npm install && npm run dev
```

Open <http://localhost:5173> in your browser.

## Training agents

Each agent family has its own training script. Checkpoints are saved to `artifacts/`.

```bash
# DQN (~hours on CPU, ~30 min on GPU)
uv run python -m oware.agents.dqn.train

# PPO (~hours on CPU, ~1 hour on GPU, 8 parallel envs)
uv run python -m oware.agents.ppo.train

# AlphaZero-lite (~1-2 days on CPU, ~hours on GPU, concurrent self-play + trainer)
uv run python -m oware.agents.az.train

# Monitor training
uv run tensorboard --logdir artifacts/tb
```

Once a checkpoint exists at `artifacts/<family>/latest.pt`, the agent appears automatically in the UI.

## Evaluating agents

```bash
uv run python scripts/eval_dqn.py   # >=99% vs Random, >=70% vs Minimax-d2
uv run python scripts/eval_ppo.py   # >=80% vs Minimax-d2, >=55% vs Minimax-d4
uv run python scripts/eval_az.py    # >=55% vs Minimax-d6
```

## Tournament + Elo

```bash
uv run python scripts/tournament.py
```

Plays all present agents round-robin (100 games per pair) and writes `artifacts/elo.json`. The server reads this file at startup and shows Elo ratings in the agent picker.

## Running tests

```bash
uv run pytest
uv run pytest tests/engine -q --cov=src/oware/engine --cov-fail-under=95
```

## Architecture

See [`docs/`](docs/) for full design documents:

- [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) — server, agents, sessions
- [`GAME_SPEC.md`](docs/GAME_SPEC.md) — Abapa rules and edge cases
- [`RL_APPROACHES.md`](docs/RL_APPROACHES.md) — DQN, PPO, AlphaZero design
- [`WS_PROTOCOL.md`](docs/WS_PROTOCOL.md) — WebSocket message schemas
- [`ROADMAP.md`](docs/ROADMAP.md) — milestones
