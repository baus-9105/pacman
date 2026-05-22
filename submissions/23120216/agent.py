"""
Advanced Student Submission for Hide and Seek Arena.
Author: Cao Thanh Bình
Implementing Advanced Belief Tracking, True BFS-based Distance Fields, 
and Straight-line Acceleration Optimization.
"""

import sys
from pathlib import Path
import numpy as np
import random
from collections import deque

# Thêm src vào path để import interface theo cấu trúc đồ án [cite: 113, 114]
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from agent_interface import PacmanAgent as BasePacmanAgent
from agent_interface import GhostAgent as BaseGhostAgent
from environment import Move


class ProductionBeliefTracker:
    """
    Bộ theo dõi và dự đoán trạng thái tin cậy (Belief State) hiệu năng cao.
    Sử dụng ma trận lan truyền xác suất để ước lượng vị trí đối thủ khuất tầm nhìn[cite: 7, 8].
    """
    def __init__(self, shape=(21, 21)):
        self.shape = shape
        self.belief_grid = np.ones(shape)
        self.reset_beliefs()

    def reset_beliefs(self):
        self.belief_grid.fill(1.0 / (self.shape[0] * self.shape[1]))

    def update(self, map_state: np.ndarray, enemy_position: tuple):
        # 1. Nếu nhìn thấy trực tiếp đối thủ, định vị chính xác 100% [cite: 27]
        if enemy_position is not None:
            self.belief_grid.fill(0.0)
            self.belief_grid[enemy_position[0], enemy_position[1]] = 1.0
            return

        # 2. Xóa bỏ xác suất ở những ô nằm trong tầm nhìn hiện tại nhưng trống (0 hoặc 1) [cite: 106]
        # Đối thủ chắc chắn không nằm trong các ô ta nhìn thấy mà không có ai [cite: 106]
        self.belief_grid[map_state >= 0] = 0.0

        # 3. Lan truyền xác suất sang các ô ẩn lân cận (-1) [cite: 106]
        new_belief = np.zeros(self.shape)
        height, width = self.shape
        moves = [(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)]

        for r in range(height):
            for c in range(width):
                if self.belief_grid[r, c] > 0:
                    valid_neighbors = []
                    for dr, dc in moves[:4]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < height and 0 <= nc < width and map_state[nr, nc] == -1:
                            valid_neighbors.append((nr, nc))
                    
                    if valid_neighbors:
                        prob_share = self.belief_grid[r, c] / len(valid_neighbors)
                        for nr, nc in valid_neighbors:
                            new_belief[nr, nc] += prob_share
                    else:
                        new_belief[r, c] += self.belief_grid[r, c]

        total_prob = np.sum(new_belief)
        if total_prob > 0:
            self.belief_grid = new_belief / total_prob
        else:
            unknown_mask = (map_state == -1)
            if np.any(unknown_mask):
                self.belief_grid[unknown_mask] = 1.0 / np.sum(unknown_mask)

    def get_best_estimate(self):
        """Trả về tọa độ có xác xuất cao nhất chứa đối thủ."""
        return np.unravel_index(np.argmax(self.belief_grid), self.shape)


def compute_bfs_distance_matrix(map_state: np.ndarray, start_pos: tuple) -> np.ndarray:
    """
    Xây dựng Bản đồ khoảng cách thực tế (True Distance Field) bằng BFS.
    Khắc phục hoàn toàn nhược điểm của khoảng cách Manhattan khi gặp tường chắn.
    """
    height, width = map_state.shape
    dist_matrix = np.full((height, width), 999.0)  # Thay bằng số lớn thay cho inf để tối ưu bộ nhớ
    queue = deque([start_pos])
    dist_matrix[start_pos[0], start_pos[1]] = 0

    while queue:
        curr = queue.popleft()
        curr_dist = dist_matrix[curr[0], curr[1]]
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = curr[0] + dr, curr[1] + dc
            if 0 <= nr < height and 0 <= nc < width and map_state[nr, nc] != 1: # 1 là tường [cite: 106]
                if dist_matrix[nr, nc] == 999.0:
                    dist_matrix[nr, nc] = curr_dist + 1
                    queue.append((nr, nc))
    return dist_matrix


