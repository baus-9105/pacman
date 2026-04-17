"""
Template for student agent implementation.

INSTRUCTIONS:
1. Copy this file to submissions/<your_student_id>/agent.py
2. Implement the PacmanAgent and/or GhostAgent classes
3. Replace the simple logic with your search algorithm
4. Test your agent using: python arena.py --seek <your_id> --hide example_student

IMPORTANT:
- Do NOT change the class names (PacmanAgent, GhostAgent)
- Do NOT change the method signatures (step, __init__)
- Pacman step must return either a Move or a (Move, steps) tuple where
    1 <= steps <= pacman_speed (provided via kwargs)
- Ghost step must return a Move enum value
- You CAN add your own helper methods
- You CAN import additional Python standard libraries
- Agents are STATEFUL - you can store memory across steps
- enemy_position may be None when limited observation is enabled
- map_state cells: 1=wall, 0=empty, -1=unseen (fog)
"""

import sys
from pathlib import Path

# Add src to path to import the interface
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from agent_interface import PacmanAgent as BasePacmanAgent
from agent_interface import GhostAgent as BaseGhostAgent
from environment import Move
import numpy as np

from collections import deque
import heapq
import random


class PacmanAgent(BasePacmanAgent):
    """
    Pacman (Seeker) Agent - Goal: Catch the Ghost

    Strategy layers (highest priority first):
      1. Minimax close-combat (dist <= 8) — accounts for Pacman speed
      2. A* with ghost-interception prediction
      3. Direct A* chase to ghost / last known position
      4. Systematic fog exploration via BFS to unseen cells
      5. Visit-count fallback to avoid oscillation
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pacman_speed = max(1, int(kwargs.get("pacman_speed", 1)))
        self.name = "WAG Pacman"
        # Memory for limited observation mode
        self.last_known_enemy_pos = None
        self.prev_enemy_pos = None
        self.visited = {}

    def step(self, map_state: np.ndarray,
             my_position: tuple,
             enemy_position: tuple,
             step_number: int):
        """
        Decide the next move.

        Args:
            map_state: 2D numpy array where 1=wall, 0=empty, -1=unseen (fog)
            my_position: Your current (row, col) in absolute coordinates
            enemy_position: Ghost's (row, col) if visible, None otherwise
            step_number: Current step number (starts at 1)

        Returns:
            Move or (Move, steps): Direction to move (optionally with step count)
        """
        self.visited[my_position] = self.visited.get(my_position, 0) + 1

        # Update memory if enemy is visible
        if enemy_position is not None:
            self.prev_enemy_pos = self.last_known_enemy_pos
            self.last_known_enemy_pos = enemy_position

        # --- Enemy visible: pursue aggressively ---
        if enemy_position is not None:
            dist = self._manhattan(my_position, enemy_position)

            # Close combat: minimax for precise capture
            if dist <= 8:
                action = self._minimax_chase(
                    my_position, enemy_position, map_state, depth=4
                )
                if action is not None:
                    return action

            # Medium range: intercept predicted ghost positions
            action = self._intercept_chase(
                my_position, enemy_position, map_state
            )
            if action is not None:
                return action

            # Direct A* fallback
            action = self._a_star_chase(my_position, enemy_position, map_state)
            if action is not None:
                return action

        # --- Chase last known position ---
        if self.last_known_enemy_pos is not None:
            action = self._a_star_chase(
                my_position, self.last_known_enemy_pos, map_state
            )
            if action is not None:
                return action

        # --- Explore unseen / least-visited areas ---
        action = self._explore(my_position, map_state)
        if action is not None:
            return action

        return self._fallback_move(my_position, map_state)

    # ── Minimax close-combat ─────────────────────────────

    def _minimax_chase(self, pac, ghost, map_state, depth):
        """Pacman minimises distance via depth-limited minimax."""
        best_action = None
        best_score = float('inf')

        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            steps = self._max_valid_steps(pac, move, map_state, self.pacman_speed)
            if steps <= 0:
                continue
            # Simulate full speed move
            new_pac = self._simulate_steps(pac, move, map_state, steps)
            score = self._mm_pac(new_pac, ghost, map_state, depth - 1, False)
            if score < best_score:
                best_score = score
                best_action = (move, steps)

        return best_action

    def _mm_pac(self, pac, ghost, map_state, depth, is_pac_turn):
        """Minimax eval — Pacman minimises, Ghost maximises distance."""
        if self._manhattan(pac, ghost) < 2:
            return -1000
        if depth <= 0:
            return self._manhattan(pac, ghost)

        if is_pac_turn:
            best = float('inf')
            for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
                nxt = self._apply_move(pac, move)
                if self._is_valid_position(nxt, map_state):
                    best = min(best, self._mm_pac(nxt, ghost, map_state, depth - 1, False))
            return best
        else:
            best = -float('inf')
            for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT, Move.STAY]:
                nxt = self._apply_move(ghost, move)
                if not self._is_valid_position(nxt, map_state):
                    continue
                best = max(best, self._mm_pac(pac, nxt, map_state, depth - 1, True))
            return best

    # ── Intercept predicted ghost path ───────────────────

    def _intercept_chase(self, pac, ghost, map_state):
        """Target ghost's predicted future positions for interception."""
        targets = [ghost]

        # Linear extrapolation from previous position
        if self.prev_enemy_pos is not None:
            dr = ghost[0] - self.prev_enemy_pos[0]
            dc = ghost[1] - self.prev_enemy_pos[1]
            if dr != 0 or dc != 0:
                r, c = ghost
                for k in range(1, 4):
                    p = (r + dr * k, c + dc * k)
                    if self._is_valid_position(p, map_state):
                        targets.append(p)
                    else:
                        break

        # Ghost likely flees AWAY from Pacman
        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            nxt = self._apply_move(ghost, move)
            if (self._is_valid_position(nxt, map_state)
                    and self._manhattan(nxt, pac) > self._manhattan(ghost, pac)):
                if nxt not in targets:
                    targets.append(nxt)

        # Pick the target reachable with the shortest A* path
        best_action, best_len = None, float('inf')
        for t in targets:
            path = self._a_star(pac, t, map_state)
            if path is not None and len(path) < best_len:
                best_len = len(path)
                best_action = self._compress_path(pac, path, map_state)
        return best_action

    # ── Direct A* chase ──────────────────────────────────

    def _a_star_chase(self, start, target, map_state):
        """Chase a target using A* pathfinding."""
        path = self._a_star(start, target, map_state)
        if path:
            return self._compress_path(start, path, map_state)
        return None

    # ── Fog exploration ──────────────────────────────────

    def _explore(self, pos, map_state):
        """Explore toward unseen cells, or visit least-visited areas."""
        h, w = map_state.shape

        # Priority 1: BFS to nearest empty cell adjacent to unseen fog
        unseen = []
        for r in range(h):
            for c in range(w):
                if map_state[r, c] == -1:
                    unseen.append((self._manhattan(pos, (r, c)), r, c))
        if unseen:
            unseen.sort()
            for _, r, c in unseen[:20]:
                for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
                    adj = self._apply_move((r, c), move)
                    if (self._is_valid_position(adj, map_state)
                            and map_state[adj[0], adj[1]] == 0):
                        path = self._a_star(pos, adj, map_state)
                        if path:
                            return self._compress_path(pos, path, map_state)

        # Priority 2: least-visited reachable cell
        bfs = self._bfs_distances(pos, map_state)
        best_target, best_score = None, float('inf')
        for cell, dist in bfs.items():
            if dist == 0:
                continue
            score = self.visited.get(cell, 0) * 50 + dist
            if score < best_score:
                best_score = score
                best_target = cell
        if best_target:
            path = self._a_star(pos, best_target, map_state)
            if path:
                return self._compress_path(pos, path, map_state)
        return None

    # ── Fallback ─────────────────────────────────────────

    def _fallback_move(self, pos, map_state):
        """Emergency: pick least-visited adjacent cell."""
        candidates = []
        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            nxt = self._apply_move(pos, move)
            if self._is_valid_position(nxt, map_state):
                visits = self.visited.get(nxt, 0)
                candidates.append((visits, random.random(), move))
        if candidates:
            candidates.sort()
            m = candidates[0][2]
            steps = self._max_valid_steps(pos, m, map_state, self.pacman_speed)
            return (m, max(1, steps))
        return (Move.STAY, 1)

    # ── Core algorithms ──────────────────────────────────

    def _a_star(self, start, goal, map_state):
        """A* search returning list of Move enums, or None."""
        if start == goal:
            return []
        heap = []
        g = {start: 0}
        parent = {}
        mfrom = {}
        cnt = 0
        heapq.heappush(heap, (self._manhattan(start, goal), 0, cnt, start))
        while heap:
            _, cg, _, cur = heapq.heappop(heap)
            if cur == goal:
                path = []
                while cur in parent:
                    path.append(mfrom[cur])
                    cur = parent[cur]
                path.reverse()
                return path
            if cg != g.get(cur, cg):
                continue
            for d in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
                n = self._apply_move(cur, d)
                if not self._is_valid_position(n, map_state):
                    continue
                ng = cg + 1
                if ng < g.get(n, 1 << 30):
                    g[n] = ng
                    parent[n] = cur
                    mfrom[n] = d
                    cnt += 1
                    heapq.heappush(heap, (ng + self._manhattan(n, goal), ng, cnt, n))
        return None

    def _bfs_distances(self, start, map_state):
        """BFS flood-fill returning {pos: distance}."""
        dist = {start: 0}
        q = deque([start])
        while q:
            p = q.popleft()
            d = dist[p]
            for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
                n = self._apply_move(p, move)
                if self._is_valid_position(n, map_state) and n not in dist:
                    dist[n] = d + 1
                    q.append(n)
        return dist

    def _compress_path(self, start, path, map_state):
        """Compress consecutive same-direction moves into (Move, steps)."""
        if not path:
            return None
        first = path[0]
        steps, cur = 0, start
        for m in path:
            if m != first or steps >= self.pacman_speed:
                break
            nxt = self._apply_move(cur, m)
            if not self._is_valid_position(nxt, map_state):
                break
            cur = nxt
            steps += 1
        return (first, steps) if steps > 0 else None

    def _simulate_steps(self, pos, move, map_state, steps):
        """Simulate multi-step movement, stopping at walls."""
        cur = pos
        for _ in range(steps):
            nxt = self._apply_move(cur, move)
            if self._is_valid_position(nxt, map_state):
                cur = nxt
            else:
                break
        return cur

    # ── Helper methods (from template) ───────────────────

    def _max_valid_steps(self, pos: tuple, move: Move, map_state: np.ndarray, max_steps: int) -> int:
        steps = 0
        current = pos
        for _ in range(max_steps):
            delta_row, delta_col = move.value
            next_pos = (current[0] + delta_row, current[1] + delta_col)
            if not self._is_valid_position(next_pos, map_state):
                break
            steps += 1
            current = next_pos
        return steps

    def _is_valid_move(self, pos: tuple, move: Move, map_state: np.ndarray) -> bool:
        """Check if a move from pos is valid for at least one step."""
        return self._max_valid_steps(pos, move, map_state, 1) == 1

    def _is_valid_position(self, pos: tuple, map_state: np.ndarray) -> bool:
        """Check if a position is valid (not a wall and within bounds)."""
        row, col = pos
        height, width = map_state.shape
        if row < 0 or row >= height or col < 0 or col >= width:
            return False
        return map_state[row, col] != 1  # walkable: empty (0) or unseen (-1)

    def _apply_move(self, pos, move):
        dr, dc = move.value
        return (pos[0] + dr, pos[1] + dc)

    def _manhattan(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])


