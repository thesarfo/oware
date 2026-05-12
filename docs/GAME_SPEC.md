# Oware — Game Specification (Abapa)

Source of truth for the engine. If code disagrees with this doc, fix one of them deliberately. All rule clauses below are paraphrased from the **Abapa** ruleset (the tournament variant used across West Africa and the Caribbean, also known as Ayoayo, Awale, Warri, Adji-Boto, Awele). Direct quotes from the rules document are marked with `>`.

## Board and equipment

- Two rows of 6 **houses**. Each row is the territory of the player sitting nearest to it.
- Two **stores** (one per player) hold captured seeds. On portable boards these are external; on the standard board they are two extra depressions between the rows. Either way, stores never participate in sowing.
- 48 seeds (a.k.a. **nickers**) total; 4 seeds in each of the 12 houses at the start.

Internal indexing:

```text
        Opponent (north)
   11  10   9   8   7   6
    0   1   2   3   4   5
        Player (south)
```

- `pits[0..5]` = south's row, left → right from south's view.
- `pits[6..11]` = north's row, continuing **anti-clockwise** (so sowing goes 0→1→…→5→6→…→11→0…).
- `store[0]` = south, `store[1]` = north.

## Object

> The object of the game is to capture as many seeds (nickers) as possible. The first player to capture 25 seeds or more wins the game. A draw is possible in this game with each player capturing 24 seeds.

So: **first to 25 wins; 24–24 is a draw**. Captures are made by landing the **last** seed on the opponent's side in a house that now totals 2 or 3.

## Who starts

> To start the game both players have to decide who should start. … In subsequent games the winner starts.

In our system the human picks color when creating the game; the server respects that. The "winner starts next game" clause matters only if we add multi-round matches (not in v1).

## Sowing

A player picks one of their own houses that contains ≥1 seed (action = house index 0–5 from their perspective), scoops **all** seeds, and sows them one at a time **anti-clockwise** starting in the house immediately to the right of the source.

> The remainder of the seeds are placed in the houses directly following each other without skipping a house.

### Omitting the source on a long lap

> The only exception is when a house that is being played has more than 11 seeds in it. … one will be able to place a seed in each house until one comes to the original house that one scooped the seeds from, the next seed is not placed in this house but in the one after it.

In implementation terms: when the in-hand seed count is **≥12**, sowing will lap past the source house; on each lap, **skip the source house**. The destination index increments to the next house instead. (At exactly 11 seeds the last seed lands in the house just before the source, so no skip is needed; the rule only kicks in at 12+.)

## Captures

> One captures seeds by making a two or three with one's last seed on the opponent's side. Take note if one makes a two or three but has seeds left to sow one does not gain anything.

Two conditions, both required:

1. The **last** sown seed lands in an **opponent** house.
2. That house's count is **exactly 2 or 3** *after* the seed lands.

If you make a 2 or 3 mid-sow, that's **not** a capture — only the final seed matters.

### Multiple (chain) capture

> If one makes a two or three with one's last seed and the house or houses preceding the captured house on the opponent's side also have twos, threes or any combination of them, one captures these as well. So long as there are no houses with less than two or more than three seeds, in-between them, a maximum of five houses can be captured in this way.

Walk backwards along the **opponent's row** from the landing house. Each preceding opponent house that contains exactly 2 or 3 seeds is also captured. Stop at:

- the first opponent house whose count is not 2 or 3, **or**
- the boundary into your own row (the player's territory is never captured),
- at most 5 houses captured this way.

### Grand-slam forfeit

> Beyond five houses one forfeits everything, as this would leave the opponent with no seeds to play with.

If the chain of captures would empty every house on the opponent's side (leave them with no seeds anywhere in their row), the capture is **forfeited entirely**: sowing still happens, but **no seeds move to the mover's store**. This corresponds to the "no grand slam" rule used in tournament play.

The 5-house cap in the rules is a consequence of this: the opponent has 6 houses, so capturing 6 would always be a grand slam; the largest legal chain is therefore 5. We enforce the underlying rule ("would the opponent be left with zero seeds?") rather than hard-coding 5, because the same situation can arise with fewer houses if some opponent pits are already empty.

## Compulsory moves ("must-feed")

> If the situation arises where one player has no seeds to play with the other player must provide some seeds to the opponent if possible. A move that does not do this whilst being able to feed the other player with seeds is not allowed.

If the opponent has zero seeds across their row, the side to move **must** play a move that sows at least one seed into the opponent's row. Among the player's pseudo-legal moves, filter to those that "feed"; if any exist, only those are legal. If none exist, the game ends (see below).

> Greater priority is placed on capturing seeds to the end. Therefore maneuvering seeds in such a way that will eventually lead to the opponent not having seeds to play with is not encouraged.

This second sentence is a social/strategic note, not a mechanical rule: the engine does not forbid moves that *eventually* starve the opponent — only moves that *immediately* fail to feed when the opponent is already empty.

## End of game

> The game ends when one player has captured 25 seeds or more. When both players decide that continuing will only lead to going round in circles in such a case each player keeps the seeds on their side.

End conditions, in priority order:

1. **Majority**: a player's store reaches ≥25 → that player wins.
2. **Draw by majority**: both stores = 24 → draw.
3. **Must-feed impossible**: it's your turn, the opponent has no seeds, and **no** move you can play would feed them → the game ends. Standard tournament practice is that the player on move collects the seeds remaining on **their own** side (since the opponent's side is already empty). All remaining seeds on the board go to the store of whoever has them on their side.
4. **Mutual no-progress / cycle**: the rules allow players to agree to end the game when it loops; computers can't "agree", so we apply a deterministic surrogate — **if 100 plies pass with no capture, the game ends and each player collects the seeds on their own side**. The 100-ply cap is a project choice, not part of Abapa; revisit if it produces pathological play. (Some tournaments cap at 200; we picked 100 to keep self-play episodes short.)

