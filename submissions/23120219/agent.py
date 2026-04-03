"""
Example student submission showing the required interface.

Students should implement their own PacmanAgent and/or GhostAgent
following this template.
"""

import sys
from pathlib import Path
from collections import deque
import heapq

# Add src to path to import the interface
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from agent_interface import PacmanAgent as BasePacmanAgent
from agent_interface import GhostAgent as BaseGhostAgent
from environment import Move
import numpy as np
import random


class PacmanAgent(BasePacmanAgent):
    """
    Example Pacman agent using a simple greedy strategy.
    Students should implement their own search algorithms here.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize the Pacman agent.
        Students can set up any data structures they need here.
        """
        super().__init__(**kwargs)
        self.name = "BFS Pacman"
        self.pacman_speed = max(1, int(kwargs.get("pacman_speed", 1)))
        # Memory for limited observation mode
        self.last_known_enemy_pos = None
        self.current_path = []
        self.last_target = None
    

    def _get_neighbors(self, pos, map_state):
        """
        Get all valid neighboring positions from the current position.

        Args:
            pos: Current position as a tuple (row, col)
            map_state: 2D numpy array representing the map (0 = empty, 1 = wall)

        Returns:
            List of tuples: (neighbor_position, move_direction)
        """
        neighbors = []
        # Check all four directions
        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            delta_row, delta_col = move.value
            next_pos = (pos[0] + delta_row, pos[1] + delta_col)
            # Only add positions that are valid (not walls, in bounds)
            if self._is_valid_position(next_pos, map_state):
                neighbors.append((next_pos, move))
        
        random.shuffle(neighbors)
        return neighbors


    def bfs(self, start, goal, map_state):
        """
        Perform Breadth-First Search (BFS) to find the shortest path from start to goal.

        Args:
            start: Starting position as a tuple (row, col)
            goal: Target position as a tuple (row, col)
            map_state: 2D numpy array representing the map

        Returns:
            List of moves to reach the goal. Empty list if no path found.
        """
        # Queue stores tuples: (current_position, path_taken_to_reach_here)
        queue = deque([(start, [])])
        visited = set([start])  # Keep track of visited positions to avoid loops

        while queue:
            current, path = queue.popleft()  # FIFO: ensures BFS (shortest path)

            # If goal is reached, return the path
            if current == goal:
                return path

            # Explore all valid neighbors
            for next_pos, move in self._get_neighbors(current, map_state):
                if next_pos not in visited:
                    visited.add(next_pos)
                    # Append the move to the current path and add neighbor to queue
                    new_path = path + [move]
                    queue.append((next_pos, new_path))
        
        # No path found
        return []

    def step(self, map_state: np.ndarray, 
            my_position: tuple, 
            enemy_position: tuple,
            step_number: int):
        """
        BFS-based chasing strategy.

        - Always recompute BFS each step (no caching).
        - Chase the current enemy position if visible.
        - Otherwise, chase the last known position.
        - Move only 1 step to avoid path inconsistency.
        """

        # Update memory when enemy is visible
        if enemy_position is not None:
            self.last_known_enemy_pos = enemy_position

        # Use current enemy position or fallback to last known position
        target = enemy_position or self.last_known_enemy_pos

        # If no information about the enemy, stay in place
        if target is None:
            return (Move.STAY, 1)

        # Recompute BFS path every step (important for moving target)
        path = self.bfs(my_position, target, map_state)

        if path:
            move = path[0]  # take only the first move
            # Store last move for future oscillation check
            self.last_move = move
            # Move only 1 step to keep BFS path valid
            return (move, 1)

        # If no path found, stay in place
        return (Move.STAY, 1)
    
    
    def _is_valid_position(self, pos: tuple, map_state: np.ndarray) -> bool:
        """Check if a position is valid (not a wall and within bounds)."""
        row, col = pos
        height, width = map_state.shape
        
        if row < 0 or row >= height or col < 0 or col >= width:
            return False
        
        return map_state[row, col] == 0

    def _max_valid_steps(self, pos: tuple, move: Move, map_state: np.ndarray, desired_steps: int) -> int:
        steps = 0
        max_steps = min(self.pacman_speed, max(1, desired_steps))
        current = pos
        for _ in range(max_steps):
            delta_row, delta_col = move.value
            next_pos = (current[0] + delta_row, current[1] + delta_col)
            if not self._is_valid_position(next_pos, map_state):
                break
            steps += 1
            current = next_pos
        return steps

    def _desired_steps(self, move: Move, row_diff: int, col_diff: int) -> int:
        if move in (Move.UP, Move.DOWN):
            return abs(row_diff)
        if move in (Move.LEFT, Move.RIGHT):
            return abs(col_diff)
        return 1


