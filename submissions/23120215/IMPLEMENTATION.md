# Lab 2 – Blind Adversary: Implementation Document

## 1. Problem Statement

Both agents operate under **partial observability**: instead of seeing the full 21×21 map,
each agent perceives only a cross-shaped field of view extending **5 cells** in each cardinal
direction, blocked by walls. The `enemy_position` parameter is `None` whenever the opponent
is outside the agent's line of sight, and empty cells beyond the FOV are marked as `−1`
(unseen) in the `map_state` array.

The challenge is to **seek** (Pacman) or **hide** (Ghost) effectively when the opponent's
location is unknown most of the time.

| Setting | Value |
|---------|-------|
| Map size | 21 × 21 |
| FOV shape | Cross (cardinal rays) |
| FOV radius | 5 cells, blocked by walls |
| Pacman speed | 2 cells/step (straight line only) |
| Capture condition | Manhattan distance < 2 |
| Max steps | 200 |
| Time budget | 1 second per step |
| Memory budget | 16 MB |

---

## 2. Architecture Overview

```
agent.py
├── Shared utilities
│   ├── is_valid()          – bounds + wall check (known-empty only)
│   ├── is_passable()       – bounds + non-wall check (allows unseen)
│   ├── a_star()            – A* with optional optimistic traversal
│   ├── pacman_next_positions()     – speed-2 reachability (1 turn)
│   └── pacman_turn_distances()     – BFS modelling speed-2 per turn
├── MemoryMap               – persistent map built from partial observations
├── PacmanAgent             – seek agent
│   ├── _chase()            – A* + speed-2 when enemy visible
│   ├── _search()           – frontier exploration when enemy hidden
│   └── _find_frontier_target()  – BFS to nearest exploration boundary
└── GhostAgent              – hide agent
    ├── Belief map           – Bayesian probability grid for Pacman's location
    │   ├── _predict_belief()   – motion-model prediction step
    │   ├── _belief_centroid()  – weighted mean of belief distribution
    │   └── observation update  – positive/negative evidence
    ├── _panic()             – 2-ply minimax for close encounters
    ├── _caution()           – weighted multi-factor scoring
    └── _calm()              – A* to safest haven cell
```

---

## 3. Key Components

### 3.1 Memory Map (`MemoryMap` class)

Both agents maintain a **persistent map** that accumulates every observation across steps.

```
Step 1:  Agent sees cells around (15,10)  →  those cells are revealed (0)
Step 2:  Agent moves to (14,10)           →  new cells revealed, old ones remembered
...
Step N:  Most of the maze is explored     →  known map ≈ full map
```

**Implementation** (lines 144–170):
- Internal grid initialised to `−1` (all unknown).
- Walls (`1`) are copied on the first observation (the framework always provides all walls).
- Visible empty cells (`0`) are merged in on every call to `update()`.
- `get()` returns the current best-known map for pathfinding.

**Why it matters**: Without the memory map, the agent would only be able to pathfind
within its current 5-cell cross.  With it, the agent can A\* through corridors it explored
30 steps ago, even though those corridors are currently outside the FOV.

### 3.2 Optimistic A\* (`allow_unseen` mode)

Standard A\* only traverses cells known to be empty (`== 0`).  When navigating toward
unexplored territory, this would fail because the path necessarily crosses unseen cells.

**Solution**: the `allow_unseen=True` flag treats `−1` cells as passable (optimistic
assumption — the cell is probably a corridor, not a wall).

```python
def get_neighbors(pos, known_map, allow_unseen=False):
    checker = is_passable if allow_unseen else is_valid
    ...
```

This is used by the Pacman exploration logic and is **never** used when the enemy position
is known (where we want guaranteed-safe paths).

### 3.3 Pacman-Turn BFS (`pacman_turn_distances`)

Models Pacman's speed-2 movement in BFS: one BFS level = one game turn.  From each cell,
the BFS expands to all 1-step neighbors **and** all 2-step straight-line extensions.

This is used by the Ghost to assess how many *turns* (not cells) it would take Pacman to
reach any position — a more accurate threat metric than Manhattan distance.

---

## 4. PacmanAgent (Seek)

### 4.1 Algorithm Selection

| Situation | Algorithm | Rationale |
|-----------|-----------|-----------|
| Enemy visible | **A\* search** with Manhattan heuristic | Optimal shortest path through known terrain |
| Enemy recently seen (≤15 steps) | A\* to last-known position | Ghost likely still nearby |
| Enemy unknown | **Frontier exploration** (BFS) | Systematically uncovers unseen map regions |

### 4.2 Chase Mode (enemy visible)

