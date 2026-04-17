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
import heapq


class PacmanAgent(BasePacmanAgent):
    """
    Pacman (Seeker) Agent - Goal: Catch the Ghost
    
    Implement your search algorithm to find and catch the ghost.
    Suggested algorithms: BFS, DFS, A*, Greedy Best-First
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pacman_speed = max(1, int(kwargs.get("pacman_speed", 1)))
        # TODO: Initialize any data structures you need
        # Examples:
        # - self.path = []  # Store planned path
        # - self.visited = set()  # Track visited positions
        self.name = "WAG Hunter"
        self.path = []
        self.cached_target = None
        self.visited = {}
        # Memory for limited observation mode
        self.last_known_enemy_pos = None
        self.last_enemy_pos = None
    
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
        # TODO: Implement your search algorithm here
        self.visited[my_position] = self.visited.get(my_position, 0) + 1

        # Update memory if enemy is visible
        if enemy_position is not None:
            self.last_known_enemy_pos = enemy_position

        planned_action = None

        # Visible enemy: pursue with predicted interception points.
        if enemy_position is not None:
            candidate_targets = self._predict_enemy_positions(enemy_position, map_state)
            planned_action = self._best_action_to_any_target(my_position, candidate_targets, map_state)
            self.last_enemy_pos = enemy_position

        # Not visible: chase last known location first.
        if planned_action is None and self.last_known_enemy_pos is not None:
            planned_action = self._best_action_to_any_target(
                my_position,
                [self.last_known_enemy_pos],
                map_state
            )

        # If no direct chase target is available, explore toward nearest unseen cells.
        if planned_action is None:
            explore_target = self._choose_exploration_target(my_position, map_state)
            if explore_target is not None:
                planned_action = self._best_action_to_any_target(
                    my_position,
                    [explore_target],
                    map_state
                )

        if planned_action is not None:
            return planned_action

        # Emergency fallback: choose the least-visited valid move.
        return self._fallback_move(my_position, map_state)
    
    # Helper methods (you can add more)
    
    def _best_action_to_any_target(self, start: tuple, targets, map_state: np.ndarray):
        best_path = None
        best_score = None

        for target in targets:
            if target is None or not self._is_valid_position(target, map_state):
                continue
            path = self._a_star(start, target, map_state)
            if not path:
                continue

            # Prefer shorter path, then lower heuristic distance after first move.
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

        # Predict likely future ghost positions (1-3 turns ahead).
        r, c = enemy_pos
        for k in range(1, 4):
            nxt = (r + dr * k, c + dc * k)
            if not self._is_valid_position(nxt, map_state):
                break
            candidates.append(nxt)
        return candidates

    def _choose_exploration_target(self, start: tuple, map_state: np.ndarray):
        h, w = map_state.shape
        unseen_cells = []
        for r in range(h):
            for c in range(w):
                if map_state[r, c] == -1:
                    unseen_cells.append((r, c))

        if not unseen_cells:
            return None

        # Try a few nearest unseen cells by Manhattan distance to keep runtime low.
        unseen_cells.sort(key=lambda p: self._manhattan(start, p))
        for candidate in unseen_cells[:24]:
            if self._a_star(start, candidate, map_state):
                return candidate
        return unseen_cells[0]

    def _fallback_move(self, pos: tuple, map_state: np.ndarray):
        candidates = []
        for move in [Move.UP, Move.LEFT, Move.DOWN, Move.RIGHT]:
            steps = self._max_valid_steps(pos, move, map_state, self.pacman_speed)
            if steps <= 0:
                continue
            delta_row, delta_col = move.value
            next_pos = (pos[0] + delta_row, pos[1] + delta_col)
            visit_penalty = self.visited.get(next_pos, 0)
            candidates.append((visit_penalty, -steps, move, steps))

        if not candidates:
            return (Move.STAY, 1)

        candidates.sort()
        _, _, move, steps = candidates[0]
        return (move, steps)

    def _compress_path_to_action(self, start: tuple, path, map_state: np.ndarray):
        if not path:
            return None

        first_move = path[0]
        steps = 0
        current = start

        for move in path:
            if move != first_move or steps >= self.pacman_speed:
                break
            delta_row, delta_col = move.value
            nxt = (current[0] + delta_row, current[1] + delta_col)
            if not self._is_valid_position(nxt, map_state):
                break
            current = nxt
            steps += 1

        if steps == 0:
            return None
        return (first_move, steps)

    def _a_star(self, start: tuple, goal: tuple, map_state: np.ndarray):
        if start == goal:
            return []

        open_heap = []
        g_score = {start: 0}
        came_from = {}
        move_from = {}
        counter = 0

        heapq.heappush(open_heap, (self._manhattan(start, goal), 0, counter, start))

        while open_heap:
            _, current_g, _, current = heapq.heappop(open_heap)
            if current == goal:
                return self._reconstruct_path(came_from, move_from, current)

            # Skip outdated heap entries.
            if current_g != g_score.get(current, current_g):
                continue

            for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
                delta_row, delta_col = move.value
                nxt = (current[0] + delta_row, current[1] + delta_col)
                if not self._is_valid_position(nxt, map_state):
                    continue

                tentative_g = current_g + 1
                if tentative_g < g_score.get(nxt, 10**9):
                    g_score[nxt] = tentative_g
                    came_from[nxt] = current
                    move_from[nxt] = move
                    counter += 1
                    f = tentative_g + self._manhattan(nxt, goal)
                    heapq.heappush(open_heap, (f, tentative_g, counter, nxt))

        return None

    def _reconstruct_path(self, came_from, move_from, end_node):
        moves = []
        cur = end_node
        while cur in came_from:
            moves.append(move_from[cur])
            cur = came_from[cur]
        moves.reverse()
        return moves

    def _manhattan(self, a: tuple, b: tuple) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

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
        
        return map_state[row, col] != 1


class GhostAgent(BaseGhostAgent):
    """
    Ghost (Hider) Agent - Risk-Aware Strategy #4
    
    Intelligently avoids Pacman by assessing threat level and adapting behavior:
    - HIGH ALERT (distance <= 5): Escape mode - maximize distance
    - MEDIUM ALERT (distance <= 10): Strategic retreat - balance distance + wall cover
    - LOW ALERT (distance > 10): Explore dead-ends - safer areas harder to reach
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "WAG Ghost"
        self.DANGER_DISTANCE = 5  # Critical: activate panic mode
        self.SAFE_DISTANCE = 10   # Safe: explore freely
        self.last_known_enemy_pos = None
    
    def step(self, map_state: np.ndarray, 
             my_position: tuple, 
             enemy_position: tuple,
             step_number: int) -> Move:
        """
        Smart evasion based on threat assessment.
        
        Args:
            map_state: 2D numpy array where 1=wall, 0=empty, -1=unseen (fog)
            my_position: Your current (row, col) in absolute coordinates
            enemy_position: Pacman's (row, col) if visible, None otherwise
            step_number: Current step number (starts at 1)
            
        Returns:
            Move: Adaptive move based on risk level
        """
        # Update memory if Pacman is visible
        if enemy_position is not None:
            self.last_known_enemy_pos = enemy_position
        
        pacman_pos = enemy_position or self.last_known_enemy_pos
        
        # No information about Pacman - explore safely
        if pacman_pos is None:
            return self._explore_safely(my_position, map_state)
        
        # Assess threat level
        distance = self._manhattan_distance(my_position, pacman_pos)
        
        # HIGH ALERT: Pacman is dangerously close!
        if distance <= self.DANGER_DISTANCE:
            return self._escape_panic(my_position, pacman_pos, map_state)
        
        # MEDIUM ALERT: Move away steadily while seeking protection
        elif distance <= self.SAFE_DISTANCE:
            return self._move_away_strategically(my_position, pacman_pos, map_state)
        
        # LOW ALERT: Safe zone - explore dead-ends (hard to reach areas)
        else:
            return self._explore_dead_ends(my_position, map_state)
    
    def _escape_panic(self, pos: tuple, pacman_pos: tuple, map_state: np.ndarray) -> Move:
        """
        Panic mode: Maximize distance to Pacman immediately.
        Used when danger is imminent (distance <= 5).
        """
        best_move = Move.STAY
        max_distance = self._manhattan_distance(pos, pacman_pos)
        
        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            if self._is_valid_move(pos, move, map_state):
                next_pos = self._apply_move(pos, move)
                distance = self._manhattan_distance(next_pos, pacman_pos)
                if distance > max_distance:
                    max_distance = distance
                    best_move = move
        
        return best_move
    
    def _move_away_strategically(self, pos: tuple, pacman_pos: tuple, map_state: np.ndarray) -> Move:
        """
        Strategic retreat: Balance distance from Pacman + wall shelter.
        Used when threat is moderate (5 < distance <= 10).
        Score = distance + (wall_count * 0.5)
        """
        best_move = Move.STAY
        best_score = -float('inf')
        
        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            if self._is_valid_move(pos, move, map_state):
                next_pos = self._apply_move(pos, move)
                distance = self._manhattan_distance(next_pos, pacman_pos)
                walls = self._count_adjacent_walls(next_pos, map_state)
                
                # Combine distance and wall protection
                score = distance + walls * 0.5
                
                if score > best_score:
                    best_score = score
                    best_move = move
        
        return best_move
    
    def _explore_dead_ends(self, pos: tuple, map_state: np.ndarray) -> Move:
        """
        Low-threat exploration: Seek dead-end corridors (many walls).
        Dead-ends are strategically safer (harder for Pacman to reach).
        """
        best_move = Move.STAY
        best_deadend_score = self._count_adjacent_walls(pos, map_state)
        
        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            if self._is_valid_move(pos, move, map_state):
                next_pos = self._apply_move(pos, move)
                wall_count = self._count_adjacent_walls(next_pos, map_state)
                
                if wall_count > best_deadend_score:
                    best_deadend_score = wall_count
                    best_move = move
        
        return best_move
    
    def _explore_safely(self, pos: tuple, map_state: np.ndarray) -> Move:
        """
        Explore when Pacman is not visible: prefer dead-ends.
        """
        best_move = Move.STAY
        best_score = self._count_adjacent_walls(pos, map_state)
        
        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            if self._is_valid_move(pos, move, map_state):
                next_pos = self._apply_move(pos, move)
                score = self._count_adjacent_walls(next_pos, map_state)
                if score > best_score:
                    best_score = score
                    best_move = move
        
        return best_move
    
    # Helper methods (you can add more)
    
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
        
        return map_state[row, col] == 0

    def _manhattan_distance(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def _count_adjacent_walls(self, pos, map_state):
        count = 0
        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            next_pos = self._apply_move(pos, move)
            if not self._is_valid_position(next_pos, map_state):
                count += 1
        return count

    def _apply_move(self, pos, move):
        delta_row, delta_col = move.value
        return (pos[0] + delta_row, pos[1] + delta_col)

    def _explore_safely(self, pos, map_state):
        """Move to a safe position."""
        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            if self._is_valid_move(pos, move, map_state):
                return move
        return Move.STAY

    def _escape_panic(self, pos, pacman_pos, map_state):
        """Escape mode: move to furthest reachable position."""
        best_move = Move.STAY
        max_distance = 0
        
        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            if self._is_valid_move(pos, move, map_state):
                next_pos = self._apply_move(pos, move)
                distance = self._manhattan_distance(next_pos, pacman_pos)
                if distance > max_distance:
                    max_distance = distance
                    best_move = move
        
        return best_move
    
    def _move_away_strategically(self, pos, pacman_pos, map_state):
        """Balance between distance and wall protection."""
        best_move = Move.STAY
        best_score = -float('inf')
        
        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            if self._is_valid_move(pos, move, map_state):
                next_pos = self._apply_move(pos, move)
                distance = self._manhattan_distance(next_pos, pacman_pos)
                walls = self._count_adjacent_walls(next_pos, map_state)
                
                # Prefer: distance + wall protection
                score = distance + walls * 0.5
                
                if score > best_score:
                    best_score = score
                    best_move = move
        
        return best_move
    
    def _explore_dead_ends(self, pos, map_state):
        """When safe, explore dead-end corridors."""
        # Dead-ends are hard for Pacman to reach
        best_move = Move.STAY
        best_deadend_score = self._count_adjacent_walls(pos, map_state)
        
        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            if self._is_valid_move(pos, move, map_state):
                next_pos = self._apply_move(pos, move)
                score = self._count_adjacent_walls(next_pos, map_state)
                if score > best_deadend_score:
                    best_deadend_score = score
                    best_move = move
        
        return best_move

    def __str__(self):
        return f"GhostAgent(DANGER_DISTANCE={self.DANGER_DISTANCE}, SAFE_DISTANCE={self.SAFE_DISTANCE})"