class GhostAgent(BaseGhostAgent):
    """
    Example Ghost agent using a simple evasive strategy.
    Students should implement their own search algorithms here.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize the Ghost agent.
        Students can set up any data structures they need here.
        """
        super().__init__(**kwargs)
        self.name = "Example Evasive Ghost"
        # Memory for limited observation mode
        self.last_known_enemy_pos = None
    
    def step(self, map_state: np.ndarray, 
             my_position: tuple, 
             enemy_position: tuple,
             step_number: int) -> Move:
        """
        Simple evasive strategy: move away from Pacman.
        
        When enemy_position is None (limited observation mode),
        uses last known position or moves randomly.
        
        Students should implement better search algorithms like:
        - BFS to find furthest point
        - A* to plan escape route
        - Minimax for adversarial search
        - etc.
        """
        # Update memory if enemy is visible
        if enemy_position is not None:
            self.last_known_enemy_pos = enemy_position
        
        # Use current sighting, fallback to last known, or move randomly
        threat = enemy_position or self.last_known_enemy_pos
        
        if threat is None:
            # No information about enemy - move randomly
            return self._random_move(my_position, map_state)
        
        # Calculate direction away from threat
        row_diff = my_position[0] - threat[0]
        col_diff = my_position[1] - threat[1]
        
        # List of possible moves in order of preference
        moves = []
        
        # Prioritize vertical movement away from Pacman
        if row_diff > 0:
            moves.append(Move.DOWN)
        elif row_diff < 0:
            moves.append(Move.UP)
        
        # Prioritize horizontal movement away from Pacman
        if col_diff > 0:
            moves.append(Move.RIGHT)
        elif col_diff < 0:
            moves.append(Move.LEFT)
        
        # Try each move in order
        for move in moves:
            delta_row, delta_col = move.value
            new_pos = (my_position[0] + delta_row, my_position[1] + delta_col)
            
            # Check if move is valid
            if self._is_valid_position(new_pos, map_state):
                return move
        
        # If no preferred move is valid, try any valid move
        all_moves = [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]
        random.shuffle(all_moves)
        
        for move in all_moves:
            delta_row, delta_col = move.value
            new_pos = (my_position[0] + delta_row, my_position[1] + delta_col)
            
            if self._is_valid_position(new_pos, map_state):
                return move
        
        # If no move is valid, stay
        return Move.STAY

    def _random_move(self, my_position: tuple, map_state: np.ndarray) -> Move:
        """Random movement when enemy position is unknown."""
        all_moves = [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]
        random.shuffle(all_moves)
        
        for move in all_moves:
            delta_row, delta_col = move.value
            new_pos = (my_position[0] + delta_row, my_position[1] + delta_col)
            if self._is_valid_position(new_pos, map_state):
                return move
        
        return Move.STAY
    
    def _is_valid_position(self, pos: tuple, map_state: np.ndarray) -> bool:
        """Check if a position is valid (not a wall and within bounds)."""
        row, col = pos
        height, width = map_state.shape
        
        if row < 0 or row >= height or col < 0 or col >= width:
            return False
        
        return map_state[row, col] == 0

print("PacmanAgent exists:", 'PacmanAgent' in globals())