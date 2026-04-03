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
        self.name = "Template Pacman"
        # Memory for limited observation mode
        self.last_known_enemy_pos = None
    
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
        
        # Update memory if enemy is visible
        if enemy_position is not None:
            self.last_known_enemy_pos = enemy_position
        
        # Use current sighting, fallback to last known, or explore
        target = enemy_position or self.last_known_enemy_pos
        
        if target is None:
            # No information about enemy - explore randomly
            for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
                if self._is_valid_move(my_position, move, map_state):
                    return (move, 1)
            return (Move.STAY, 1)
        
        # Example: Simple greedy approach (replace with your algorithm)
        row_diff = target[0] - my_position[0]
        col_diff = target[1] - my_position[1]
        
        # Try to move towards ghost
        if abs(row_diff) > abs(col_diff):
            primary_move = Move.DOWN if row_diff > 0 else Move.UP
            desired_steps = abs(row_diff)
        else:
            primary_move = Move.RIGHT if col_diff > 0 else Move.LEFT
            desired_steps = abs(col_diff)

        action = self._choose_action(
            my_position,
            [primary_move],
            map_state,
            desired_steps
        )
        if action:
            return action

        # If the primary direction is blocked, try other moves
        fallback_moves = [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]
        action = self._choose_action(my_position, fallback_moves, map_state, self.pacman_speed)
        if action:
            return action
        
        return (Move.STAY, 1)
    
    # Helper methods (you can add more)
    
    def _choose_action(self, pos: tuple, moves, map_state: np.ndarray, desired_steps: int):
        for move in moves:
            max_steps = min(self.pacman_speed, max(1, desired_steps))
            steps = self._max_valid_steps(pos, move, map_state, max_steps)
            if steps > 0:
                return (move, steps)
        return None

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
        
        return map_state[row, col] == 0


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
        self.name = "Risk-Aware Ghost"
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