class PacmanAgent(BasePacmanAgent):
    """
    Pacman (Seeker) Siêu cấp:
    - Tìm đường thông minh bằng Bản đồ Khoảng cách Thực tế (BFS-driven Search Field).
    - Tối ưu trọng số góc cua để tận dụng tuyệt đối Luật di chuyển thẳng 2 ô/bước.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "Ultimate Seeker Pacman"
        self.pacman_speed = max(1, int(kwargs.get("pacman_speed", 2))) # Mặc định luật chơi là 2 ô 
        self.tracker = ProductionBeliefTracker()

    def step(self, map_state: np.ndarray, my_position: tuple, enemy_position: tuple, step_number: int):
        # Cập nhật thông tin tình báo về vị trí địch [cite: 27]
        self.tracker.update(map_state, enemy_position)
        target = enemy_position if enemy_position is not None else self.tracker.get_best_estimate()

        height, width = map_state.shape
        best_move = Move.STAY
        best_steps = 1
        min_cost = float('inf')

        # Duyệt qua toàn bộ hướng đi để tìm hướng áp sát mục tiêu tối ưu nhất
        for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            dr, dc = move.value
            
            # Kiểm tra khả năng đi thẳng tối đa (Hỗ trợ luật tăng tốc 2 ô) 
            max_possible_steps = 1
            first_step = (my_position[0] + dr, my_position[1] + dc)
            
            if 0 <= first_step[0] < height and 0 <= first_step[1] < width and map_state[first_step[0], first_step[1]] != 1:
                if self.pacman_speed > 1:
                    second_step = (first_step[0] + dr, first_step[1] + dc)
                    if 0 <= second_step[0] < height and 0 <= second_step[1] < width and map_state[second_step[0], second_step[1]] != 1:
                        max_possible_steps = 2
                
                # Giả lập vị trí mới sau khi đi (1 hoặc 2 bước) 
                for steps in range(1, max_possible_steps + 1):
                    new_pos = (my_position[0] + dr * steps, my_position[1] + dc * steps)
                    
                    # Tính toán khoảng cách thực từ vị trí mới này tới mục tiêu
                    dist_matrix = compute_bfs_distance_matrix(map_state, new_pos)
                    current_dist = dist_matrix[target[0], target[1]]
                    
                    # Chi phí tính toán: Ưu tiên đường đi rút ngắn khoảng cách thực tế nhất
                    # Di chuyển 2 bước thẳng hiệu quả tương đương chi phí thời gian được chia đôi 
                    cost = current_dist - (0.1 * steps) 
                    
                    if cost < min_cost:
                        min_cost = cost
                        best_move = move
                        best_steps = steps

        if best_move == Move.STAY:
            # Fallback nếu bị kẹt đường: Tìm ô trống ngẫu nhiên kế cạnh để kích hoạt lại radar
            for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
                dr, dc = move.value
                nr, nc = my_position[0] + dr, my_position[1] + dc
                if 0 <= nr < height and 0 <= nc < width and map_state[nr, nc] != 1:
                    return (move, 1)
            return (Move.STAY, 1)

        return (best_move, best_steps)


class GhostAgent(BaseGhostAgent):
    """
    Ghost (Hider) Siêu cấp:
    - Sử dụng hàm đánh giá Adversarial Lookahead chống áp sát của Pacman.
    - Ưu tiên vùng tối sương mù và giữ không gian an toàn đa hướng (Mobility Score)[cite: 106, 107].
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "Ultimate Evasive Ghost"
        self.tracker = ProductionBeliefTracker()

    def step(self, map_state: np.ndarray, my_position: tuple, enemy_position: tuple, step_number: int) -> Move:
        # Cập nhật thông tin dự đoán vị trí thợ săn Pacman [cite: 27]
        self.tracker.update(map_state, enemy_position)
        
        height, width = map_state.shape
        best_move = Move.STAY
        max_score = -float('inf')

        # Thử nghiệm tất cả các nước đi khả thi (Bao gồm đứng yên lánh nạn)
        for move in [Move.STAY, Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
            if move == Move.STAY:
                next_pos = my_position
            else:
                dr, dc = move.value
                next_pos = (my_position[0] + dr, my_position[1] + dc)

            # Loại bỏ nước đi phạm quy hoặc đụng tường [cite: 106]
            if not (0 <= next_pos[0] < height and 0 <= next_pos[1] < width) or map_state[next_pos[0], next_pos[1]] == 1:
                continue

            # Đánh giá độ an toàn của vị trí tiềm năng này
            score = self._evaluate_ghost_position(next_pos, map_state)

            if score > max_score:
                max_score = score
                best_move = move

        return best_move

    def _evaluate_ghost_position(self, pos: tuple, map_state: np.ndarray) -> float:
        """
        Hàm đánh giá phân tích rủi ro dựa trên ma trận khoảng cách bước chạy thực (True Distance)
        """
        height, width = map_state.shape
        score = 0.0

        # Tính toán lưới khoảng cách thực xuất phát từ vị trí hiện tại của Ghost
        ghost_dist_map = compute_bfs_distance_matrix(map_state, pos)

        # 1. Phạt cực nặng nếu khoảng cách thực tới vùng có mật độ Pacman cao quá ngắn 
        for r in range(height):
            for c in range(width):
                p_prob = self.tracker.belief_grid[r, c]
                if p_prob > 0.01:
                    true_dist = ghost_dist_map[r, c]
                    if true_dist == 0:
                        score -= p_prob * 10000.0  # Nguy cơ bị bắt trực tiếp 
                    elif true_dist < 4:
                        score -= p_prob * (2000.0 / true_dist)  # Quá gần tầm quét tốc độ của Pacman 
                    else:
                        score += p_prob * true_dist * 25.0  # Ưu tiên kéo giãn khoảng cách thực tế càng xa càng tốt

        # 2. Điểm thưởng ẩn nấp sương mù: Khuyến khích ẩn thân sâu trong ô -1 [cite: 106, 107]
        if map_state[pos[0], pos[1]] == -1:
            score += 40.0

        # 3. Chỉ số tự do (Mobility Score): Tính số đường thoát hiểm từ ô này
        # Tránh việc chạy xa Pacman hình học nhưng vô tình tự dồn mình vào góc chết hẹp (Dead-end)
        escape_routes = 0
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = pos[0] + dr, pos[1] + dc
            if 0 <= nr < height and 0 <= nc < width and map_state[nr, nc] != 1:
                escape_routes += 1
                
        score += escape_routes * 15.0

        return score