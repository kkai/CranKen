# CranKen Roadmap — Toward Certified, Uniquely Solvable Puzzles

*Companion to [PRD-solvability.md](PRD-solvability.md). Phases 0–2 implement the PRD; Phase 3 is future work beyond its scope.*

## Phase 0 — Baseline & test harness (~1 day)

Goal: measure how bad the problem is today, and build the rig every later phase is verified on.

- Headless test rig: run `source/puzzle_generator.lua` under desktop Lua with a small `playdate` shim (`pd.getSecondsSinceEpoch`, `class()` from CoreLibs — or run inside the Playdate Simulator's console).
- Reference uniqueness check: reuse the Python CSP solver already in `../../kenken/` (`csp.py`, FC+MRV — solves 9×9 in ~70 ms desktop, per its README benchmarks) with a solution-counting wrapper. This is the independent oracle the Lua solver is validated against.
- Generate ≥ 1,000 puzzles per size (3–6), export cages as JSON/Lua, and record the **baseline non-uniqueness rate per size** plus generation timing.
- Exit criteria: harness runs in one command; baseline table exists.

## Phase 1 — Uniqueness on device (core, ~2–3 days)

Goal: PRD FR1, FR2, and the G1 guarantee.

- New `source/puzzle_solver.lua`: count-to-2 backtracking counter — row-major cell order, per-row/column used-value sets, partial-cage pruning (`+` sum bounds, `x` divisibility/overshoot; `-`, `/`, `=` checked at cage completion), early exit at 2 solutions, node-visit cap (default 20k).
- Wire into `PuzzleGenerator:generate_puzzle()`: generate → count → if ambiguous, **repair** (diff the two found solutions, split a differing cell into a `=` cage, re-count; cap singles at ≤ size) → after 5 failed repairs regenerate fresh, up to 50 attempts. Never return an unverified puzzle.
- Fix the dead `math.min(4, math.random(1, 3))` cage-size cap (`puzzle_generator.lua:141`); choose the new size distribution using Phase 0 uniqueness/difficulty measurements.
- Validate: Lua counter agrees with the Python oracle on 1,000+ puzzles per size (0 disagreements); on-device timing profiled on real hardware for 6×6.
- Exit criteria: harness shows 100% unique across ≥ 1,000 puzzles/size; p95 6×6 generate+verify < 1 s on device.

## Phase 2 — UX & trust (~1–2 days)

Goal: PRD FR3, FR5 — the guarantee is invisible unless generation also feels instant and reproducible.

- "Generating…" indicator when generation exceeds 250 ms (6×6 repair loops); keep the crank-idle animation running so the device never looks hung.
- Seeded generation: derive the puzzle from a stored seed; show it subtly (pause menu) and record it with best times in `best_times.lua` — reproducible puzzles, debuggable bug reports.
- Persist in-progress puzzle (cages + player grid + elapsed time) via `playdate.datastore` so closing the app doesn't lose a half-solved grid.
- Reset best-times tables (old times came from ambiguous puzzles); archive as "legacy".
- Exit criteria: v1.1 "Certified Puzzles" build sideloaded and played through all four sizes.

## Phase 3 — Future (post-v1.1, unscheduled)

- **Logic-only solvability + difficulty grading.** Rule-based solver (naked/hidden singles, cage-combination enumeration, cross-cage elimination). A puzzle solvable by rules alone = "no guessing needed"; the hardest rule used grades it Easy/Medium/Hard within each size. Grades shown at size select; best times per grade.
- **Sizes 7×7–9×9 via pre-verified packs.** On-device counting gets expensive at 7+; reuse the `../../kenken/` Python pipeline to pre-generate, uniqueness-check, and grade puzzle packs shipped as Lua data. (Fix that pipeline's negative-subtraction-target bug, `kenken.py:140`, in the process — its shipped 4×4 is currently unwinnable.)
- **Daily puzzle.** Date-derived seed + the verified generator → everyone gets the same certified puzzle; pairs with the seed work in Phase 2.
- **Pencil marks.** Crank-cycled candidate notes; becomes much more valuable once puzzles are guaranteed deducible.
- **Crank Puzzle Club.** Fold CranKen, sudoku, and a future nonogram into one shell app with shared grid UI, marks, and daily seeds — see `../../PROJECTS_OVERVIEW.md`.
