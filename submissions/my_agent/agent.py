"""
Hide and Seek Arena – Agent Implementation

PacmanAgent (Seek): A* search with speed-2 straight-line optimization.
GhostAgent (Hide): Risk-aware BFS distance maximization with minimax
                   lookahead for close-range encounters.

Allowed libraries: builtins, numpy, pandas, scipy, gurobi.
Time budget: < 1 second per step.
"""

import sys
from pathlib import Path
from collections import deque
import heapq
import random

# Add src to path to import the interface
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from agent_interface import PacmanAgent as BasePacmanAgent
from agent_interface import GhostAgent as BaseGhostAgent
from environment import Move
import numpy as np

# ──────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────

ALL_MOVES = [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]

OPPOSITE = {
    Move.UP: Move.DOWN, Move.DOWN: Move.UP,
    Move.LEFT: Move.RIGHT, Move.RIGHT: Move.LEFT,
    Move.STAY: Move.STAY,
}


def is_valid(pos, map_state):
    """Check if a position is traversable (in-bounds and not a wall)."""
    r, c = pos
    h, w = map_state.shape
    return 0 <= r < h and 0 <= c < w and map_state[r, c] == 0


def apply_move(pos, move):
    """Return the position after applying a single-step move."""
    dr, dc = move.value
    return (pos[0] + dr, pos[1] + dc)


def get_neighbors(pos, map_state):
    """Yield (next_pos, move) for every valid cardinal neighbor."""
    for move in ALL_MOVES:
        nxt = apply_move(pos, move)
        if is_valid(nxt, map_state):
            yield nxt, move


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def bfs_distances(origin, map_state):
    """BFS from *origin*; return dict {pos: distance}."""
    dist = {origin: 0}
    queue = deque([origin])
    while queue:
        pos = queue.popleft()
        d = dist[pos]
        for nxt, _ in get_neighbors(pos, map_state):
            if nxt not in dist:
                dist[nxt] = d + 1
                queue.append(nxt)
    return dist


def pacman_turn_distances(origin, map_state):
    """
    BFS that models Pacman's speed-2 movement.
    At each 'turn', Pacman can move 1 cell in any direction, OR 2 cells in
    a straight line (if the intermediate cell is also valid).
    Returns dict {pos: min_turns_to_reach}.
    """
    dist = {origin: 0}
    queue = deque([origin])
    while queue:
        pos = queue.popleft()
        d = dist[pos]
        for move in ALL_MOVES:
            # 1-step
            p1 = apply_move(pos, move)
            if is_valid(p1, map_state) and p1 not in dist:
                dist[p1] = d + 1
                queue.append(p1)
            # 2-step straight line
            if is_valid(p1, map_state):
                p2 = apply_move(p1, move)
                if is_valid(p2, map_state) and p2 not in dist:
                    dist[p2] = d + 1
                    queue.append(p2)
    return dist


def a_star(start, goal, map_state):
    """
    A* search returning list[Move] from *start* to *goal*.
    Returns [] if goal == start, or if no path exists.
    """
    if start == goal:
        return []
    counter = 0
    open_set = [(manhattan(start, goal), counter, start, [])]
    g_scores = {start: 0}
    while open_set:
        _, _, cur, path = heapq.heappop(open_set)
        if cur == goal:
            return path
        cur_g = g_scores[cur]
        for nxt, move in get_neighbors(cur, map_state):
            ng = cur_g + 1
            if ng < g_scores.get(nxt, float("inf")):
                g_scores[nxt] = ng
                counter += 1
                heapq.heappush(
                    open_set,
                    (ng + manhattan(nxt, goal), counter, nxt, path + [move]),
                )
    return []


# ══════════════════════════════════════════════════════════════════════
#  PACMAN AGENT  –  A* Seek with speed-2 optimization
# ══════════════════════════════════════════════════════════════════════