In all end-by-no-progress cases, **store totals after the seed sweep** determine the winner; ties are draws.

## Legal move generation (pseudocode)

```python
legal_moves(state):
    side = state.to_move
    own_indices = range(0, 6) if side == SOUTH else range(6, 12)
    candidates = [i for i in own_indices if state.pits[i] > 0]

    opp_indices = range(6, 12) if side == SOUTH else range(0, 6)
    if sum(state.pits[j] for j in opp_indices) == 0:
        # must-feed: keep only moves that deliver a seed to opp_indices
        feeding = [i for i in candidates if move_feeds_opponent(state, i)]
        if feeding:
            return feeding
        # else: no legal move; game ends via end-condition #3

    return candidates
```

`move_feeds_opponent` is computed by simulating the sow (it must account for the source-skip rule on laps of 12+).

## Canonical state encoding for RL

```python
obs = [
    *pits_from_to_move_perspective,   # 12 ints, rotated so the agent's row is [0..5]
    store_to_move,                    # int
    store_opponent,                   # int
    ply_count_normalized,             # float in [0, 1]
]
```

Always presenting the board from the **side-to-move's perspective** lets one network play both colors and doubles the training data per game.

## Worked examples

Numbered to be referenced from [TEST_PLAN.md](TEST_PLAN.md).

### EX1 — opening sow, no capture

South plays pit 2 (4 seeds) from the initial position.

- After: pits = `[4,4,0,5,5,5,5,4,4,4,4,4]`, stores `[0,0]`. Last seed lands in pit 6 (now 5) → not 2 or 3, no capture.

### EX2 — single capture

South pit 5 = 1, north pit 6 = 1, rest arbitrary but not 2-or-3. South plays pit 5.

- Last seed lands in pit 6, now 2, on the opponent's side → capture 2 seeds.

### EX3 — chained capture

South pit 5 = 2; north pits {6: 1, 7: 1, 8: 4}. South plays pit 5.

- Sows into 6, 7. Pit 7 now = 2 → capture. Walk back: pit 6 now = 2 → capture. Pit 8 = 4 → stop. Total captured = 4.

### EX4 — capture interrupted by a non-2/3

South pit 5 = 2; north pits {6: 4, 7: 1}. South plays pit 5.

- Sows into 6, 7. Pit 7 = 2 → capture. Walk back: pit 6 = 5 → stop. Total captured = 2.

### EX5 — "made a two mid-sow, no capture"

A sow whose final seed lands in pit 9 (own row would be different — landing on own side never captures). Or: a sow that makes a 2 in pit 8 mid-flight but ends in pit 11 with a value of 5 → **no capture** anywhere. The rule is final-seed-only.

### EX6 — grand-slam forfeit

A position where the only capture chain would empty all six of the opponent's houses, or would empty every non-empty house on the opponent's side. The move is **legal**, sowing happens, but **no seeds enter the store**.

### EX7 — long sow skipping the source

South pit 0 = 12. South plays pit 0.

- Sows into 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 (11 seeds placed). Twelfth seed would go back into pit 0; **skip** it, place in pit 1 instead.
- After: pit 0 = 0, pit 1 = +2, pits 2–11 each +1.

### EX8 — must-feed forced

North has zero seeds. South pits = `[0,0,0,0,0,1]`. The only legal move is pit 5 (which sows into pit 6 in north's row). All other moves are illegal even if they'd be otherwise pseudo-legal.

### EX9 — must-feed impossible → game ends

North has zero seeds. South cannot reach the opponent's row with any move (e.g. south pit 5 = 0 and all remaining south seeds are too far back). Game ends; south sweeps remaining seeds on south's side into south's store; winner is whoever has ≥25 after the sweep (else draw).

### EX10 — majority win

South store reaches 25 mid-game → game ends immediately with south as winner, regardless of seeds remaining on the board.

### EX11 — 24–24 draw via no-progress cap

Game reaches the 100-ply no-capture cap with stores `[24, 24]` and 0 seeds left on the board → draw.

## References

- Abapa rules (provided by project owner; quoted inline above).
- Wikipedia: Oware — for cross-checking against Ayoayo / Awari naming variants.
- Romein & Bal, *Solving Awari with Parallel Retrograde Analysis* (2003) — useful for sanity-checking endgame positions if we want a strong external oracle.
