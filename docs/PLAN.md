# Oware Mancala — Project Plan

A web-based Oware (Awalé) platform where humans play against a ladder of AI agents in real time. Agents range from a classical Minimax/Alpha-Beta baseline up to deep RL agents trained via DQN, PPO, and an AlphaZero-style MCTS+NN self-play loop.

## Goals

1. **Playable product**: a polished web UI where a human can pick an opponent (Random / Minimax-depth-N / DQN / PPO / AlphaZero) and play a full game over a WebSocket connection.
2. **Correct engine**: a fast, well-tested Oware rules engine (canonical rules + grand-slam rule + cycle detection) usable as a Python library and as a `gymnasium` environment.
3. **Agent ladder**: at least one agent at each tier — heuristic, classical search, and three RL families — exposed behind a single `Agent.choose_move(state) -> action` interface.
4. **Reproducible training**: configs, seeds, checkpoints, and eval reports versioned; trained weights round-trip into the serving runtime.
5. **Strength measurement**: agents ranked against each other and against fixed-depth Minimax baselines via Elo from round-robin tournaments.

## Non-goals (for v1)

- Mobile-native apps, accounts/auth, persistent match history, multiplayer human-vs-human matchmaking, monetization. The web UI is single-player vs. AI.
- Distributed/multi-GPU training. Single-GPU (or CPU for DQN/MCTS-lite) is enough for a research-grade result on a board this small.
- Beating top published Oware engines. We aim for "clearly stronger than depth-6 Minimax," not state-of-the-art.

## High-level architecture

```text
┌────────────────┐    WebSocket (JSON)    ┌──────────────────────┐
│  Web client    │ ─────────────────────► │  FastAPI gateway     │
│  (React + TS)  │ ◄───────────────────── │  (game session mgr)  │
└────────────────┘                        └──────────┬───────────┘
                                                     │
                                          ┌──────────▼───────────┐
                                          │  Agent registry      │
                                          │  ├─ Random           │
                                          │  ├─ Minimax/AB       │
                                          │  ├─ DQN (torch)      │
                                          │  ├─ PPO (torch)      │
                                          │  └─ AlphaZero (MCTS) │
                                          └──────────┬───────────┘
                                                     │
                                          ┌──────────▼───────────┐
                                          │  Oware engine        │
                                          │  (pure Python core)  │
                                          └──────────────────────┘
```

Training jobs run **offline** against the same engine, write checkpoints to `artifacts/`, and the gateway hot-loads the latest checkpoint per agent at startup.

## Repo layout (target)

```text
oware/
├── docs/                       # this folder
├── src/oware/
│   ├── engine/                 # rules, board repr, move gen, terminal detection
│   ├── env/                    # gymnasium env wrapper
│   ├── agents/
│   │   ├── base.py             # Agent protocol
│   │   ├── random_agent.py
│   │   ├── minimax.py          # alpha-beta + iterative deepening + TT
│   │   ├── dqn/                # network, replay, trainer, inference
│   │   ├── ppo/                # actor-critic, rollout buffer, trainer
│   │   └── alphazero/          # MCTS, policy-value net, self-play loop
│   ├── server/                 # FastAPI app, WS handlers, session store
│   └── eval/                   # tournament runner, Elo, reports
├── web/                        # React + Vite frontend
├── artifacts/                  # checkpoints, eval reports (gitignored)
├── configs/                    # training/eval YAMLs
└── tests/
```

## Phased roadmap

See [ROADMAP.md](ROADMAP.md) for milestone breakdown. Short version:

1. **M1 — Engine + tests** (week 1): correct rules, move gen, terminal detection, ≥95% line coverage on rules.
2. **M2 — Server + UI skeleton** (week 2): FastAPI WS, React board, play vs. Random agent end-to-end.
3. **M3 — Classical baseline** (week 2–3): alpha-beta minimax with heuristic eval; depths 2/4/6 selectable from UI.
4. **M4 — Gym env + DQN** (week 3–4): wrap engine, train DQN against Random + self-play, ship checkpoint.
5. **M5 — PPO** (week 4–5): actor-critic with action masking, league play vs. previous snapshots.
6. **M6 — AlphaZero-lite** (week 5–7): MCTS + small ResNet, self-play loop, periodic evaluator.
7. **M7 — Tournament + UI polish** (week 7–8): Elo ladder visible in UI, post-game analysis, agent selector with strength estimates.

## Key design decisions to lock early

- **State representation**: 14-int vector (12 pits + 2 stores) plus side-to-move and ply counter. Same tensor shape feeds every NN agent.
- **Action space**: 6 discrete actions (pits 0–5 from the side to move's perspective); illegal moves masked via the policy head / Q-mask.
- **Reward**: terminal-only, `+1` win / `0` draw / `-1` loss. Intermediate seed captures are *not* rewarded — that's what shaped Minimax and we want the RL agents to discover the deeper strategy themselves.
- **Self-play opponents**: maintain a snapshot pool (last N checkpoints + Minimax depth 4) and sample uniformly to avoid policy collapse.
- **Determinism**: every agent takes a seed; the server records `(initial_state, move_list, seed)` so any game is replayable.

## Open questions (decide before M4)

- Cycle / repetition rule variant — strict "no-capture for X moves → split remaining seeds" or the simpler 200-ply cap? See [GAME_SPEC.md](GAME_SPEC.md).
- Inference budget per move in the served UI — fixed wall-clock (e.g. 500 ms) or fixed MCTS sims? Affects perceived agent strength and UX pacing.
- Frontend stack: Vite + React + Tailwind is the default; revisit if we want SSR.

## Cross-references

- [CLEAN_CODE.md](CLEAN_CODE.md) — **the zen; read before every code change.**
- [GAME_SPEC.md](GAME_SPEC.md) — exact Abapa rules, edge cases, worked examples.
- [TEST_PLAN.md](TEST_PLAN.md) — engine test strategy, coverage matrix, property tests.
- [ARCHITECTURE.md](ARCHITECTURE.md) — server, WS protocol, agent interface.
- [WS_PROTOCOL.md](WS_PROTOCOL.md) — WebSocket message schemas.
- [TELEMETRY.md](TELEMETRY.md) — SQLite schema, multi-session model, analytics queries, privacy.
- [RL_APPROACHES.md](RL_APPROACHES.md) — DQN, PPO, AlphaZero design details.
- [TRAINING.md](TRAINING.md) — TensorBoard layout, tqdm conventions, run reproducibility.
- [ROADMAP.md](ROADMAP.md) — milestones, deliverables, risks.