class PacmanAgent(BasePacmanAgent):
    """
    Seek agent that uses A* pathfinding with optimal speed-2 utilization.

    Strategy
    --------
    1. A* to find shortest maze path to the ghost.
    2. Move 2 cells when consecutive path moves share the same direction.
    3. When the ghost is invisible (fog-of-war), explore systematically
       toward the farthest unvisited reachable cell.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pacman_speed = max(1, int(kwargs.get("pacman_speed", 1)))
        self.last_known_enemy_pos = None
        self.visited = set()
        self.exploration_target = None

    # ── main entry ────────────────────────────────────────────────────

    def step(self, map_state, my_position, enemy_position, step_number):
        self.visited.add(my_position)

        # Update memory
        if enemy_position is not None:
            self.last_known_enemy_pos = enemy_position
            self.exploration_target = None

        target = enemy_position or self.last_known_enemy_pos

        if target is None:
            return self._explore(my_position, map_state)

        # A* toward target
        path = a_star(my_position, target, map_state)
        if not path:
            return self._greedy_toward(my_position, target, map_state)

        return self._speed_action(my_position, path, map_state)

    # ── speed-2 action builder ────────────────────────────────────────

    def _speed_action(self, pos, path, map_state):
        """Build (Move, steps) exploiting speed-2 on straight segments."""
        move = path[0]
        steps = 1
        if self.pacman_speed >= 2 and len(path) >= 2 and path[1] == move:
            p1 = apply_move(pos, move)
            p2 = apply_move(p1, move)
            if is_valid(p1, map_state) and is_valid(p2, map_state):
                steps = 2
        return (move, steps)

    # ── exploration (fog-of-war / invisible ghost) ────────────────────

    def _explore(self, pos, map_state):
        if self.exploration_target is None or self.exploration_target == pos:
            self.exploration_target = self._farthest_unvisited(pos, map_state)
        if self.exploration_target:
            path = a_star(pos, self.exploration_target, map_state)
            if path:
                return self._speed_action(pos, path, map_state)
        # fallback – any valid move
        moves = list(ALL_MOVES)
        random.shuffle(moves)
        for m in moves:
            if is_valid(apply_move(pos, m), map_state):
                return (m, 1)
        return (Move.STAY, 1)

    def _farthest_unvisited(self, pos, map_state):
        """BFS to find the farthest reachable cell not yet visited."""
        queue = deque([(pos, 0)])
        seen = {pos}
        best, best_d = None, -1
        while queue:
            cur, d = queue.popleft()
            if cur not in self.visited and d > best_d:
                best, best_d = cur, d
            for nxt, _ in get_neighbors(cur, map_state):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, d + 1))
        return best

    # ── greedy fallback ───────────────────────────────────────────────

    def _greedy_toward(self, pos, target, map_state):
        best_move, best_d = Move.STAY, manhattan(pos, target)
        for nxt, m in get_neighbors(pos, map_state):
            d = manhattan(nxt, target)
            if d < best_d:
                best_d, best_move = d, m
        return (best_move, 1)


# ══════════════════════════════════════════════════════════════════════
#  GHOST AGENT  –  Risk-Aware Hide with minimax close-range defence
# ══════════════════════════════════════════════════════════════════════

class GhostAgent(BaseGhostAgent):
    """
    Hide agent that adapts strategy based on threat distance.

    Strategy layers (evaluated every step)
    ---------------------------------------
    * **PANIC** (Pacman ≤ 4 turns away):
        2-ply minimax – simulate Pacman's best speed-2 response for each
        of our candidate moves; pick the move whose *worst-case* resulting
        distance is highest.

    * **CAUTION** (Pacman 5–10 turns away):
        Score each move by a weighted combination of:
          – BFS distance from Pacman (accounts for walls & speed-2)
          – number of escape routes at the destination
          – anti-oscillation bonus

    * **CALM** (Pacman > 10 turns away):
        Move toward the cell with the highest Pacman-turn-distance that
        still has ≥ 2 escape exits (avoid trapping ourselves in dead-ends).
    """

    # Threat-level thresholds (in Pacman turns, NOT cells)
    PANIC_THRESHOLD = 6
    CAUTION_THRESHOLD = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_known_enemy_pos = None
        self.last_move = None
        self._haven_target = None
        self._last_pac_pos = None

    # ── main entry ────────────────────────────────────────────────────

    def step(self, map_state, my_position, enemy_position, step_number):
        # Memory update
        if enemy_position is not None:
            self._last_pac_pos = self.last_known_enemy_pos
            self.last_known_enemy_pos = enemy_position

        threat = enemy_position or self.last_known_enemy_pos

        if threat is None:
            return self._wander(my_position, map_state)

        # Pacman-turn distance map (accounts for speed-2)
        ptd = pacman_turn_distances(threat, map_state)
        my_turn_dist = ptd.get(my_position, 999)

        # Invalidate haven when Pacman gets closer
        if self._haven_target and ptd.get(self._haven_target, 999) < my_turn_dist:
            self._haven_target = None

        if my_turn_dist <= self.PANIC_THRESHOLD:
            move = self._panic(my_position, threat, map_state, ptd)
        elif my_turn_dist <= self.CAUTION_THRESHOLD:
            move = self._caution(my_position, threat, map_state, ptd)
        else:
            move = self._calm(my_position, threat, map_state, ptd)

        self.last_move = move
        return move

    # ── PANIC: 2-ply minimax with BFS maze distance ──────────────────

    def _panic(self, my_pos, pac_pos, map_state, ptd):
        """
        2-ply minimax: for each ghost move, simulate every Pacman speed-2
        response; then for each resulting state, simulate every ghost
        follow-up and every Pacman response again.  Pick the ghost move
        whose worst-case BFS maze distance is maximized.

        Falls back to 1-ply if the full 2-ply would be too slow.
        """
        pac_nexts = self._pacman_next_positions(pac_pos, map_state)

        # Ghost candidate moves (including STAY)
        g_candidates = [(my_pos, Move.STAY)]
        for nxt, m in get_neighbors(my_pos, map_state):
            g_candidates.append((nxt, m))

        best_move = Move.STAY
        best_score = -float("inf")

        for g1_pos, g1_move in g_candidates:
            # Worst-case over Pacman's first response
            min_over_pac = float("inf")
            for p1_pos in pac_nexts:
                # If already caught, score is -inf
                if manhattan(p1_pos, g1_pos) < 2:
                    min_over_pac = -100
                    break
                # Ghost's 2nd ply: best follow-up
                g2_cands = [g1_pos]  # STAY
                for g2nxt, _ in get_neighbors(g1_pos, map_state):
                    g2_cands.append(g2nxt)
                # Pacman's 2nd ply positions
                p2_nexts = self._pacman_next_positions(p1_pos, map_state)
                best_g2 = -float("inf")
                for g2_pos in g2_cands:
                    worst_p2 = min(manhattan(p2, g2_pos) for p2 in p2_nexts)
                    if worst_p2 > best_g2:
                        best_g2 = worst_p2
                if best_g2 < min_over_pac:
                    min_over_pac = best_g2

            # Bonuses
            escapes = sum(1 for _ in get_neighbors(g1_pos, map_state))
            escape_bonus = escapes * 0.15
            osc_penalty = -0.3 if (self.last_move and g1_move == OPPOSITE.get(self.last_move)) else 0
            dead_penalty = -2.0 if escapes <= 1 else 0
            # Prefer positions farther in Pacman-turn BFS
            ptd_bonus = ptd.get(g1_pos, 0) * 0.2

            score = min_over_pac + escape_bonus + osc_penalty + dead_penalty + ptd_bonus
            if score > best_score:
                best_score = score
                best_move = g1_move

        return best_move

    # ── CAUTION: weighted multi-factor scoring ────────────────────────

    def _caution(self, my_pos, pac_pos, map_state, ptd):
        best_move = Move.STAY
        best_score = -float("inf")

        candidates = [(my_pos, Move.STAY)]
        for nxt, m in get_neighbors(my_pos, map_state):
            candidates.append((nxt, m))

        for pos, move in candidates:
            td = ptd.get(pos, 0)
            escapes = sum(1 for _ in get_neighbors(pos, map_state))
            osc = -1.5 if (self.last_move and move == OPPOSITE.get(self.last_move)) else 0
            dead = -5 if escapes <= 1 else 0
            stay_pen = -0.5 if move == Move.STAY else 0
            score = td * 2.5 + escapes * 1.2 + osc + dead + stay_pen
            if score > best_score:
                best_score = score
                best_move = move

        return best_move

    # ── CALM: head toward the safest haven ────────────────────────────

    def _calm(self, my_pos, pac_pos, map_state, ptd):
        """Move toward the reachable cell with the highest Pacman-turn
        distance that has ≥ 2 escape exits."""
        if self._haven_target is None or self._haven_target == my_pos:
            self._haven_target = self._find_haven(my_pos, map_state, ptd)

        if self._haven_target and self._haven_target != my_pos:
            path = a_star(my_pos, self._haven_target, map_state)
            if path:
                return path[0]

        return self._caution(my_pos, pac_pos, map_state, ptd)

    def _find_haven(self, my_pos, map_state, ptd):
        """BFS outward from ghost; pick the cell that maximises ptd and
        has at least 2 exits."""
        best, best_td = None, -1
        queue = deque([(my_pos, 0)])
        seen = {my_pos}
        while queue:
            pos, d = queue.popleft()
            exits = sum(1 for _ in get_neighbors(pos, map_state))
            td = ptd.get(pos, 0)
            if exits >= 2 and td > best_td:
                best, best_td = pos, td
            for nxt, _ in get_neighbors(pos, map_state):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, d + 1))
        return best

    # ── random wander (no info about Pacman) ──────────────────────────

    def _wander(self, pos, map_state):
        moves = list(ALL_MOVES)
        random.shuffle(moves)
        for m in moves:
            if is_valid(apply_move(pos, m), map_state):
                return m
        return Move.STAY

    # ── helper: generate Pacman's reachable next positions ────────────

    def _pacman_next_positions(self, pac_pos, map_state):
        """All positions Pacman can reach in one turn (speed 1 or 2)."""
        positions = {pac_pos}  # STAY
        for move in ALL_MOVES:
            p1 = apply_move(pac_pos, move)
            if is_valid(p1, map_state):
                positions.add(p1)
                p2 = apply_move(p1, move)
                if is_valid(p2, map_state):
                    positions.add(p2)
        return positions
