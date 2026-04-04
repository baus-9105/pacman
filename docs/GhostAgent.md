# GhostAgent - Chiến Lược Trốn Tránh & Tài Liệu Tiếp Cận Bài Toán

## 📚 Mục Lục

1. [Phân tích Bài Toán](#phân-tích-bài-toán)
2. [Các Chiến Lược](#các-chiến-lược)
3. [Triển Khai Chi Tiết](#triển-khai-chi-tiết)
4. [Phân Tích Độ Phức Tạp](#phân-tích-độ-phức-tạp)
5. [Tips & Best Practices](#tips--best-practices)
6. [Debugging & Testing](#debugging--testing)

---

## 🎮 Phân Tích Bài Toán

### Định Nghĩa Vấn Đề

**Mục tiêu Ghost**: Tồn tại càng lâu càng tốt mà không bị Pacman bắt.

**Ràng buộc**:
- Ghost và Pacman chuyển động **đồng thời** → không thể phản ứng tức thời
- Ghost nhận thông tin về vị trí Pacman (nếu trong tầm quan sát)
- Ghost phải di chuyển trên lưới maze (tránh tường)
- Trò chơi kết thúc khi: Pacman bắt được Ghost HOẶC vượt quá max_steps (200)

### Các Yếu Tố Quyết Định Thành Công

| Yếu Tố | Tác Động | Độ Quan Trọng |
|--------|--------|-------------|
| **Khoảng cách** | Càng xa Pacman càng tốt | ⭐⭐⭐⭐⭐ |
| **Dự đoán** | Dự đoán hướng Pacman để tránh | ⭐⭐⭐⭐ |
| **Vị trí chiến lược** | Chọn vị trí khó tiếp cận | ⭐⭐⭐⭐ |
| **Tường bảo vệ** | Dùng tường làm rào cản | ⭐⭐⭐ |
| **Động lực** | Có pattern rõ ràng hay random? | ⭐⭐ |

### Mô Hình Trò Chơi

```
┌─────────────────────────────────────────┐
│  Bước t                                  │
│  ┌────────────────────────────────────┐ │
│  │ 1. Ghost nhận: map, my_pos, enemy  │ │
│  │ 2. Pacman nhận: map, my_pos, enemy │ │
│  └───────┬────────────────────┬───────┘ │
│          │                    │         │
│    Ghost quyết định      Pacman quyết định
│        Move G               Move P      │
│          │                    │         │
│  ┌───────▼────────────────────▼───────┐ │
│  │ Cập nhật vị trí đồng thời          │ │
│  │ pos_ghost = pos_ghost + Move_G     │ │
│  │ pos_pacman = pos_pacman + Move_P   │ │
│  └───────┬─────────────────────────────┘ │
│          │                               │
│    ┌─────▼──────────────┐              │
│    │ Kiểm tra chiến thắng │              │
│    │ caught = (dist <= 0) │              │
│    └────────────────────┘              │
└─────────────────────────────────────────┘
         Bước t+1
```

---

## 🎯 Các Chiến Lược

### Chiến Lược 1️⃣: Random (Baseline)

```
Ưu điểm:
  ✓ Dễ implement (1 dòng code)
  ✓ Khó dự đoán

Nhược điểm:
  ✗ Không tối ưu
  ✗ Thường bị bắt sớm
  ✗ Không dùng thông tin có sẵn
```

### Chiến Lược 2️⃣: Distance Maximization (Tối đa hoá khoảng cách)

**Ý tưởng**: Luôn chọn bước đi làm **tăng maximum** khoảng cách tới Pacman.

```python
best_move = argmax_move(distance_after_move(move, pacman_pos))
```

**Ưu điểm**:
- ✓ Tuyến tính O(4) = O(1)
- ✓ Thường hiệu quả khi xa Pacman
- ✓ Dễ implement

**Nhược điểm**:
- ✗ Cục bộ optimal (không toàn bộ tối ưu)
- ✗ Có thể bị "kẹt" ở dead-end

**Khi nào dùng**: Priority 2️⃣ - Dùng khi Pacman gần

---

### Chiến Lược 3️⃣: Wall-Hugging (Dùng Tường Làm Rào Cản)

**Ý tưởng**: Ưu tiên di chuyển tới các vị trí có nhiều **tường xung quanh** (dead-ends).

```python
wall_score = count_adjacent_walls(next_pos)
best_move = argmax_move(wall_score)
```

**Lý do**: 
- Dead-ends khó tiếp cận hơn (Pacman phải đi dài)
- Là "hang ổn định" tự nhiên

```
Maze Layout:
                ┌─────────────────┐
                │ Dead-end (3 tường)
                │ [Rất An toàn]
    Main Path   │
 ┌──────────────┘
 │ (1 tường)
 │ [Kém An toàn]
```

**Ưu điểm**:
- ✓ Chiến lược dài hạn tốt
- ✓ Passive defense hiệu quả
- ✓ O(4) per step

**Nhược điểm**:
- ✗ Kém khi Pacman gần (cần chạy trốn ngay)
- ✗ Có thể bị "bao vây" ở dead-end

**Khi nào dùng**: Priority 3️⃣ - Dùng khi an toàn

---

### Chiến Lược 4️⃣: Prediction-Based (Dự đoán)

**Ý tưởng**: Dự đoán hướng di chuyển của Pacman, rồi **di chuyển ngược lại**.

```python
predicted_direction = estimate_direction(last_pacman_pos, current_pacman_pos)
best_move = opposite_direction(predicted_direction)
```

**Ứng dụng**:
```
Bước t-1: Pacman ở (5, 5)
Bước t:   Pacman ở (5, 7)
          → Pacman di chuyển hướng PHẢI
          → Ghost nên di chuyển hướng TRÁI
```

**Ưu điểm**:
- ✓ Dự phòng tấn công trực tiếp
- ✓ Xây dựng intuition tốt

**Nhược điểm**:
- ✗ Chỉ dựa trên 1 lần di chuyển
- ✗ Con đường ngược có thể bị chặn

**Khi nào dùng**: Priority 2️⃣ - Kết hợp với Distance Maximization

---

### Chiến Lược 5️⃣: Risk-Aware (Thích Ứng Theo Mối Đe Dọa) ⭐ **TỐI ƯU**

**Ý tưởng**: Kết hợp tất cả các chiến lược dựa trên **mức độ nguy hiểm**.

```
Mức Nguy Hiểm = Khoảng cách tới Pacman

Nếu dist <= 5:
    Chế độ PANIC → Tối đa hoá khoảng cách ngay
    
Nếu 5 < dist <= 10:
    Chế độ CAUTION → Cân bằng (khoảng cách + tường)
    
Nếu dist > 10:
    Chế độ CALM → Khám phá dead-ends
```

**Ưu điểm**:
- ✓ Thích ứng với tình huống động
- ✓ Kết hợp ưu điểm của tất cả chiến lược
- ✓ Hiệu suất cao

**Nhược điểm**:
- ✗ Phức tạp hơn
- ✗ Cần tuning parameters

**Khi nào dùng**: Priority 1️⃣ - **KHUYẾN CÁO SỬ DỤNG**

---

## 📝 Triển Khai Chi Tiết

### Cấu Trúc Cơ Bản

```python
class GhostAgent(BaseGhostAgent):
    def __init__(self, **kwargs):
        # Khởi tạo constants
        self.DANGER_DISTANCE = 5
        self.SAFE_DISTANCE = 10
        self.last_known_enemy_pos = None
    
    def step(self, map_state, my_position, enemy_position, step_number):
        # 1. Cập nhật bộ nhớ
        if enemy_position is not None:
            self.last_known_enemy_pos = enemy_position
        
        pacman_pos = enemy_position or self.last_known_enemy_pos
        
        # 2. Xử lý fog of war
        if pacman_pos is None:
            return self._explore_safely(my_position, map_state)
        
        # 3. Đánh giá mối đe dọa
        distance = self._manhattan_distance(my_position, pacman_pos)
        
        # 4. Chọn chiến lược
        if distance <= self.DANGER_DISTANCE:
            return self._escape_panic(my_position, pacman_pos, map_state)
        elif distance <= self.SAFE_DISTANCE:
            return self._move_away_strategically(my_position, pacman_pos, map_state)
        else:
            return self._explore_dead_ends(my_position, map_state)
    
    # Helper methods...
```

### Hàm Helper Cần Thiết

#### 1. Manhattan Distance
```python
def _manhattan_distance(self, pos1, pos2):
    """Tính khoảng cách Manhattan giữa 2 điểm."""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
```

#### 2. Valid Move Check
```python
def _is_valid_move(self, pos, move, map_state):
    """Kiểm tra xem bước di chuyển có hợp lệ không."""
    next_pos = self._apply_move(pos, move)
    return self._is_valid_position(next_pos, map_state)

def _is_valid_position(self, pos, map_state):
    """Kiểm tra vị trí có nằm trong map và không là tường."""
    row, col = pos
    height, width = map_state.shape
    
    # Check bounds
    if row < 0 or row >= height or col < 0 or col >= width:
        return False
    
    # Check wall
    return map_state[row, col] == 0
```

#### 3. Count Adjacent Walls
```python
def _count_adjacent_walls(self, pos, map_state):
    """Đếm số tường xung quanh vị trí (chỉ số cao = dead-end)."""
    walls = 0
    for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
        next_pos = self._apply_move(pos, move)
        if not self._is_valid_position(next_pos, map_state):
            walls += 1
    return walls
```

#### 4. Apply Move
```python
def _apply_move(self, pos, move):
    """Áp dụng bước di chuyển để tính vị trí tiếp theo."""
    delta_row, delta_col = move.value
    return (pos[0] + delta_row, pos[1] + delta_col)
```

---

## 📊 Phân Tích Độ Phức Tạp

### Time Complexity

| Chiến Lược | Complexity | Ghi Chú |
|-----------|-----------|--------|
| Random | O(1) | Chọn random từ 5 movement |
| Distance Max | O(4) = O(1) | Lặp 4 hướng, kiểm tra distance |
| Wall-Hugging | O(4 × S) | S = số bước kiểm tra |
| Prediction | O(5) | Dự đoán + tìm opposite |
| Risk-Aware | O(20) = O(1) | Kết hợp nhưng vẫn hằng số |

**Tất cả đều O(1) per step** ✓ (không phụ thuộc kích thước map)

### Space Complexity

| Chiến Lược | Space | Storage |
|-----------|-------|---------|
| Random | O(1) | Không lưu gì |
| Distance Max | O(1) | 1-2 variables |
| Wall-Hugging | O(1) | 1-2 variables |
| Prediction | O(1) | Lưu last_pos |
| Risk-Aware | O(1) | Lưu constants + last_pos |

**Tất cả đều O(1)** ✓

---

## 💡 Tips & Best Practices

### 1. **Tuning Parameters**

```python
# Điều chỉnh ngưỡng dựa trên kích thước map
map_height, map_width = map_state.shape
DANGER_DISTANCE = max(5, (map_height + map_width) // 8)
SAFE_DISTANCE = max(10, (map_height + map_width) // 4)
```

### 2. **Handle Fog of War**

```python
def step(self, map_state, my_position, enemy_position, step_number):
    # Luôn cập nhật bộ nhớ khi thấy enemy
    if enemy_position is not None:
        self.last_known_enemy_pos = enemy_position
    
    # Sử dụng last known hoặc None
    current_threat = enemy_position or self.last_known_enemy_pos
```

### 3. **Prioritize Valid Moves**

```python
# Thay vì random fallback, ưu tiên moves có khoảng cách tốt
valid_moves = []
for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
    if self._is_valid_move(pos, move, map_state):
        valid_moves.append(move)

if valid_moves:
    # Chọn best từ valid_moves
    best = max(valid_moves, key=lambda m: score(m))
else:
    return Move.STAY
```

### 4. **Avoid Oscillation**

```python
# ❌ KHÔNG LÀM: Quay lại và quay lại
# Bước t:   Move RIGHT
# Bước t+1: Move LEFT (quay lại)

# ✅ LÀM: Ưu tiên tiếp tục hướng hiện tại
def _prefer_continued_direction(self, last_move, map_state, pos, target):
    """Ưu tiên tiếp tục hướng cũ nếu có thể."""
    if self._is_valid_move(pos, last_move, map_state):
        return last_move
    # Fallback: chọn bước tốt nhất
    ...
```

### 5. **Cache Common Computations**

```python
def __init__(self, **kwargs):
    # Tính sẵn nếu cần
    self.neighbor_moves = [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]
    self.cache_wall_count = {}
```

---

## 🐛 Debugging & Testing

### Quy Trình Test

```bash
# Test cơ bản
python arena.py --seek example_student --hide WAG

# Test với visualization
python arena.py --seek example_student --hide WAG --visualizer

# Test với timeout
python arena.py --seek example_student --hide WAG --timeout 5

# Test lặp lại
for i in {1..10}; do python arena.py --seek example_student --hide WAG; done
```

### Các Chỉ Số Để Monitor

```python
# 1. Bao lâu bị bắt?
steps_survived = step_number_when_caught

# 2. Strategy được gọi bao nhiêu lần?
self.escape_panic_count += 1
self.strategic_move_count += 1
self.explore_count += 1

# 3. Hiệu suất di chuyển
distance_to_pacman_history = []
```

### Common Issues & Solutions

| Vấn Đề | Nguyên Nhân | Giải Pháp |
|--------|-----------|---------|
| Bị bắt sớm | DANGER threshold quá cao | Giảm DANGER_DISTANCE |
| Bị kẹt trong dead-end | Logic không thoát | Thêm escape heuristic |
| Quá random | Weighting sai | Điều chỉnh scoring function |
| Quá dự đoán | Dựa vào last_pos sai | Clear history khi mất sight |

### Profiling & Optimization

```python
import time

class GhostAgent(BaseGhostAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.timing = {'escape': 0, 'strategic': 0, 'explore': 0}
    
    def step(self, map_state, my_position, enemy_position, step_number):
        if distance <= self.DANGER_DISTANCE:
            start = time.time()
            result = self._escape_panic(...)
            self.timing['escape'] += time.time() - start
            return result
        # ...
    
    def print_stats(self):
        print(f"Timing: {self.timing}")
```

---

## 🚀 Lộ Trình Cải Thiện

### Level 1: Baseline (Bắt Đầu)
- [ ] Implement Random movement
- [ ] Test basic mechanics
- Target: Tồn tại 30 bước

### Level 2: Distance Optimization
- [ ] Implement Distance Maximization
- [ ] Verify valid move checking
- Target: Tồn tại 100 bước

### Level 3: Strategic Movement
- [ ] Add Wall-Hugging logic
- [ ] Implement dual-mode (panic + calm)
- Target: Tồn tại 150 bước

### Level 4: Advanced (Risk-Aware)
- [ ] Implement 3-level threat assessment
- [ ] Add prediction module
- [ ] Optimize scoring function
- Target: Tồn tại 180+ bước

### Level 5: Elite (Fine-tuning)
- [ ] A* for optimal paths (nếu cần)
- [ ] Probability heatmaps
- [ ] Machine learning predictions
- Target: Tồn tại 195+ bước

---

## 📚 Tài Liệu Tham Khảo

### Concepts
- **Graph Search**: BFS, DFS (có thể dùng cho planning)
- **Game Theory**: Minimax, Zero-sum games
- **Heuristics**: Manhattan distance, Wall proximity

### Thuật Toán Nâng Cao (Optional)
- **A\* Search**: Tìm optimal escape path
- **Minimax**: Dự đoán tối ưu của Pacman
- **Monte Carlo Tree Search**: Sampling các lối thoát

### Đọc Thêm
- `STUDENT_GUIDE.md` - Hướng dẫn chung
- `arena.py` - Hiểu luật chơi
- `environment.py` - Move mechanics

---

## ✅ Checklist Trước Khi Submit

- [ ] Code compile không lỗi
- [ ] GhostAgent đúng interface
- [ ] `step()` return `Move` enum
- [ ] Helper functions hoạt động đúng
- [ ] Handle `enemy_position = None`
- [ ] Handle `map_state` với wall/empty/fog
- [ ] Test ít nhất 5 ván
- [ ] Ghi log cho debugging nếu cần

---

**Chúc bạn may mắn! 🍀**
