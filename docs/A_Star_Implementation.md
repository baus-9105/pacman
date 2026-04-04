# 22120016 Agent Implementation Notes

## Overview
This document explains the seeker agent implemented in agent.py for team 22120016.

Main goal:
- Catch the hider as fast as possible.

Core method:
- A* search with Manhattan heuristic.

Key competition-oriented improvements:
- Uses Pacman straight-line speed efficiently.
- Predicts likely future enemy positions for interception.
- Keeps memory across turns.
- Switches to exploration in fog when enemy is not visible.
- Uses anti-loop fallback behavior.

## What Was Implemented

### 1. Stateful Seek Agent Memory
The seeker stores useful state between turns:
- pacman_speed: max straight-line speed from arena config.
- last_known_enemy_pos: most recent visible enemy location.
- last_enemy_pos: previous visible position used for direction prediction.
- visited: dictionary counting visits per position.
- name: agent display name.

Why this matters:
- Better tracking under limited observation.
- Less repeated movement in dead ends.

### 2. A* Pathfinding Engine
A* is used to plan shortest routes on each decision.

Details:
- Priority queue based open set.
- g score for path cost.
- f score = g + Manhattan distance heuristic.
- Reconstructs move sequence from start to target.

Benefits:
- Faster convergence than uninformed search.
- Strong baseline in maze maps with walls.

### 3. Interception Through Enemy Motion Prediction
When enemy is visible:
- Current enemy location is used as a target.
- Additional predicted targets are generated from observed motion vector.
- Predictions look ahead up to several steps if cells remain valid.

Why this matters:
- Reduces chase lag against moving hiders.
- Often improves catch time versus pure direct pursuit.

### 4. Speed-Aware Action Compression
Arena allows the seeker to move multiple cells in one direction per turn.

Implemented behavior:
- Convert planned path into a legal action tuple: (Move, steps).
- Compress consecutive same-direction moves.
- Respect pacman_speed limit and wall constraints.

Why this matters:
- Uses full movement advantage.
- Reduces total turns to capture.

### 5. Fog-Aware Exploration Mode
When enemy is not visible:
- First, attempt to route to last known enemy position.
- If unavailable, find nearest unseen cells and route there.

Why this matters:
- Improves re-detection of hidden opponents.
- Avoids idle behavior in limited observation games.

### 6. Anti-Loop Fallback
If no planned action is available:
- Choose valid move with lower visit count.
- Prefer longer straight movement where possible.

Why this matters:
- Prevents repetitive local loops.
- Keeps pressure on the map.

## Decision Flow Per Turn
1. Update visit count for current position.
2. If enemy visible:
   - update memory,
   - generate predicted interception targets,
   - run A* and pick best target.
3. Else if last known enemy exists:
   - run A* to last known location.
4. Else explore nearest unseen regions using A*.
5. If all above fail, use anti-loop fallback move.

## Complexity Notes
Let V be reachable cells and E be edges.
- A* worst-case: O(E log V) due to heap operations.
- In this map size (21x21), runtime is safely within step limits.

## Rule Compliance
The implementation follows required rules:
- Class names unchanged.
- Method signatures unchanged.
- Pacman returns Move or (Move, steps).
- No external third-party libraries added.
- Uses standard library plus framework-provided imports.
