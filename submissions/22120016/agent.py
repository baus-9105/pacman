import sys
from pathlib import Path
import numpy as np
import heapq
from collections import deque

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from agent_interface import PacmanAgent as BasePacmanAgent
from agent_interface import GhostAgent as BaseGhostAgent
from environment import Move

class PacmanAgent(BasePacmanAgent):
    """
    Seeker 22120016: A* Search with Interception Prediction and Speed Compression.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pacman_speed = max(1, int(kwargs.get("pacman_speed", 1)))
        self.name = "AStar Hunter 22120016"
        self.visited = {}
        self.last_known_enemy_pos = None
        self.last_enemy_pos = None
    
    def step(self, map_state: np.ndarray, my_position: tuple, enemy_position: tuple, step_number: int):
        self.visited[my_position] = self.visited.get(my_position, 0) + 1

        if enemy_position is not None:
            self.last_known_enemy_pos = enemy_position

        planned_action = None

        # 1. Interception Chase: If visible, predict enemy movement 
        if enemy_position is not None:
            candidate_targets = self._predict_enemy_positions(enemy_position, map_state)
            planned_action = self._best_action_to_any_target(my_position, candidate_targets, map_state)
            self.last_enemy_pos = enemy_position

        # 2. Last Known Location: If hidden, route to the last sighting
        if planned_action is None and self.last_known_enemy_pos is not None:
            planned_action = self._best_action_to_any_target(
                my_position, [self.last_known_enemy_pos], map_state
            )

        # 3. Fog Exploration: Route to nearest unseen territory (-1 cells)
        if planned_action is None:
            explore_target = self._choose_exploration_target(my_position, map_state)
            if explore_target is not None:
                planned_action = self._best_action_to_any_target(
                    my_position, [explore_target], map_state
                )

        if planned_action is not None:
            return planned_action

        # Fallback: Least-visited valid move
        return self._fallback_move(my_position, map_state)
    
    def _best_action_to_any_target(self, start: tuple, targets, map_state: np.ndarray):
        best_path = None
        best_score = None

        for target in targets:
            if target is None or not self._is_valid_position(target, map_state):
                continue
            path = self._a_star(start, target, map_state)
            if not path:
                continue

            score = len(path)
            if best_score is None or score < best_score:
                best_score = score
                best_path = path

        if not best_path:
            return None
        return self._compress_path_to_action(start, best_path, map_state)

    def _predict_enemy_positions(self, enemy_pos: tuple, map_state: np.ndarray):
        candidates = [enemy_pos]
        if self.last_enemy_pos is None:
            return candidates

        dr = enemy_pos[0] - self.last_enemy_pos[0]
        dc = enemy_pos[1] - self.last_enemy_pos[1]
        if dr == 0 and dc == 0:
            return candidates

        r, c = enemy_pos
        for k in range(1, 4):
            nxt = (r + dr * k, c + dc * k)
            if not self._is_valid_position(nxt, map_state):
                break
            candidates.append(nxt)
        return candidates

    def _choose_exploration_target(self, start: tuple, map_state: np.ndarray):
        h, w = map_state.shape
        unseen_cells = [(r, c) for r in range(h) for c in range(w) if map_state[r, c] == -1]

        if not unseen_cells:
            return None

        unseen_cells.sort(key=lambda p: self._manhattan(start, p))
        for candidate in unseen_cells[:24]:
            if self._a_star(start, candidate, map_state):
                return candidate
        return unseen_cells[0]

    def _fallback_move(self, pos: tuple, map_state: np.ndarray):
        candidates = []
        for move in [Move.UP, Move.LEFT, Move.DOWN, Move.RIGHT]:
            steps = self._max_valid_steps(pos, move, map_state, self.pacman_speed)
            if steps <= 0: continue
            delta_row, delta_col = move.value
            next_pos = (pos[0] + delta_row, pos[1] + delta_col)
            candidates.append((self.visited.get(next_pos, 0), -steps, move, steps))

        if not candidates: return (Move.STAY, 1)
        candidates.sort()
        return (candidates[0][2], candidates[0][3])

    def _compress_path_to_action(self, start: tuple, path, map_state: np.ndarray):
        if not path: return None
        first_move = path[0]
        steps = 0
        current = start

        for move in path:
            if move != first_move or steps >= self.pacman_speed: break
            delta_row, delta_col = move.value
            nxt = (current[0] + delta_row, current[1] + delta_col)
            if not self._is_valid_position(nxt, map_state): break
            current = nxt
            steps += 1

        return (first_move, steps) if steps > 0 else None

    def _a_star(self, start: tuple, goal: tuple, map_state: np.ndarray):
        if start == goal: return []
        open_heap = []
        g_score = {start: 0}
        came_from, move_from = {}, {}
        counter = 0

        heapq.heappush(open_heap, (self._manhattan(start, goal), 0, counter, start))

        while open_heap:
            _, current_g, _, current = heapq.heappop(open_heap)
            if current == goal:
                moves = []
                while current in came_from:
                    moves.append(move_from[current])
                    current = came_from[current]
                return moves[::-1]

            if current_g != g_score.get(current, current_g): continue

            for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
                delta_row, delta_col = move.value
                nxt = (current[0] + delta_row, current[1] + delta_col)
                if not self._is_valid_position(nxt, map_state): continue

                tentative_g = current_g + 1
                if tentative_g < g_score.get(nxt, float('inf')):
                    g_score[nxt] = tentative_g
                    came_from[nxt], move_from[nxt] = current, move
                    counter += 1
                    f = tentative_g + self._manhattan(nxt, goal)
                    heapq.heappush(open_heap, (f, tentative_g, counter, nxt))
        return None

    def _manhattan(self, a: tuple, b: tuple) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _max_valid_steps(self, pos: tuple, move: Move, map_state: np.ndarray, max_steps: int) -> int:
        steps, current = 0, pos
        for _ in range(max_steps):
            delta_row, delta_col = move.value
            next_pos = (current[0] + delta_row, current[1] + delta_col)
            if not self._is_valid_position(next_pos, map_state): break
            steps += 1
            current = next_pos
        return steps
    
    def _is_valid_position(self, pos: tuple, map_state: np.ndarray) -> bool:
        row, col = pos
        height, width = map_state.shape
        if row < 0 or row >= height or col < 0 or col >= width: return False
        return map_state[row, col] != 1


class GhostAgent(BaseGhostAgent):
    """
    Hider 22120016: True BFS Distance Maximization and Exit Evaluation.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pacman_speed = max(1, int(kwargs.get("pacman_speed", 2)))
        self.last_known_enemy_pos = None
        self.last_move = Move.STAY
        self.visited = {}
    
    def step(self, map_state: np.ndarray, my_position: tuple, enemy_position: tuple, step_number: int) -> Move:
        self.visited[my_position] = self.visited.get(my_position, 0) + 1
        
        if enemy_position is not None:
            self.last_known_enemy_pos = enemy_position
        
        threat = enemy_position or self.last_known_enemy_pos
        
        if threat is None:
            move = self._explore_move(my_position, map_state)
            self.last_move = move
            return move

        move = self._best_escape_move(my_position, threat, map_state)
        self.last_move = move
        return move

    def _best_escape_move(self, my_position: tuple, threat: tuple, map_state: np.ndarray) -> Move:
        pacman_reachable = self._pacman_reachable_positions(threat, map_state)
        candidates = []

        for move in [Move.UP, Move.LEFT, Move.DOWN, Move.RIGHT, Move.STAY]:
            next_pos = self._apply_move(my_position, move, map_state)
            if move != Move.STAY and next_pos == my_position: continue

            score = self._evaluate_escape_state(
                ghost_pos=next_pos, pacman_positions=pacman_reachable, map_state=map_state, move=move
            )
            candidates.append((score, move))

        if not candidates: return Move.STAY
        candidates.sort(reverse=True, key=lambda item: item[0])
        return candidates[0][1]

    def _evaluate_escape_state(self, ghost_pos: tuple, pacman_positions, map_state: np.ndarray, move: Move) -> float:
        threat_map = self._multi_source_distance_map(pacman_positions, map_state)
        nearest_threat = threat_map.get(ghost_pos, 10**6)

        if nearest_threat <= 1: return -10000.0

        safe_area = self._safe_area_size(ghost_pos, threat_map, map_state)
        exits = self._exit_count(ghost_pos, map_state)
        visit_penalty = self.visited.get(ghost_pos, 0)
        reverse_penalty = 2.0 if self._is_reverse(move, self.last_move) else 0.0

        return (30.0 * nearest_threat + 0.8 * safe_area + 6.0 * exits - 2.0 * visit_penalty - reverse_penalty)

    def _explore_move(self, my_position: tuple, map_state: np.ndarray) -> Move:
        if self.last_known_enemy_pos is not None:
            return self._best_escape_move(my_position, self.last_known_enemy_pos, map_state)

        candidates = []
        for move in [Move.UP, Move.LEFT, Move.DOWN, Move.RIGHT, Move.STAY]:
            next_pos = self._apply_move(my_position, move, map_state)
            if move != Move.STAY and next_pos == my_position: continue

            score = 4.0 * self._exit_count(next_pos, map_state) - 1.5 * self.visited.get(next_pos, 0)
            if self._is_reverse(move, self.last_move): score -= 2.0
            candidates.append((score, move))

        if not candidates: return Move.STAY
        candidates.sort(reverse=True, key=lambda item: item[0])
        return candidates[0][1]

    def _pacman_reachable_positions(self, pacman_pos: tuple, map_state: np.ndarray):
        reachable = {pacman_pos}
        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            current = pacman_pos
            for _ in range(self.pacman_speed):
                nxt = self._apply_move(current, move, map_state)
                if nxt == current: break
                reachable.add(nxt)
                current = nxt
        return reachable

    def _multi_source_distance_map(self, sources, map_state: np.ndarray):
        queue = deque()
        dist = {}
        for source in sources:
            if source not in dist:
                dist[source] = 0
                queue.append(source)

        while queue:
            current = queue.popleft()
            for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
                nxt = self._apply_move(current, move, map_state)
                if nxt != current and nxt not in dist:
                    dist[nxt] = dist[current] + 1
                    queue.append(nxt)
        return dist

    def _safe_area_size(self, start: tuple, threat_map, map_state: np.ndarray) -> int:
        queue = deque([start])
        seen = {start}
        safe = 0
        while queue:
            current = queue.popleft()
            if threat_map.get(current, 10**6) > 2: safe += 1
            for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
                nxt = self._apply_move(current, move, map_state)
                if nxt != current and nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return safe

    def _apply_move(self, pos: tuple, move: Move, map_state: np.ndarray) -> tuple:
        delta_row, delta_col = move.value
        new_pos = (pos[0] + delta_row, pos[1] + delta_col)
        return new_pos if self._is_valid_position(new_pos, map_state) else pos

    def _exit_count(self, pos: tuple, map_state: np.ndarray) -> int:
        return sum(1 for m in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT] if self._apply_move(pos, m, map_state) != pos)

    def _is_reverse(self, move: Move, previous: Move) -> bool:
        if move == Move.STAY or previous == Move.STAY: return False
        return move.value[0] == -previous.value[0] and move.value[1] == -previous.value[1]
    
    def _is_valid_position(self, pos: tuple, map_state: np.ndarray) -> bool:
        row, col = pos
        height, width = map_state.shape
        if row < 0 or row >= height or col < 0 or col >= width: return False
        return map_state[row, col] == 0