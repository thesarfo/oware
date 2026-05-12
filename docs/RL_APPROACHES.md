# RL Approaches

Three agent families, in increasing order of complexity and (expected) playing strength. All three share the engine, the canonical observation, and the `Agent` interface — the only thing that differs is the training loop and the inference path.

## Shared design

- **Observation**: 14-int board (12 pits + 2 stores) from side-to-move perspective + a normalized ply counter. Flattened to a length-15 float vector, or reshaped to a 2×6 grid for conv nets.
- **Action space**: `Discrete(6)`. All agents output 6 logits/Q-values; illegal actions are masked to `-inf` (policy) or excluded from the argmax (Q).
- **Reward**: terminal only. `+1` win, `0` draw, `-1` loss. No shaping. Discount γ = 0.99.
- **Self-play**: every NN family trains in self-play after a brief bootstrap. Opponent pool = last K snapshots + a Minimax-d4 anchor to prevent rock-paper-scissors collapse.
- **Eval protocol**: every N training steps, play 200 games vs. Minimax-d2/d4/d6 (100 as each color) and log winrate. Promotion to `latest.pt` requires beating the previous `latest.pt` head-to-head ≥55% over 400 games.

## 1. DQN

**Why first**: simplest of the three. Off-policy, value-based, replay buffer — well-trodden territory and a useful sanity check that the env + reward are correct.

### Network

- Input: 15-vector. MLP, 3 hidden layers of 128, ReLU. Output: 6 Q-values.
- Optional dueling head (`V(s) + A(s,a) - mean(A)`) — small board so this is almost free.

### Training loop

- Double DQN: target network updated every 2k env steps.
- Replay buffer: 200k transitions, prioritized (PER, α=0.6, β annealed 0.4→1.0).
- Epsilon: 1.0 → 0.05 over 200k steps.
- Loss: Huber on TD error with illegal-action Q-values masked out of the target's max.
- Batch size 256, Adam @ 1e-4, ~1M env steps.

### Opponent schedule

- Steps 0–50k: opponent is Random.
- 50k–150k: opponent is Minimax-d2 (50%) + Random (50%).
- 150k+: self-play snapshot pool + Minimax-d4 anchor.

### Expected strength

Should comfortably beat Random and Minimax-d2, contest Minimax-d4. Likely loses to Minimax-d6 due to terminal-only reward + thin search.

## 2. PPO (Actor-Critic)

**Why second**: on-policy, stable, and the action-masking story is clean. PPO with a shared trunk and separate policy/value heads is the workhorse for board-game RL when you don't yet want MCTS.

### Network

- Shared trunk: MLP (2×6 reshape → flatten → 2× hidden 256). Or a tiny conv stack treating the board as a 2×6 image with 1 channel — try both.
- Policy head: 6 logits, masked.
- Value head: scalar V(s).

### Training loop

- Rollouts of 2048 steps from N parallel self-play envs (N=8). Each env plays both sides; we collect trajectories for the side-to-move and flip the value sign at the boundary.
- GAE (λ=0.95), clip ε=0.2, entropy coef 0.01 (annealed), value coef 0.5.
- 4 epochs per rollout, minibatch 256.
- ~50M env steps target.

### Action masking

Apply mask **before** the softmax so illegal actions contribute zero probability and zero gradient. Don't just zero them post-softmax — you'll get gradient leakage into the masked logits.

### League play

Maintain a pool of the last 10 snapshots. Each parallel env picks an opponent at the start of each game: 60% latest, 30% from pool, 10% Minimax-d4. Prevents the policy from forgetting how to beat earlier styles.

### Expected strength

Should beat Minimax-d4 reliably and contest d6. This is the agent that's most likely to be the "fun, fast, strong" web opponent — single forward pass per move, no search.

## 3. AlphaZero-lite

**Why third (and last)**: highest ceiling, highest engineering cost. We do a deliberately small version — small net, low simulation count — because the board is tiny and we don't have a render farm.

### Network

Two heads on a shared body:

- **Policy head**: 6 logits, π(a|s).
- **Value head**: scalar v(s) ∈ [-1, 1].

Body: small ResNet — 4 residual blocks of (Conv-BN-ReLU)×2, 64 channels, on a 2×6 input. Total parameters ~150k. The board is small enough that an MLP would work too; we use a tiny resnet to mirror the canonical AlphaZero recipe and keep the code reusable for larger boards later.

### MCTS

- PUCT formula with `c_puct = 1.5`.
- Default 200 simulations per move at training time; 400 at served inference. Configurable.
- Dirichlet noise (α=0.5, ε=0.25) added to the root prior during self-play only.
- Virtual loss for batched leaf evaluation if/when we parallelize rollouts.

### Self-play loop

1. **Self-play workers** (CPU): each plays a game using MCTS + current net, writes `(state, π, z)` tuples to a shared buffer. `π` is the visit-count distribution at the root; `z` is the final outcome from that state's perspective.
2. **Trainer** (GPU): samples minibatches from the buffer, optimizes `L = (z - v)² - π·log p + c·||θ||²`. Adam @ 1e-3, batch 512.
3. **Evaluator**: every N training steps, the candidate plays 100 games vs. the current best. Promote if winrate ≥ 55%.

Buffer size: 500k positions, FIFO. Temperature: τ=1.0 for the first 15 plies of self-play, then τ→0 (argmax over visit counts).

### Symmetries

Oware has **no spatial symmetry** we can exploit (the two rows aren't interchangeable — they belong to different players). So no symmetry augmentation, unlike Go/Chess AlphaZero.

### Compute budget

- Single GPU (or even CPU + small net): ~24–48 hours of self-play should land somewhere between Minimax-d6 and Minimax-d8.
- Hard cap the project at this — we are not trying to solve Awari (it's already weakly solved by retrograde analysis; that's a different research lane).

### Expected strength

Strongest of the three. The combination of search at inference time + a learned prior is what makes this agent qualitatively different from PPO/DQN, which are pure policy/value lookups.

## Comparison table

| Property              | DQN              | PPO                | AlphaZero-lite     |
|-----------------------|------------------|--------------------|--------------------|
| On/off policy         | Off              | On                 | Off (replay buffer)|
| Search at inference   | None             | None               | MCTS (200–400 sims)|
| Wall clock to train   | Hours            | Hours–day          | 1–2 days           |
| Inference latency     | ~5 ms            | ~5 ms              | ~500 ms            |
| Expected vs Minimax-d4| ~contest         | ~win               | win                |
| Expected vs Minimax-d6| lose             | contest            | win                |
| Implementation cost   | Low              | Medium             | High               |

## Things we'll get wrong the first time (predictions)

- DQN will saturate around Minimax-d2 if we forget to mask illegal actions in the **target** max as well as the behavior policy. Easy bug, common in board-game DQN code.
- PPO will collapse to a single opening if we don't keep entropy ≥ 0.3 in the early phase. Anneal slowly.
- AlphaZero will look weak for the first 100k self-play games then suddenly improve — this is normal. Don't kill the run too early.
