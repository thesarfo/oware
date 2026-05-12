# The Zen of Oware

> Read this before writing code. Read it again before reviewing code.
> If a rule below conflicts with what you're about to do, the rule wins until you've justified the exception out loud.

## I. Do less

1. **The best code is no code.** A function you don't write has no bugs, no tests to maintain, no cognitive load. Default to *not* adding things.
2. **Three similar lines beat a premature abstraction.** Don't extract a helper on the second occurrence. Wait for the third, and only then if the shape really is the same.
3. **No speculative generality.** No "we might need this later" parameters, no unused config knobs, no hooks for features that don't exist. YAGNI is not a suggestion.
4. **No half-finished work.** Either land it or don't open the PR. No `TODO: handle errors`, no commented-out blocks, no scaffolding that "we'll wire up next sprint".
5. **Delete fearlessly.** If it's unused, it's gone. Git remembers; comments don't need to.

## II. Be honest with the reader

1. **Names carry the meaning.** A well-named identifier removes the need for a comment. Spend the thirty seconds. `seeds_captured` not `n`.
2. **Comments explain why, never what.** The code already says what. If the why is obvious from context, skip the comment too.
3. **No tombstones.** Don't write `// removed foo() — see commit abc` or `# old logic for backwards compat`. Just delete.
4. **No ticket numbers, no author tags, no dates in code.** That metadata belongs in version control, not the source.
5. **Tests document behavior.** A failing test is the best comment. If you can't write a test for it, you don't understand it yet.

## III. Trust the boundary; verify nothing inside it

1. **Validate at the edges, not in the middle.** User input, network responses, file contents: check once on entry. After that, trust your own types.
2. **Don't catch what you can't handle.** A bare `except` swallowing exceptions is a bug factory. Let it crash; the stack trace is the bug report.
3. **No defensive nulls.** If a function's contract says the argument is non-null, don't `if x is None: return None` "just in case". The caller broke the contract — let them learn.
4. **Errors are values, not vibes.** Either raise a specific exception (`IllegalMoveError`) or return a typed result. No string-matching on error messages.

## IV. Pure things stay pure

1. **The engine is stateless.** `State` is immutable. `step(s, a)` returns a new state. This is non-negotiable — MCTS, replay buffers, golden tests, and parallel self-play all depend on it.
2. **No globals.** No module-level mutable state. No singletons-by-convention. If you need state, pass it.
3. **Determinism by default.** Every stochastic component takes a `seed` or an explicit `rng`. The server records seeds. Any game must be replayable bit-for-bit.
4. **Side effects are confined.** I/O lives at the edges (server handlers, training scripts, logging sinks). The engine, the agents' decision functions, and the eval code touch nothing but their arguments.

## V. Performance is a feature; measure don't guess

1. **Profile before optimizing.** No micro-optimizations without a profiler trace. `cProfile`, `py-spy`, or it didn't happen.
2. **The engine is the hot path.** `step` is called millions of times in MCTS. Treat it like a kernel: no `dict`s, no `dataclass` instantiation in tight loops, no f-strings inside `step`.
3. **NumPy is not free.** A length-12 list beats a length-12 ndarray for the rules. Reach for NumPy when batching, not when iterating.
4. **Allocation is the enemy.** Reuse buffers in training loops. The garbage collector is not your friend at 100k steps/sec.

## VI. Tests are part of the code, not extra credit

1. **A bug fix without a test is a bug waiting to come back.** Write the failing test first, then fix.
2. **Engine coverage ≥ 95%, no exceptions.** The whole stack trusts the rules. If the rules are wrong, everything above is wrong.
3. **Hypothesis catches what you didn't think of.** Every invariant gets a property test (seed conservation, turn alternation, legal-move soundness). See [TEST_PLAN.md](TEST_PLAN.md).
4. **Test names are sentences.** `test_chain_capture_stops_at_first_non_two_or_three` not `test_capture_3`.
5. **No mocking the engine.** It's fast and pure — use the real thing. Mocks lie; real code doesn't.

## VII. Reversibility shapes risk

1. **Local and reversible: just do it.** Edit, run, iterate.
2. **Shared, public, or destructive: ask first.** Pushing, force-pushing, deleting branches, dropping tables, killing training runs, posting to external services. Confirm.
3. **Don't bypass to make red go away.** `--no-verify`, `# type: ignore`, `pytest.skip` without a reason — every one of these hides a future incident. Fix the cause.
4. **Migrations are forever.** A schema change ships to production once. Think before adding a column; think harder before dropping one.

## VIII. The interface is a contract

1. **The `Agent` protocol is sacred.** Every agent — Random, Minimax, DQN, PPO, AlphaZero — satisfies the same interface. The server never special-cases an agent family.
2. **The WebSocket protocol is sacred.** Clients in the wild may use stale versions. Additive changes only; never repurpose a field.
3. **The SQLite schema is sacred (after first launch).** Add columns with NULL defaults. Never rename, never reuse. See [TELEMETRY.md](TELEMETRY.md).
4. **Internal APIs can break; document the break.** When refactoring across module boundaries, update every caller in the same commit. No half-migrated code on `main`.

## IX. Sharp edges, called out

1. **Action masking goes before softmax.** Zeroing post-softmax leaks gradient into masked logits. This will silently sabotage PPO.
2. **Illegal-action Q-values get masked in the target max too**, not just the behavior policy. This will silently sabotage DQN.
3. **Grand-slam refusal is not "5 houses max" — it's "would the opponent be left with zero seeds".** Hardcoding 5 is a bug in disguise.
4. **The source pit is skipped on sows of ≥12, not ≥11.** Off-by-one here ruins replay determinism.
5. **Canonical perspective means rotating the board, not relabeling.** Both colors literally see `pits[0..5]` as their own row. The bug surfaces as a model that plays one color brilliantly and the other randomly.

## X. Communication

1. **Commit messages explain why.** The diff explains what.
2. **PR descriptions list what could break.** "I changed X. The things that depend on X are Y and Z. I checked them."
3. **If you don't know, say so.** "I think this works but I haven't tested the must-feed edge case" is infinitely more useful than confident silence.
4. **No status theater.** Don't write summaries of work the reader can see in the diff. Don't narrate progress in code comments. Ship the work.

## Coda

> When in doubt, do less, name things better, write a test, and ask before doing anything you can't undo. Everything else is decoration.
