# PRD: CranKen Puzzle Solvability & Uniqueness

*Status: Draft v1 — July 2026*
*Owner: Kai Kunze*
*Scope: `finished/crankken` (Playdate, Lua, on-device generation, sizes 3×3–6×6)*

## 1. Problem

CranKen generates puzzles on device by building a random Latin square (`source/puzzle_generator.lua:25`) and carving it into random cages of 1–3 cells (`create_cage`, line 136). The solved grid is kept as `puzzle.solution`, but **no solver ever checks how many grids satisfy the published cages**. Consequences:

- **Multiple solutions are common.** Small cages with `+`/`x` targets frequently admit several valid Latin-square fills. The player can reach a grid that satisfies every printed constraint yet differs from the generator's solution.
- Today the game happens to accept those alternates, because `check_completion()` (`source/crankken.lua:204`) validates constraints rather than comparing to `puzzle.solution` — so nobody gets *stuck* — but the puzzle is not a real KenKen: a KenKen's contract with the player is "there is exactly one answer, and you can commit to deductions."
- **Best times are not comparable.** With ambiguous puzzles, a lucky alternate fill finishes faster than the intended deduction chain.

Related but out of scope here: the sibling prototype `../../kenken/` has an additional outright-unsolvable-puzzle bug (negative subtraction target from `kenken.py:140` vs. `abs()` in its checker). CranKen's operation assignment is sound (`abs` for `-`, integer-check with `+` fallback for `/`), so for CranKen "solvable" is already guaranteed by construction; **the gap is uniqueness.**

## 2. Goals

- **G1 — Uniqueness:** every puzzle presented to the player has exactly one solution.
- **G2 — Winnability:** every presented puzzle is completable via the existing `check_completion()` (no dead constraints, no regression of the by-construction solvability).
- **G3 — Feel:** generation stays on-device and endless, and still feels instant.

### Non-goals (deferred to roadmap Phase 3)

- Logic-only solvability guarantee (provably no guessing required).
- Difficulty grading within a grid size.
- Sizes 7×7–9×9, pre-shipped puzzle packs, daily puzzle mode, pencil marks.

## 3. User stories

- As a player, when I deduce a cell's value from the cages, I want that deduction to be *forced*, so that logic — not luck — finishes the puzzle.
- As a player comparing best times, I want every 4×4 puzzle to be a genuine single-solution KenKen, so times measure solving skill.
- As a player, I want a new puzzle within about a second of picking a size.

## 4. Functional requirements

- **FR1 — Solution counting.** After cage generation, a solution-counting solver runs against the cage set (not the stored solution). The puzzle is accepted only if the count is exactly 1. The counter stops searching at 2 (count-to-2; the exact number of extra solutions is irrelevant).
- **FR2 — Repair, then regenerate; never present unverified.** If count > 1: repair the puzzle (see §6) and re-count. After `MAX_REPAIRS` (default 5) unsuccessful repairs, discard and regenerate from scratch. After `MAX_ATTEMPTS` (default 50) full regenerations, fall back to the last repaired candidate *only if* it verified unique — otherwise keep trying; an unverified puzzle must never reach the player.
- **FR3 — Performance.** p95 generate+verify time < 1 s for 6×6 on Playdate hardware; < 250 ms for 3×3–4×4. If any generation exceeds 250 ms, the UI shows a "Generating…" state instead of freezing. The solver carries a node-visit cap (default 20,000); hitting the cap is treated as "ambiguous" (reject and regenerate) so worst cases cost bounded time.
- **FR4 — Win check unchanged.** `check_completion()` stays constraint-based. Once FR1 holds, constraint satisfaction and solution equality are the same predicate, and the constraint check is the more robust of the two.
- **FR5 — Seeded generation.** The RNG seed for each accepted puzzle is recorded (with best times) so puzzles are reproducible. This is the groundwork for a future daily-puzzle mode and for regression-testing reported bad puzzles.

## 5. Success metrics

Measured on the offline harness (roadmap Phase 0) over ≥ 1,000 generated puzzles per size, and cross-checked against the Python CSP solver in `../../kenken/`:

| Metric | Target |
|---|---|
| Puzzles with exactly one solution | 100% |
| Puzzles unwinnable by `check_completion` | 0 |
| p95 generate+verify, 6×6 (device) | < 1 s |
| p95 generate+verify, ≤ 4×4 (device) | < 250 ms |
| Mean regenerations per accepted puzzle | reported (expect < 3 with repair; watch for 6×6 outliers) |
| Baseline non-uniqueness rate (pre-fix) | reported per size, for the release notes |

## 6. Technical design (summary)

**New module `source/puzzle_solver.lua`** — `count_solutions(size, cages, limit, node_cap)`:

- Backtracking over cells in row-major order.
- Row/column candidate tracking via per-row and per-column `used[value]` sets (bitmask-style tables; sizes ≤ 6 keep these tiny).
- Cage pruning on every placement: for a partially filled cage, `+` prunes when the running sum plus the minimum possible remainder exceeds the target (and symmetrically for the maximum); `x` prunes on non-divisibility and overshoot; `-`, `/`, `=` are checked exactly when their cage completes (they are 1–2 cells).
- Early exit when the solution count reaches `limit` (2) or visits exceed `node_cap`.

**Generation loop change in `source/puzzle_generator.lua`** — `generate_puzzle(size)` becomes generate → count → repair/regenerate per FR2.

**Repair strategy:** when the counter finds a second solution, diff it against `puzzle.solution`; the differing cells localize the ambiguity. Pick one differing cell and split it out of its cage: it becomes a `=` single-cell cage (or the remaining cage is re-targeted from the stored solution). Each split strictly adds information, so repairs converge quickly; typically 1–2 splits suffice. Guard: cap total `=` singles per puzzle (e.g., ≤ size) so repaired puzzles don't degenerate into give-aways — beyond the cap, regenerate instead.

**Incidental fix:** `puzzle_generator.lua:141` — `local max_cage_size = math.min(4, math.random(1, 3))` caps cages at 3 despite the "1–4 cells" comment; change to an explicit distribution (e.g., weighted 1–4) once the harness can measure its effect on uniqueness rate and difficulty.

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Solver worst case on 6×6 blows the time budget | Node-visit cap → treat as ambiguous, regenerate; cap tuned on-device in Phase 1 |
| Random cages have a low uniqueness acceptance rate → long generation loops | Repair-by-splitting converges without full regeneration; harness reports attempt counts so the cage-size distribution can be tuned |
| Repair makes puzzles too easy (many `=` cells) | Cap on singles per puzzle; prefer re-targeting over splitting when possible |
| Lua GC pauses during search | Preallocate solver tables per size; no allocations in the inner loop |

## 8. Rollout

Ship as CranKen v1.1 "Certified Puzzles". Release note: every puzzle now has exactly one solution. Best-times tables reset (old times were earned on ambiguous puzzles); old bests archived under a "legacy" label.