When `enemy_position is not None` (lines 230–236):

1. Run A\* from `my_position` to `enemy_position` on the known map.
2. If no path exists on known-safe cells, retry with `allow_unseen=True`.
3. Extract the first move and apply speed-2 if the next two moves share the same direction.

**Speed-2 optimisation** (lines 318–326):
```python
if len(path) >= 2 and path[1] == path[0]:
    # Two consecutive moves in the same direction → move 2 cells
    return (move, 2)
```

### 4.3 Search Mode (enemy invisible)

When `enemy_position is None` (lines 240–267):

**Phase 1 — Last-Known Pursuit** (lines 243–251):
If the ghost was spotted within the last 15 steps, A\* toward the last-known position.
When we arrive there (distance ≤ 1), clear the stale target and switch to exploration.

**Phase 2 — Frontier Exploration** (lines 253–264):
Find and navigate to the nearest **frontier cell** — a known-empty cell adjacent to at
least one unseen (`−1`) cell.  Moving there maximises the chance of revealing new corridors.

**Frontier-finding algorithm** (`_find_frontier_target`, lines 269–314):
```
BFS from my_position over known-empty cells:
  for each cell in BFS order:
    if cell has at least one unseen neighbor → it's a frontier
    return the nearest frontier cell
  if no frontier exists → map fully explored → patrol farthest cell
```

**Phase 3 — Stuck detection** (lines 211–216):
If the agent hasn't moved for 3+ steps, it picks a new exploration target to break loops.

### 4.4 Complexity

| Operation | Time | Frequency |
|-----------|------|-----------|
| Memory map update | O(21×21) = O(441) | Every step |
| A\* search | O(N log N), N ≤ 441 | Every step |
| Frontier BFS | O(N), N ≤ 441 | When exploration target expires |
| Total per step | **< 1 ms** | — |

---

## 5. GhostAgent (Hide)

### 5.1 Core Innovation: Bayesian Belief Tracking

The Ghost maintains a **21×21 probability grid** (`self.belief`) estimating where Pacman
is likely to be.  This is updated every step via a predict–update cycle inspired by
Bayesian filtering (Hidden Markov Model style).

#### Predict Step (`_predict_belief`, lines 462–476)

Before incorporating the current observation, we spread the belief forward in time:

```
For each cell (r,c) with probability P(r,c) > 0:
    Compute all cells Pacman could reach from (r,c) in one turn
    (speed-1 in any direction, speed-2 in a straight line, or STAY)
    Distribute P(r,c) uniformly among those reachable cells
```

This models the uncertainty: since we don't know Pacman's strategy, we assume each
reachable destination is equally likely.

#### Update Step (lines 399–420)

Two types of evidence are incorporated:

| Evidence | Condition | Action |
|----------|-----------|--------|
| **Positive** | `enemy_position is not None` | Collapse belief: `belief = 0 everywhere; belief[enemy] = 1.0` |
| **Negative** | Visible empty cell, no Pacman there | `belief[visible_cells] = 0` (Pacman is definitely not here) |

Negative evidence is powerful: every step, the Ghost zeroes out all cells within its
FOV.  Over time, the belief concentrates on unobserved regions, giving the Ghost a
statistical estimate of Pacman's direction.

#### Belief Centroid (`_belief_centroid`, lines 478–488)

The expected Pacman position is the weighted mean:

```
E[row] = Σ (row × belief[row,col]) / Σ belief
E[col] = Σ (col × belief[row,col]) / Σ belief
```

This centroid is used as the "estimated threat" for evasion when Pacman is invisible.

### 5.2 Three-Layer Evasion Strategy

The evasion layer is selected based on the **Pacman-turn distance** (BFS accounting for
speed-2) from the estimated threat to the Ghost's current position.

#### PANIC Mode (Pacman-turn distance ≤ 6)

**Algorithm**: 2-ply minimax with alpha-pruning (lines 492–531).

```
For each Ghost move g₁:
  new_ghost = apply(ghost_pos, g₁)
  For each Pacman response p₁ ∈ pacman_next_positions(threat):
    if manhattan(p₁, new_ghost) < 2 → caught → score = -100
    For each Ghost follow-up g₂:
      For each Pacman response p₂:
        evaluate: manhattan(p₂, g₂)
      worst_p₂ = min over all p₂
    best_g₂ = max over all g₂ of worst_p₂
  min_over_pac = min over all p₁ of best_g₂
  
  score = min_over_pac + escape_bonus + oscillation_penalty + dead_end_penalty + ptd_bonus
  
Choose g₁ with highest score
```

**Evaluation bonuses** (lines 520–526):

