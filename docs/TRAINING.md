# Training Logs & Monitoring

All training runs log to **TensorBoard** (scalars, histograms, text, occasional images) and use **tqdm** for live terminal progress. No external services — everything lives in `artifacts/` and is viewable from a local browser tab.

We deliberately chose TensorBoard over W&B for v1: zero account/auth, no network dependency, fully self-contained for a single-machine project. The logging API we wrap is thin enough that swapping to W&B later is a one-file change if we want it.

## Quick start

```bash
# Run training in one terminal:
uv run python -m oware.agents.dqn.train --config configs/dqn_v1.yaml

# View logs in another (auto-discovers all runs under artifacts/):
uv run tensorboard --logdir artifacts/tb --port 6006

# Open http://localhost:6006
```

Each training run creates `artifacts/tb/<agent_family>/<run_id>/` where `run_id = <timestamp>_<short_hash_of_config>`. TensorBoard's run picker shows every historical run side-by-side for direct comparison.

## What we log

### Scalars (per training step or eval interval)

Common to every family:

| Tag                          | When             | Notes                                                  |
|------------------------------|------------------|--------------------------------------------------------|
| `train/loss`                 | every step       | total loss                                             |
| `train/lr`                   | every step       | learning rate (useful with schedulers)                 |
| `train/grad_norm`            | every step       | post-clip; spike-watching                              |
| `train/step_per_sec`         | every 100 steps  | throughput regression catcher                          |
| `eval/winrate_vs_random`     | every N steps    | sanity — should hit ~1.0 fast                          |
| `eval/winrate_vs_minimax_d2` | every N steps    | first real milestone                                   |
| `eval/winrate_vs_minimax_d4` | every N steps    | the headline metric                                    |
| `eval/winrate_vs_minimax_d6` | every N steps    | aspirational                                           |
| `eval/avg_plies`             | every N steps    | shorter = more decisive; very long = stalling          |
| `eval/avg_captured`          | every N steps    | balance of capture frequency                           |
| `promotion/event`            | on promotion     | step value of any `latest.pt` promotion (vertical line)|

Family-specific:

**DQN**

- `train/td_error_mean`, `train/td_error_max`
- `train/replay_buffer_size`
- `train/epsilon`
- `train/q_value_mean`, `train/q_value_max` (sanity — should grow then plateau)

**PPO**

- `train/policy_loss`, `train/value_loss`, `train/entropy`
- `train/clip_fraction` (PPO clip diagnostic; ideally 0.1–0.3)
- `train/approx_kl` (early-stop if it spikes)
- `train/explained_variance` (value function quality)

**AlphaZero-lite**

- `train/policy_loss`, `train/value_loss`
- `train/value_mean_abs_error`
- `selfplay/games_per_sec`
- `selfplay/avg_root_visits`
- `mcts/avg_depth`, `mcts/avg_branching`

### Histograms (every K steps, K=1000)

- `weights/<layer_name>` and `grads/<layer_name>` — watching for dead/exploding layers.
- `actions/distribution` — which pits the policy plays during eval. Collapse to one pit = a bug.
- `q_values/distribution` (DQN) or `policy_logits/distribution` (PPO/AZ).

### Text (every M steps, M=10000)

- A sampled eval game logged as a board-string sequence. Helps eyeball *why* the agent is winning or losing.

### Images (optional)

- A heatmap of action probabilities across a fixed test-set of 16 positions. Stored under `eval/policy_heatmap`. Reveals stylistic shifts over time.

## tqdm conventions

Use one tqdm bar per logical loop, no nesting more than two levels (Python terminals get unreadable past that).

```python
from tqdm import tqdm

for epoch in tqdm(range(num_epochs), desc="epochs", position=0):
    for batch in tqdm(loader, desc="batch", position=1, leave=False):
        ...
```

Postfix carries the live scalars the eye needs *now*, not everything we log:

```python
pbar.set_postfix(loss=f"{loss:.3f}", winrate=f"{winrate:.2%}", eps=f"{eps:.2f}")
```

Rules:

1. **One outer bar = total expected steps.** No infinite spinners — if the loop has no known end, fix that first.
2. **`leave=False` on inner bars**, `leave=True` on the outermost so the final state is preserved in scrollback.
3. **No `print()` inside a tqdm loop** — use `tqdm.write()` or it shreds the bar.
4. **Update at most ~10×/sec.** Default mininterval is fine; do not call `pbar.update()` in a tight inner loop.
5. **In CI/non-tty runs**, set `disable=not sys.stdout.isatty()` so logs aren't polluted with bar redraws.

## Logging code shape

Single thin wrapper so swapping backends later is a one-file change:

```python
# src/oware/training/logging.py
from torch.utils.tensorboard import SummaryWriter

class RunLogger:
    def __init__(self, run_dir: Path):
        self.writer = SummaryWriter(str(run_dir))

    def scalar(self, tag: str, value: float, step: int): ...
    def scalars(self, prefix: str, values: dict[str, float], step: int): ...
    def hist(self, tag: str, tensor, step: int): ...
    def text(self, tag: str, text: str, step: int): ...
    def image(self, tag: str, image, step: int): ...
    def close(self): ...
```

Trainers receive a `RunLogger` — they do not import TensorBoard directly. This is the rule that makes a W&B port a half-hour job.

## Config persistence

Every run writes its resolved config as `artifacts/tb/<family>/<run_id>/config.yaml` and as a `text` tag `meta/config` inside TensorBoard. Hovering over any scalar curve in the UI then has the matching config one click away.

Also written alongside:

- `git_sha.txt` — current commit, dirty-flag if uncommitted changes.
- `env.txt` — Python version, torch version, CUDA visible devices.

These three artifacts are what makes a run reproducible.

## Eval games dump

The eval runner writes every game's `(state, action, captured)` trace to `artifacts/eval/<run_id>/games.jsonl`. Same format as the [telemetry SQLite](TELEMETRY.md) `moves` rows, so we can replay an eval game in the web UI by loading it from the JSONL.

## Watching long runs

For a multi-hour PPO or multi-day AlphaZero run:

- Run training under `nohup` or inside a `tmux` session.
- TensorBoard reload interval is 30s by default — fine.
- Use the **smoothing slider** at ~0.9 on noisy scalars (`policy_loss`, `entropy`) and 0 on winrate (you want to see the raw stair-step of eval intervals, not a blur).
- The **scalars dashboard** supports regex filtering: `train/.*loss` is a useful preset.

## When training looks broken

Quick triage checklist before opening a debugger:

1. **`eval/winrate_vs_random` not hitting ~1.0**: env/reward/masking bug. Stop training; fix the engine wrapper.
2. **Loss diverges (`NaN` / spike)**: gradient explosion — check `train/grad_norm` for the step before the spike. Add or tighten clipping.
3. **`actions/distribution` collapses to one pit**: entropy died. For PPO, raise entropy coef or slow its anneal. For DQN, raise epsilon floor.
4. **`mcts/avg_depth` ≈ 1** (AZ): MCTS budget is too small, or the value head is outputting constants — check `train/value_mean_abs_error`.
5. **Throughput drops over time**: replay buffer leak, dataloader leak, or GPU memory fragmentation. `py-spy dump` on the training PID is your first move.

## Out of scope (for v1)

- **W&B / MLflow / Neptune**: explicitly skipped to keep the project self-contained. If we ever want multi-machine collaboration, the `RunLogger` wrapper makes this a small change.
- **Live training control** (pause / adjust LR from a UI): cute, never worth the engineering on a single-developer project.
- **Distributed logging** (multiple workers writing to one run): self-play workers write their own subdirs; the trainer logs scalars; TensorBoard merges naturally.