class GhostAgent(BaseGhostAgent):
    """
    Ghost (Hider) Agent - Goal: Avoid being caught

    Strategy layers:
      1. Minimax evasion (BFS dist <= 6) with alpha-beta pruning
      2. BFS-distance maximisation (true wall-aware distance, not Manhattan)
         - Heavily penalises dead-ends (exits <= 1)
         - Prefers junctions (exits >= 3) for escape flexibility
         - 2-step lookahead for sustained distance
         - Accounts for Pacman speed in danger assessment
      3. Anti-prediction: controlled randomness + move-repeat penalty
      4. Fog wandering: seek high-connectivity junctions
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "WAG Ghost"
        # Memory for limited observation mode
        self.last_known_enemy_pos = None
        self.prev_moves = []
        self.visited = {}

    def step(self, map_state: np.ndarray,
             my_position: tuple,
             enemy_position: tuple,
             step_number: int) -> Move:
        """
        Decide the next move.

        Args:
            map_state: 2D numpy array where 1=wall, 0=empty, -1=unseen (fog)
            my_position: Your current (row, col) in absolute coordinates
            enemy_position: Pacman's (row, col) if visible, None otherwise
            step_number: Current step number (starts at 1)

        Returns:
            Move: One of Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT, Move.STAY
        """
        self.visited[my_position] = self.visited.get(my_position, 0) + 1

        # Update memory if enemy is visible
        if enemy_position is not None:
            self.last_known_enemy_pos = enemy_position

        threat = enemy_position or self.last_known_enemy_pos

        # No threat info: wander toward junctions
        if threat is None:
            return self._smart_wander(my_position, map_state)

        # Compute BFS distance map FROM Pacman (wall-aware true distance)
        pac_dist = self._bfs_distances(threat, map_state)
        my_bfs_dist = pac_dist.get(my_position, 0)

        # DANGER ZONE: minimax evasion with alpha-beta
        if my_bfs_dist <= 6:
            action = self._minimax_evade(
                my_position, threat, map_state, depth=4
            )
            if action is not None:
                self._record_move(action)
                return action

        # Standard: maximise BFS distance with heuristics
        return self._maximise_distance(my_position, threat, map_state, pac_dist)

    # ── Minimax evasion ──────────────────────────────────

    def _minimax_evade(self, ghost, pac, map_state, depth):
        """Ghost maximises distance via minimax with alpha-beta pruning."""
        best_move = Move.STAY
        best_score = -float('inf')
        alpha = -float('inf')
        beta = float('inf')

        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT, Move.STAY]:
            nxt = self._apply_move(ghost, move)
            if not self._is_valid_position(nxt, map_state):
                continue

            score = self._mm_ghost(
                pac, nxt, map_state, depth - 1, True, alpha, beta
            )
            # Bonus for escape routes at new position
            score += self._count_exits(nxt, map_state) * 0.5
            # Penalty for dead-ends
            if self._count_exits(nxt, map_state) <= 1:
                score -= 20

            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)

        return best_move

    def _mm_ghost(self, pac, ghost, map_state, depth, is_pac_turn, alpha, beta):
        """Minimax: Pacman minimises dist, Ghost maximises. Alpha-beta pruned."""
        if self._manhattan(pac, ghost) < 2:
            return -1000  # caught = worst for ghost

        if depth <= 0:
            # Evaluation: BFS distance + escape routes
            bfs = self._bfs_distances(pac, map_state)
            bfs_dist = bfs.get(ghost, 50)
            exits = self._count_exits(ghost, map_state)
            return bfs_dist * 2 + exits * 3

        if is_pac_turn:
            # Pacman minimises — also model Pacman speed by allowing 2-step
            best = float('inf')
            for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
                nxt = self._apply_move(pac, move)
                if not self._is_valid_position(nxt, map_state):
                    continue
                score = self._mm_ghost(
                    nxt, ghost, map_state, depth - 1, False, alpha, beta
                )
                best = min(best, score)
                beta = min(beta, best)
                if beta <= alpha:
                    break
            return best
        else:
            best = -float('inf')
            for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT, Move.STAY]:
                nxt = self._apply_move(ghost, move)
                if not self._is_valid_position(nxt, map_state):
                    continue
                score = self._mm_ghost(
                    pac, nxt, map_state, depth - 1, True, alpha, beta
                )
                best = max(best, score)
                alpha = max(alpha, best)
                if beta <= alpha:
                    break
            return best

    # ── BFS distance maximisation ────────────────────────

    def _maximise_distance(self, pos, pac, map_state, pac_dist):
        """Choose the move that maximises wall-aware BFS distance from Pacman."""
        candidates = []

        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            nxt = self._apply_move(pos, move)
            if not self._is_valid_position(nxt, map_state):
                continue

            # Primary: BFS distance from Pacman (wall-aware, not Manhattan)
            bfs_d = pac_dist.get(nxt, 0)

            # Secondary: escape routes (connectivity)
            exits = self._count_exits(nxt, map_state)

            # Tertiary: 2-step lookahead — best BFS distance reachable next turn
            look2 = bfs_d
            for m2 in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
                nxt2 = self._apply_move(nxt, m2)
                if self._is_valid_position(nxt2, map_state):
                    look2 = max(look2, pac_dist.get(nxt2, 0))

            # Dead-end penalty: NEVER walk into dead-ends
            dead_pen = -20 if exits <= 1 else 0

            # Corridor penalty: positions with only 2 exits (straight line)
            # let Pacman use speed — prefer junctions
            corridor_pen = -3 if exits == 2 else 0

            # Anti-repetition: penalise repeating same direction 3+ times
            rep_pen = 0
            if (len(self.prev_moves) >= 2
                    and self.prev_moves[-1] == move
                    and self.prev_moves[-2] == move):
                rep_pen = -3

            # Visit penalty: avoid revisiting cells
            visit_pen = -self.visited.get(nxt, 0) * 0.5

            score = (bfs_d * 4
                     + exits * 3
                     + look2 * 1.5
                     + dead_pen
                     + corridor_pen
                     + rep_pen
                     + visit_pen
                     + random.random() * 0.3)  # small random tiebreaker

            candidates.append((score, move))

        if candidates:
            candidates.sort(reverse=True)
            best = candidates[0][1]
        else:
            best = Move.STAY

        self._record_move(best)
        return best

    # ── Fog wandering ────────────────────────────────────

    def _smart_wander(self, pos, map_state):
        """When Pacman is invisible, wander toward high-connectivity junctions."""
        best_move = Move.STAY
        best_score = -float('inf')

        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            nxt = self._apply_move(pos, move)
            if not self._is_valid_position(nxt, map_state):
                continue

            exits = self._count_exits(nxt, map_state)
            score = exits * 3.0

            # Avoid revisiting
            score -= self.visited.get(nxt, 0) * 0.5

            # Anti-repetition
            if self.prev_moves and self.prev_moves[-1] == move:
                score -= 0.5

            # Small randomness for unpredictability
            score += random.random() * 0.5

            if score > best_score:
                best_score = score
                best_move = move

        self._record_move(best_move)
        return best_move

    # ── Core algorithms ──────────────────────────────────

    def _bfs_distances(self, start, map_state):
        """BFS flood-fill returning {pos: distance}."""
        dist = {start: 0}
        q = deque([start])
        while q:
            p = q.popleft()
            d = dist[p]
            for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
                n = self._apply_move(p, move)
                if self._is_valid_position(n, map_state) and n not in dist:
                    dist[n] = d + 1
                    q.append(n)
        return dist

    def _count_exits(self, pos, map_state):
        """Count number of valid moves from a position."""
        count = 0
        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            nxt = self._apply_move(pos, move)
            if self._is_valid_position(nxt, map_state):
                count += 1
        return count

    def _record_move(self, move):
        """Track recent moves for anti-repetition."""
        self.prev_moves.append(move)
        if len(self.prev_moves) > 10:
            self.prev_moves.pop(0)

    # ── Helper methods (from template) ───────────────────

    def _is_valid_move(self, pos: tuple, move: Move, map_state: np.ndarray) -> bool:
        """Check if a move from pos is valid."""
        delta_row, delta_col = move.value
        new_pos = (pos[0] + delta_row, pos[1] + delta_col)
        return self._is_valid_position(new_pos, map_state)

    def _is_valid_position(self, pos: tuple, map_state: np.ndarray) -> bool:
        """Check if a position is valid (not a wall and within bounds)."""
        row, col = pos
        height, width = map_state.shape
        if row < 0 or row >= height or col < 0 or col >= width:
            return False
        return map_state[row, col] != 1  # walkable: empty (0) or unseen (-1)

    def _apply_move(self, pos, move):
        dr, dc = move.value
        return (pos[0] + dr, pos[1] + dc)

    def _manhattan(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
