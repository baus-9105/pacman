# Implementation Documentation

---

## Table of Contents

1. [Overview](#overview)
2. [PacmanAgent (Seeker)](#pacmanagent-seeker)
3. [GhostAgent (Hider)](#ghostagent-hider)
4. [Shared Algorithms](#shared-algorithms)
5. [Design Decisions](#design-decisions)
6. [Complexity Analysis](#complexity-analysis)
7. [Testing](#testing)

---

## Overview

This agent implements advanced AI strategies for both the Pacman (seeker) and Ghost (hider) roles. The core philosophy:

- **Pacman**: "Predict, intercept, and corner" — don't chase where the Ghost *is*, chase where it *will be*.
- **Ghost**: "Maximise true distance, never get cornered" — use wall-aware BFS distance (not Manhattan), avoid dead-ends, stay near junctions.

Both agents use **depth-4 minimax** for close-combat decisions, with the Ghost adding **alpha-beta pruning** for efficiency.

### Architecture

```
step() is called each turn
  │
  ├── Enemy visible?
  │     ├── Close range  →  Minimax (adversarial lookahead)
  │     ├── Medium range →  A* / BFS-distance heuristics
  │     └── Far range    →  A* pathfinding / distance maximisation
  │
  ├── Enemy last known?
  │     └── Chase / flee from last known position
  │
  └── No info (fog)?
        └── Exploration / junction-seeking wander
```

---

## PacmanAgent (Seeker)

### Strategy Layers (highest priority first)

#### Layer 1: Minimax Close-Combat (Manhattan distance ≤ 8)

When the Ghost is within 8 tiles, Pacman uses **depth-4 minimax** to find the optimal capture move.

```
_minimax_chase(pac_pos, ghost_pos, map_state, depth=4)
  └── For each valid direction:
        ├── Simulate full-speed movement (pacman_speed steps)
        └── Evaluate with _mm_pac() minimax tree
              ├── Pacman turn: minimise distance (wants to get closer)
              └── Ghost turn: maximise distance (assumes Ghost plays optimally)
```

**Key design**: Pacman's root moves simulate the full `pacman_speed` (e.g., 2 tiles in a straight line), modelling the actual speed advantage. Deeper nodes use single-step moves for simplicity.

**Return value**: `(Move, steps)` tuple that exploits speed.

**Terminal condition**: `manhattan(pac, ghost) < 2` → capture (score = -1000).

#### Layer 2: Intercept Prediction (enemy visible, any range)

Instead of chasing the Ghost's *current* position, Pacman predicts where the Ghost will be:

```
_intercept_chase(pac_pos, ghost_pos, map_state)
  │
  ├── Target 1: Ghost's current position
  │
  ├── Targets 2-4: Linear extrapolation
  │     └── If Ghost moved (dr, dc) last turn, predict positions
  │         at ghost + k*(dr,dc) for k = 1,2,3
  │
  ├── Targets 5+: Flee-direction prediction
  │     └── Ghost likely moves to cells that INCREASE distance from Pacman
  │
  └── Pick the target with the SHORTEST A* path
```

**Why this works**: If the Ghost is running right, Pacman can cut it off by heading to a position 2-3 tiles ahead of the Ghost's trajectory.

#### Layer 3: Direct A* Chase

Standard A* pathfinding to the Ghost's position (or last known position if Ghost is hidden).

- Uses **Manhattan distance** as the heuristic (admissible, consistent)
- Returns optimal shortest path through the maze
- Path is **compressed** into a `(Move, steps)` tuple: consecutive same-direction moves are merged to exploit Pacman's speed multiplier

#### Layer 4: Fog Exploration

When the Ghost is not visible and no last-known position is available:

1. **Priority 1**: Find the nearest **unseen cell** (value = -1 in map_state) and A* to an empty cell adjacent to it — this systematically reveals fog
2. **Priority 2**: BFS flood-fill to find the **least-visited reachable cell**, scored as `visit_count * 50 + distance` — this ensures Pacman doesn't oscillate

#### Layer 5: Fallback

Pick the least-visited adjacent cell with a small random tiebreaker to avoid loops.

---

## GhostAgent (Hider)

### Strategy Layers

#### Layer 1: Minimax Evasion with Alpha-Beta (BFS distance ≤ 6)

When Pacman is dangerously close (within 6 BFS tiles), Ghost uses **depth-4 minimax with alpha-beta pruning**.

```
_minimax_evade(ghost_pos, pac_pos, map_state, depth=4)
  └── For each valid direction (including STAY):
        ├── Evaluate with _mm_ghost() minimax tree
        │     ├── Pacman turn: minimise score (wants to catch)
        │     └── Ghost turn: maximise score (wants to escape)
        │
        ├── Add bonus: +0.5 per exit at new position
        └── Add penalty: -20 if new position is a dead-end
```

**Evaluation function** (at leaf nodes):
```
score = BFS_distance(pac → ghost) × 2  +  exit_count(ghost) × 3
```

This evaluation combines:
- **BFS distance**: True wall-aware distance (not Manhattan) — a Ghost behind a wall is safer than one in an open corridor at the same Manhattan distance
- **Exit count**: Positions with more exits give the Ghost more escape options on future turns

**Alpha-beta pruning**: Cuts the search tree significantly. Worst case is O(5^4) = 625 nodes; alpha-beta typically prunes this to ~O(5^2) = 25 nodes.

#### Layer 2: BFS Distance Maximisation (standard evasion)

For each candidate move, compute a multi-factor score:

| Factor | Weight | Purpose |
|--------|--------|---------|
| `bfs_distance` | ×4 | Primary: true wall-aware distance from Pacman |
| `exit_count` | ×3 | Prefer junctions (3+ exits) for escape flexibility |
| `lookahead_2` | ×1.5 | Best BFS distance reachable in 2 moves |
| `dead_end_penalty` | -20 | **Never** walk into dead-ends (exits ≤ 1) |
| `corridor_penalty` | -3 | Avoid straight corridors (exits = 2) where Pacman can use speed |
| `repetition_penalty` | -3 | Don't repeat the same direction 3+ times consecutively |
| `visit_penalty` | ×-0.5 | Avoid revisiting cells |
| `random_tiebreaker` | +0.0-0.3 | Break score ties unpredictably |

**Why BFS distance instead of Manhattan?**

Manhattan distance ignores walls. A Ghost at Manhattan distance 5 from Pacman might actually be 15 BFS tiles away if there's a wall maze between them. Using BFS gives the Ghost an accurate picture of how much time it has before Pacman arrives.

**Why penalise corridors?**

With `pacman_speed = 2`, Pacman can cover 2 tiles per turn in a straight line. In a corridor (only 2 exits: forward and backward), Pacman's speed advantage is devastating. At junctions (3-4 exits), Pacman must choose a direction and can only move 1 tile before hitting a wall/turn, neutralising the speed advantage.

#### Layer 3: Anti-Prediction

The Ghost uses several techniques to remain unpredictable:

1. **Move repetition penalty**: If the Ghost has moved in the same direction for 3+ consecutive turns, that direction is penalised — preventing predictable straight-line movement
2. **Random tiebreaker**: When two moves score equally, a small random value (0.0–0.3) determines the choice — prevents Pacman from deterministically predicting the Ghost's behaviour
3. **Visit-count tracking**: The Ghost avoids cells it has visited many times, making its movement pattern non-repeating

#### Layer 4: Fog Wandering

When Pacman is not visible:
- Seek positions with **high connectivity** (many exits = junctions)
- Avoid revisiting cells
- Add controlled randomness for unpredictable patrol patterns

---

## Shared Algorithms

### A* Search (`_a_star`)

```
Input:  start position, goal position, map_state
Output: list of Move enums (optimal path), or None

Heuristic: Manhattan distance (admissible + consistent → optimal)
Data structures:
  - Min-heap priority queue: (f_score, g_score, counter, position)
  - g_score dict: shortest known distance to each node
  - parent dict: for path reconstruction
  - counter: tiebreaker for heap stability
```

**Optimisation**: Stale heap entries (where `g_score` has been updated since insertion) are skipped via the `cg != g.get(cur, cg)` check, avoiding the need for decrease-key operations.

### BFS Flood-Fill (`_bfs_distances`)

```
Input:  start position, map_state
Output: dict {position: distance} for all reachable cells

Uses: collections.deque for O(1) popleft
```

Computes the **true shortest-path distance** from `start` to every reachable cell, accounting for walls. This is the foundation for the Ghost's distance evaluation — far more accurate than Manhattan distance.

### Path Compression (`_compress_path`)

```
Input:  start position, A* path (list of Moves), map_state
Output: (first_move, steps) tuple

Merges consecutive same-direction moves up to pacman_speed.
Example: [RIGHT, RIGHT, DOWN, LEFT] with speed=2 → (RIGHT, 2)
```

This allows Pacman to exploit its speed multiplier: instead of returning `Move.RIGHT` (1 step), it returns `(Move.RIGHT, 2)` to cover 2 tiles in one turn.

---

## Design Decisions

### 1. `map_state[r, c] != 1` instead of `== 0`

Both agents treat **unseen cells** (value = -1, fog-of-war) as **walkable**. This is intentional:

- **Pacman**: Can path through fog to explore efficiently, rather than treating fog as impassable walls
- **Ghost**: Can flee into fog-covered areas, which is strategically valuable since Pacman loses sight

Other student submissions use `== 0`, which means they treat fog as walls and cannot path through unseen areas.

### 2. Minimax Depth = 4

Depth 4 provides 2 complete rounds of play (Pacman-Ghost-Pacman-Ghost). This is deep enough to detect:
- Imminent captures (Pacman closes in 2 turns)
- Cornering traps (Ghost moves to dead-end → caught next turn)
- Escape opportunities (Ghost finds a junction before Pacman arrives)

Depth 6 would be more accurate but risks timeout (1s limit per step). With alpha-beta pruning on the Ghost side, depth 4 evaluates ~25-100 nodes typically.

### 3. Ghost: BFS at Minimax Leaves

The minimax leaf evaluation runs a full BFS from Pacman's position. This is expensive but critical — it gives the Ghost an accurate assessment of whether a position is truly safe (behind walls) versus merely Manhattan-far but easily reachable.

### 4. Pacman: Speed-Aware Root Moves

In the Pacman minimax, root moves simulate the full `pacman_speed` steps, but inner tree nodes use single-step moves. This models reality accurately (Pacman does move multiple tiles per turn) while keeping the tree manageable.

---

## Complexity Analysis

### Per-Step Worst Case

| Operation | Pacman | Ghost |
|-----------|--------|-------|
| A* search | O(V log V) | — |
| BFS flood-fill | O(V) | O(V) |
| Minimax (depth 4) | O(4^4) = 256 nodes | O(5^4) = 625 nodes |
| Minimax + BFS leaves | — | 625 × O(V) |
| Alpha-beta pruning | — | Reduces to ~O(5^2) = 25 |

Where V ≈ 220 (empty cells in the 21×21 map).

**Practical timing**: On the default 21×21 map, each step completes well under the 1-second timeout, even in the worst case (Ghost minimax with BFS at every leaf).

---

## Testing

### Commands

```bash
# Test Pacman (antigravity) vs example Ghost
python arena.py --seek antigravity --hide example_student

# Test Ghost (antigravity) vs example Pacman  
python arena.py --seek example_student --hide antigravity

# Test Ghost (antigravity) vs A* Pacman (22120016)
python arena.py --seek 22120016 --hide antigravity

# Test both agents against each other
python arena.py --seek antigravity --hide antigravity

# Stress test with fog of war
python arena.py --seek antigravity --hide antigravity --pacman-obs-radius 5 --ghost-obs-radius 3
```

### Expected Results

| Match-up | Expected Winner | Reasoning |
|----------|----------------|-----------|
| Antigravity Pac vs Example Ghost | Pacman | A* + intercept easily catches greedy evader |
| Example Pac vs Antigravity Ghost | Ghost | BFS-distance + junction-seeking evades greedy chaser |
| A* Pac (22120016) vs Antigravity Ghost | Close match | Both use advanced algorithms; Ghost's anti-cornering helps |
| Antigravity Pac vs Antigravity Ghost | Depends | Minimax vs minimax — outcome depends on map topology |
