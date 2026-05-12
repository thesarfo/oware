# Engine Test Plan

The engine is the foundation; everything else (gym env, agents, server, training) trusts it. We invest heavily here. Target: **≥95% branch coverage** on `src/oware/engine/` and **zero known rule deviations** from [GAME_SPEC.md](GAME_SPEC.md).

## Test framework

- `pytest` for unit + parameterized tests.
- `hypothesis` for property-based tests.
- A small set of "golden" recorded games (`tests/fixtures/golden/*.json`) — each is a sequence of `(state, action, expected_next_state, expected_captured)` triples used as regression guards.

## Layout

```text
tests/
├── engine/
│   ├── test_sowing.py          # raw sow mechanics
│   ├── test_captures.py        # capture + chain + grand-slam
│   ├── test_must_feed.py       # compulsory feeding rule
│   ├── test_legal_moves.py     # legal-move generator
│   ├── test_terminal.py        # end-of-game conditions
│   ├── test_encoding.py        # canonical obs encoding
│   └── test_properties.py      # hypothesis property tests
├── fixtures/
│   └── golden/
│       ├── random_vs_random_seed_0.json
│       └── handcrafted_capture_chain.json
└── conftest.py
```

## Unit tests (one per worked example in GAME_SPEC.md)

| Test ID  | Maps to | What it asserts |
|----------|---------|-----------------|
| T-EX1    | EX1     | Sow from initial pit 2 produces exactly `[4,4,0,5,5,5,5,4,4,4,4,4]`, stores unchanged, captured = 0 |
| T-EX2    | EX2     | Single capture: last seed lands in opp pit, total becomes 2, exactly 2 seeds go to mover's store |
| T-EX3    | EX3     | Chain capture totals 4 seeds; pits 6 and 7 are zeroed |
| T-EX4    | EX4     | Walkback stops at non-2/3; only 2 seeds captured |
| T-EX5    | EX5     | Final-seed-only rule: 2/3 created mid-sow does NOT capture |
| T-EX6    | EX6     | Grand-slam: capture is forfeited; sown seeds remain on the board; store unchanged |
| T-EX7    | EX7     | 12-seed sow skips source pit; final layout matches the spec |
| T-EX8    | EX8     | Must-feed forces a single legal move when opponent is empty |
| T-EX9    | EX9     | Must-feed-impossible ends the game and sweeps remaining seeds |
| T-EX10   | EX10    | Majority (≥25 in store) ends the game immediately |
| T-EX11   | EX11    | 100-ply no-capture cap ends the game; sweep applied; 24-24 → draw |

Each test constructs an explicit `State` (don't reach it through play — that hides bugs in `step`) and asserts on the post-`step` state, captured count, and `terminal()` flag.

## Coverage matrix for captures

Parameterized table covering the cells of the capture decision space.

| # | Final pit side | Final count | Walkback chain | Expected captured |
|---|----------------|-------------|----------------|-------------------|
| 1 | opponent       | 1           | n/a            | 0                 |
| 2 | opponent       | 2           | none           | 2                 |
| 3 | opponent       | 3           | none           | 3                 |
| 4 | opponent       | 4           | n/a            | 0                 |
| 5 | opponent       | 2           | [2]            | 4                 |
| 6 | opponent       | 2           | [3]            | 5                 |
| 7 | opponent       | 3           | [2, 3]         | 8                 |
| 8 | opponent       | 2           | [2, 4, ...]    | 2 (stops at 4)    |
| 9 | own side       | 2 or 3      | n/a            | 0 (own side)      |
| 10| opponent       | 2           | chain empties opp | 0 (grand-slam) |

## Property-based tests (`hypothesis`)

These run against random reachable states. Use a strategy that builds states via random self-play from `initial_state()` with a bounded ply count, so we never test impossible positions.

1. **Seed conservation**
   For any state `s` and legal action `a`: `sum(next.pits) + sum(next.stores) == 48` and equal to `sum(s.pits) + sum(s.stores)`.

2. **Non-negativity**
   All pit counts and store counts in any reachable state are ≥ 0.

3. **Turn alternation**
   After a non-terminal `step`, `to_move` flips. (Oware has no "play again" rule.)

4. **Legal-move soundness**
   For every `a` in `legal_moves(s)`, `step(s, a)` does not raise.

5. **Legal-move completeness**
   For every action `a` in `range(6)` not in `legal_moves(s)`, `step(s, a)` raises `IllegalMoveError` (or equivalent).

6. **Must-feed contract**
   If opponent has zero seeds and `legal_moves(s)` is non-empty, every returned move results in `sum(opp_pits_after) > 0`.

7. **Grand-slam invariant**
   After any `step`, the opponent's row is not all-zero **unless** the game is terminal (must-feed-impossible end).

8. **Capture bound**
   `captured ≤ 5 * 3 = 15` per move (max 5 houses × 3 seeds). Tighter: `captured ≤ sum_of_opp_row_before`.

9. **Encoding round-trip property**
   For two states that are identical up to color swap, `encode(s_south_to_move) == encode(color_flip(s_south_to_move))` after re-flipping. (Catches bugs in canonical-perspective encoding that would let the NN see different obs for the same strategic position.)

10. **Determinism**
    `step(s, a)` is a pure function. Calling it twice on the same inputs yields equal outputs and equal hashes.

## Golden game regression

Record one full random-vs-random game with `seed=0` and one handcrafted game that exercises a chain capture and a 12+ sow. Store as JSON. The regression test replays each game move-by-move and asserts each intermediate state matches.

Purpose: catches subtle off-by-one bugs introduced when refactoring the sow loop or the capture walkback. Cheap to maintain — regenerate goldens deliberately when rules change, never automatically.

## Cross-check against an external oracle (stretch)

For 50 random midgame positions, compare our `legal_moves` and `step` outputs against an independent reference implementation (e.g. a known-good Awari Python package, or a small hand-rolled JavaScript engine pulled from a public Oware site). Disagreements are bugs in one of the two — investigate every case.

This is a stretch goal because finding a reference implementation that uses the exact Abapa rules (with grand-slam forfeit) is not guaranteed; many online Oware engines use slightly different rule variants.

## Performance smoke tests

Not correctness, but worth catching regressions:

- `step` throughput: ≥ 500k calls/sec on a single core (we'll need this for MCTS).
- Random self-play game: average ≤ 2 ms wall-clock per game on a laptop CPU.

Run these as `pytest-benchmark` tests gated by an `--benchmark` flag so they don't slow normal CI.

## What we are NOT testing

- Server / WebSocket behavior — that's a different test file (`tests/server/`) gated by separate fixtures.
- Agent strength — measured by the eval tournament, not pytest.
- Training convergence — too slow and noisy for unit tests; we rely on the eval-vs-Minimax winrate metric instead.

## CI

- `uv run pytest tests/engine/ -q --cov=src/oware/engine --cov-fail-under=95` on every push.
- Hypothesis runs with the default profile in CI and a `--hypothesis-profile=thorough` profile (more examples, longer deadline) on the nightly job.
- Goldens are committed; a failing golden test produces a diff and a hint to regenerate only if the change was intentional.