| Factor | Weight | Purpose |
|--------|--------|---------|
| `escape_bonus` | +0.15 per exit | Prefer positions with multiple escape routes |
| `osc_penalty` | −0.3 | Penalise reversing the last move (oscillation) |
| `dead_penalty` | −2.0 | Heavily penalise dead-ends (≤1 exit) |
| `ptd_bonus` | +0.2 × ptd | Prefer positions farther from Pacman in turn-distance |

#### CAUTION Mode (Pacman-turn distance 7–12)

**Algorithm**: Weighted multi-factor scoring (lines 535–554).

```
score = 2.5 × pacman_turn_distance
      + 1.2 × num_escape_exits
      − 1.5 × oscillation_flag
      − 5.0 × dead_end_flag
      − 0.5 × stay_flag
```

#### CALM Mode (Pacman-turn distance > 12)

**Algorithm**: A\* navigation to a "haven" cell (lines 558–581).

The haven is the reachable cell with the **maximum Pacman-turn distance** that has at
least 2 exits (not a dead-end).  The Ghost caches this target and navigates toward it,
invalidating the cache when Pacman moves closer to the haven than the Ghost is.

### 5.3 Complexity

| Operation | Time | Frequency |
|-----------|------|-----------|
| Memory map update | O(441) | Every step |
| Belief predict | O(K × 9), K = non-zero cells | Every step |
| Belief update | O(441) | Every step |
| Pacman-turn BFS | O(441) | Every step |
| 2-ply minimax (PANIC) | O(5 × 9 × 5 × 9) ≈ O(2025) | When in PANIC |
| Total per step | **< 5 ms** | — |

---

## 6. Design Decisions

### Why A\* over BFS for Pacman?

A\* with the Manhattan heuristic expands fewer nodes than BFS by guiding the search toward
the goal.  On a 441-cell grid the difference is negligible in time, but A\* guarantees
optimality while being conceptually cleaner for goal-directed search.

### Why Bayesian belief over "just go to last-known position"?

The last-known position becomes stale quickly: after 10+ steps, Pacman could be anywhere.
The belief map degrades gracefully — it spreads probability outward from the last sighting
while being continuously refined by negative evidence (visible cells without Pacman).
This gives the Ghost a statistically meaningful estimated threat direction even 50+ steps
after losing sight.

### Why optimistic pathing for exploration?

The Pacman agent needs to navigate toward unseen cells.  If A\* treated unseen cells as
walls, it could never plan a path toward them.  The optimistic assumption (`−1` = passable)
allows the agent to commit to a path; if it turns out to be blocked, the new observation
updates the memory map and a revised path is computed next step.

### Why 2-ply minimax instead of deeper search?

With branching factor ≈5 (Ghost) × 9 (Pacman with speed-2), a 2-ply search evaluates
≈2,025 leaf states.  Going to 3 plies would yield ≈91K leaves — still feasible but
approaching the 1-second budget on Colab CPUs.  2 plies provides a strong improvement over
greedy evasion while staying comfortably within the time limit.

---

## 7. Testing Summary

All tests run with: `--pacman-speed 2 --capture-distance 2 --pacman-obs-radius 5 --ghost-obs-radius 5`

### Pacman (Seek) Performance

| Opponent | Mode | Win Rate | Avg Steps |
|----------|------|----------|-----------|
| example_student | Deterministic | 1/1 (100%) | 124 |
| example_student | Stochastic ×10 | 9/10 (90%) | ~28 |
| 23120219 (BFS) | Deterministic | 1/1 (100%) | 48 |

### Ghost (Hide) Performance

| Opponent | Mode | Win Rate | Avg Survival |
|----------|------|----------|--------------|
| example_student | Deterministic | 0/1 (167 steps) | 167 |
| example_student | Stochastic ×10 | 6/10 (60%) | ~160 |
| 23120219 (BFS) | Deterministic | 1/1 (100%) | 200 |

### Self-play (×5, stochastic, 1s timeout)

- Pacman wins: 4/5 (avg 26 steps)
- Ghost wins: 1/5 (survived 200 steps)
- **No timeouts recorded.**

### Resource Usage

| Resource | Budget | Actual |
|----------|--------|--------|
| Time per step | 1,000 ms | < 5 ms |
| Memory | 16 MB | < 3 KB agent state |

---

## 8. File Structure

```
my_agent_lab2/
├── agent.py            Main agent implementation (592 lines)
└── IMPLEMENTATION.md   This document
```

### Dependencies

Only built-in libraries + `numpy`:

```python
import sys, heapq, random
from pathlib import Path
from collections import deque
import numpy as np
```
