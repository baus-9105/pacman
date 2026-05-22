# 22120016: Hide and Seek Arena Implementation

## Overview

This document outlines the architecture, algorithms, and strategic implementations for the Seeker (Pacman) and Hider (Ghost) agents for Team 22120016.

Both agents are designed to excel under partial observability (Fog of War) and fully exploit the arena's movement mechanics (e.g., Pacman's straight-line speed multiplier). The implementation relies entirely on standard Python libraries (`numpy`, `heapq`, `collections`) to strictly adhere to the 1-second per step execution limit.

---

## 1. Pacman Agent (A* Hunter)

**Main Goal:** Intercept and capture the Ghost as efficiently as possible by predicting movement rather than strictly trailing behind.

### 1.1 Core Engine: A* Pathfinding

The core routing engine utilizes the **A* Search Algorithm** paired with a Manhattan distance heuristic. It efficiently finds the optimal path through the maze structure while avoiding walls (`1`). Priority queues (`heapq`) are used to maintain low computational overhead.

### 1.2 Interception & Motion Prediction

Instead of exclusively targeting the Ghost's current cell, the agent calculates an interception trajectory.

* **Velocity Tracking:** The agent stores the `last_enemy_pos` to calculate the Ghost's current directional vector.
* **Lookahead Targets:** It projects 1 to 3 steps ahead along this vector to generate candidate interception points.
* **Optimal Selection:** It evaluates paths to all candidate targets and selects the route that yields the fastest interception.

### 1.3 Speed-Aware Action Compression

To capitalize on the `pacman_speed` advantage, the agent does not output single moves.

* Once an A* path is generated, the `_compress_path_to_action` module scans the path for consecutive moves in the same direction.
* It packages these into a single `(Move, steps)` tuple, allowing Pacman to bound across the map and drastically reduce total turns to capture.

### 1.4 Fog of War & Exploration Handling

When the Ghost falls out of the observable radius, the agent degrades gracefully through a priority system:

1. **Last Known Position:** Routes to the exact cell where the Ghost was last sighted.
2. **Nearest Unseen Territory:** If the last known location is reached and the Ghost is still hidden, it identifies the nearest completely unobserved cells (`-1`) and uses A* to navigate toward them, sweeping the map systematically.
3. **Anti-Loop Fallback:** If trapped, it defaults to the least-visited valid adjacent cell.

---

## 2. Ghost Agent (Risk-Aware BFS Hider)

**Main Goal:** Maximize survival time by prioritizing high-mobility zones and true-distance separation, avoiding the common pitfalls of Manhattan-based evasion.

### 2.1 Core Engine: True BFS Distance Mapping

A critical flaw in standard Manhattan distance is that it ignores walls—two cells might be physically adjacent but separated by a long wall.

* The Ghost agent implements `_multi_source_distance_map`, which uses a **Breadth-First Search (BFS)** flood-fill to calculate the *actual* step distance from all cells Pacman can reach in the current turn.
* This ensures the Ghost never accidentally traps itself in a dead-end that "looks" mathematically far away but is functionally a trap.

### 2.2 Risk-Aware State Evaluation

For every decision tick, the Ghost simulates moving to all adjacent valid cells. It then scores each resulting state using a weighted evaluation function:

$$Score = (30.0 \times \text{Nearest Threat}) + (0.8 \times \text{Safe Area}) + (6.0 \times \text{Exits}) - (2.0 \times \text{Visits}) - \text{Reverse Penalty}$$

* **Nearest Threat:** The True BFS distance from Pacman's immediate reach zone. (Highest priority)
* **Safe Area Size:** An estimate of how many connected cells remain safe (distance > 2) from this position, ensuring long-term survivability.
* **Exit Count (Mobility):** Prioritizes junctions and intersections over straight corridors, neutralizing Pacman's straight-line speed advantage.
* **Visit & Reverse Penalties:** Deducts points for backtracking or stepping on recently visited cells, preventing predictable oscillation.

### 2.3 Fog Exploration

When Pacman is out of sight, the Ghost does not stay idle. It transitions into an exploration mode that prioritizes moving toward highly connected junctions (maximizing exit counts) while maintaining a strict anti-loop penalty to ensure it continuously drifts through the maze.

---

## 3. Complexity Analysis

* **Pacman (A* Search):** $O(E \log V)$ worst-case per pathfinding call. Given the small grid size ($21 \times 21$), heap operations resolve almost instantaneously.
* **Ghost (BFS Evaluation):** $O(V + E)$ for the flood-fill distance mapping. Executing this up to 5 times per step (once for each potential move) scales linearly and safely executes within the ~1000 node limit of the arena, well under the 1-second constraint.