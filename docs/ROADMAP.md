# Roadmap

Eight rough weeks. Treat as a sequencing guide, not a schedule — slip the dates, keep the order.

## M1 — Engine + tests (week 1)

**Deliverable**: `src/oware/engine/` with `initial_state`, `legal_moves`, `step`, `terminal`, `encode`. ≥95% branch coverage on rules.

- Encode board as immutable `State` dataclass.
- Implement sowing with source-pit skip.
- Implement capture walk-back including grand-slam refusal.
- Implement must-feed legal-move filter.
- Implement game-end (majority, must-feed-no-moves, no-progress cap).
- Tests from the worked examples in [GAME_SPEC.md](GAME_SPEC.md) + property tests:
  - Seed conservation: total seeds in pits + stores always = 48.
  - Legal-move list is non-empty unless game is over.
  - `encode` is canonical (same position from either perspective produces matching tensors after color flip).

**Done when**: `pytest` is green and a Random-vs-Random self-play loop runs 10k games without raising.

## M2 — Server + UI skeleton (week 2)

**Deliverable**: Play a full Oware game in the browser against a Random agent over WebSocket.

- FastAPI app, `/agents` and `/play` endpoints from [WS_PROTOCOL.md](WS_PROTOCOL.md).
- In-memory session manager keyed by `game_id`.
- React + Vite frontend: agent picker, board, history strip, capture counters.
- Random agent registered, selectable from UI.

**Done when**: a human can pick "Random", play to completion, and see "Game over — you win" (or lose, the agent is bad).

## M3 — Classical baseline (week 2–3)

**Deliverable**: Minimax with alpha-beta, iterative deepening, transposition table, and a heuristic eval. Selectable at depths 2 / 4 / 6 from the UI.

- Heuristic: `own_store - opp_store + 0.5*(own_mobility - opp_mobility) + small bonus for seeds in defensible far pits`.
- Iterative deepening with a wall-clock budget so the server can always respond on time.
- Transposition table keyed by Zobrist hash of the state.
- Smoke benchmark: depth-6 average move time < 800 ms on a laptop CPU.

**Done when**: Minimax-d6 beats Minimax-d2 ≥90% over 100 games.

## M4 — Gym env + DQN (week 3–4)

**Deliverable**: `OwareEnv` gymnasium env; a trained DQN checkpoint that beats Random ≥99% and Minimax-d2 ≥70%.

- Gymnasium env with action masking exposed as part of the obs dict.
- DQN trainer per [RL_APPROACHES.md §1](RL_APPROACHES.md#1-dqn).
- TensorBoard logging.
- Agent runtime that loads `artifacts/dqn/latest.pt`.

**Done when**: UI ships a "DQN" option; checkpoint eval report committed.

## M5 — PPO (week 4–5)

**Deliverable**: PPO checkpoint that beats Minimax-d4 ≥55%.

- Vectorized self-play env (8 parallel workers).
- Action-masked policy head.
- League play with snapshot pool.
- Eval gate before promoting `latest.pt`.

**Done when**: UI ships a "PPO" option; PPO vs DQN tournament report exists.

## M6 — AlphaZero-lite (week 5–7)

**Deliverable**: MCTS agent with policy-value net that beats Minimax-d6 ≥55%.

- MCTS implementation (PUCT, Dirichlet root noise, temperature schedule).
- Tiny ResNet policy-value net.
- Self-play loop + trainer + evaluator (three processes, shared buffer on disk or via multiprocessing queue).
- Inference path that reuses the same MCTS but with no noise and lower temperature.

**Done when**: UI ships an "AlphaZero" option at 400 sims; eval report shows it beating PPO.

## M7 — Tournament + UI polish (week 7–8)

**Deliverable**: Public-facing demo.

- Round-robin tournament runner; Elo solver writes `artifacts/elo.json`.
- `/agents` endpoint exposes Elo to UI; agent picker shows strength.
- Post-game analysis pane: move list with capture annotations; optional "what would AlphaZero have played" hint replay.
- Mobile-responsive board layout.
- README + a short demo GIF.

**Done when**: a stranger can land on the site, pick an opponent, and finish a game without confusion.

## nice to have

- Spectator mode / live broadcast.
