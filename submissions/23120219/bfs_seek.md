# Pacman Agent - BFS Implementation

## Overview
This Pacman agent uses a Breadth-First Search (BFS) strategy to chase the ghost in a grid-based environment. The agent recomputes the shortest path at every step to adapt to the ghost's movement.

## Core Components

### Neighbor Expansion
The agent generates all valid neighboring positions (up, down, left, right) that are not walls and within map bounds.

To avoid deterministic behavior, the neighbor list is randomly shuffled before exploration.

### BFS Pathfinding
The agent applies BFS to find the shortest path from its current position to the target:

- Uses a queue (FIFO) to explore positions level by level.
- Maintains a visited set to avoid revisiting nodes.
- Returns the sequence of moves once the target is reached.
- Guarantees shortest path in an unweighted grid.

## Step Function Logic

At each step:

1. Update memory:
   - If the ghost is visible, store its position.

2. Determine target:
   - Use current ghost position if available.
   - Otherwise, use the last known position.

3. Handle missing information:
   - If no target is known, Pacman stays in place.

4. Path planning:
   - Run BFS from current position to target.

5. Movement:
   - Execute only the first move in the path.
   - Move exactly 1 step to ensure path consistency.

## Design Choices

- **Recompute BFS every step**: ensures adaptability to moving targets.
- **Single-step movement**: avoids invalid paths when the ghost changes direction.
- **Memory usage**: allows tracking the ghost even when it is temporarily not visible.
- **Randomized neighbor order**: reduces repetitive movement patterns.

## Advantages

- Always finds the shortest path to the target.
- Simple and reliable behavior.
- Works well in dynamic environments with moving enemies.

## Limitations

- Does not predict future ghost movement.
- May be less efficient due to recomputing BFS every step.
- Purely reactive (no long-term strategy).