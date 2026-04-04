# Risk-Aware GhostAgent - Hướng Dẫn Triển Khai Chi Tiết

## 📌 Tổng Quan Chiến Lược

**Risk-Aware Strategy** là một phương pháp **thích ứng động** dựa trên khoảng cách tới Pacman. Agent đánh giá mức độ nguy hiểm và chọn hành động tương ứng.

```
┌───────────────────────────────────────────────┐
│      Nhận vị trí Pacman & bản đồ              │
└────────────┬────────────────────────────────┘
             │
             ▼
    ┌─────────────────────────┐
    │  Tính khoảng cách       │
    │  distance = |pos_ghost  │
    │             - pos_pacman│
    └────────┬────────────────┘
             │
      ┌──────┴──────────────────────┐
      │                             │
   dist ≤ 5                    dist ≤ 10
      │                             │
      ▼                             ▼
 ESCAPE PANIC              MOVE AWAY             EXPLORE
 (Tối đa hoá             STRATEGICALLY         DEAD-ENDS
  khoảng cách)           (Cân bằng)           (Tìm ngách chết)
      │                             │                │
      └─────────────────┬───────────┴────────────────┘
                        │
                        ▼
                  Return Move
```

---

## 🏗️ Cấu Trúc Class

```python
class GhostAgent(BaseGhostAgent):
    """Risk-Aware Ghost Agent"""
    
    def __init__(self, **kwargs):
        """Khởi tạo agent"""
        super().__init__(**kwargs)
        
        # Constants định nghĩa ngưỡng
        self.DANGER_DISTANCE = 5
        self.SAFE_DISTANCE = 10
        
        # Memory cho fog of war
        self.last_known_enemy_pos = None
        
        # Statistics (optional)
        self.escape_count = 0
        self.strategic_count = 0
        self.explore_count = 0
    
    def step(self, map_state, my_position, enemy_position, step_number):
        """Main decision function"""
        # Workflow gồm 5 bước
        
    # Các method theo từng strategy
    def _escape_panic(self, pos, pacman_pos, map_state):
        """High threat mode"""
        
    def _move_away_strategically(self, pos, pacman_pos, map_state):
        """Medium threat mode"""
        
    def _explore_dead_ends(self, pos, map_state):
        """Low threat mode"""
        
    def _explore_safely(self, pos, map_state):
        """Exploration khi không thấy Pacman"""
        
    # Helper methods
    def _manhattan_distance(self, pos1, pos2):
        """Tính khoảng cách"""
        
    # ... các helper khác
```

---

## 📍 Chi Tiết 5 Bước Triển Khai

### Bước 1️⃣: Cập Nhật Bộ Nhớ

**Mục đích**: Lưu vị trí cuối cùng của Pacman nếu nó biến mất (fog of war).

```python
def step(self, map_state, my_position, enemy_position, step_number):
    # Bước 1: Cập nhật bộ nhớ
    if enemy_position is not None:
        self.last_known_enemy_pos = enemy_position
        print(f"[UPDATE] Thấy Pacman ở {enemy_position}")
    else:
        print(f"[FOG] Pacman biến mất, nhớ vị trí: {self.last_known_enemy_pos}")
```

**Ví dụ**:
```
Bước 50: enemy_position = (5, 10)
         → last_known_enemy_pos = (5, 10)

Bước 51: enemy_position = None (Pacman ngoài tầm quan sát)
         → last_known_enemy_pos vẫn = (5, 10)
         → Ghost tiếp tục dùng (5, 10) để định hướng
```

---

### Bước 2️⃣: Xác Định Vị Trí Pacman Hiện Tại

**Mục đích**: Lấy vị trí Pacman thực tế hoặc vị trí cuối cùng biết được.

```python
    # Bước 2: Xác định vị trí threat
    pacman_pos = enemy_position or self.last_known_enemy_pos
```

**Trường hợp**:
```
Trường hợp A: enemy_position = (7, 8)
             → pacman_pos = (7, 8)  ✓ Vị trí thực

Trường hợp B: enemy_position = None (fog)
             → pacman_pos = (5, 10) ✓ Vị trí cuối cùng biết

Trường hợp C: enemy_position = None + last_known = None
             → pacman_pos = None    ✓ Không biết gì
```

---

### Bước 3️⃣: Xử Lý Fog of War

**Mục đích**: Khi không thấy Pacman, Ghost tìm kiếm an toàn.

```python
    # Bước 3: Nếu không biết Pacman đang ở đâu
    if pacman_pos is None:
        return self._explore_safely(my_position, map_state)
```

**Chiến lược Explore Safely**:
- Ưu tiên di chuyển tới các dead-ends (khó tìm)
- Hoặc random walk an toàn

```python
def _explore_safely(self, pos, map_state):
    """Move to dead-ends when Pacman not visible"""
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
```

---

### Bước 4️⃣: Tính Khoảng Cách

**Mục đích**: Đánh giá mức độ nguy hiểm.

```python
    # Bước 4: Tính khoảng cách Manhattan
    distance = self._manhattan_distance(my_position, pacman_pos)
```

**Manhattan Distance** (khoảng cách đô thị):
```
    Công thức: distance = |x1 - x2| + |y1 - y2|
    
    Ví dụ:
    Ghost ở (5, 5)
    Pacman ở (8, 10)
    distance = |5-8| + |5-10| = 3 + 5 = 8
    
    Biểu diễn trên bản đồ:
         0 1 2 3 4 5 6 7 8 9 10
      0
      1
      2
      3
      4
      5  . . . . . G . . . . .
      6  . . . . . . . . . . .
      7  . . . . . . . . . . .
      8  . . . . . . . . P . . .
      
      Đường shortest path: 3 xuống + 5 phải = 8 bước
```

**Implementation**:
```python
def _manhattan_distance(self, pos1, pos2):
    """Calculate Manhattan distance"""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
```

---

### Bước 5️⃣: Chọn Hành Động Dựa Trên Mức Nguy Hiểm

**Mục đích**: Lựa chọn chiến lược phù hợp.

```python
    # Bước 5: Đánh giá mức độ nguy hiểm và hành động
    if distance <= self.DANGER_DISTANCE:              # ≤ 5
        self.escape_count += 1
        return self._escape_panic(my_position, pacman_pos, map_state)
    
    elif distance <= self.SAFE_DISTANCE:              # ≤ 10
        self.strategic_count += 1
        return self._move_away_strategically(my_position, pacman_pos, map_state)
    
    else:                                              # > 10
        self.explore_count += 1
        return self._explore_dead_ends(my_position, map_state)
```

**Minh hoạ Ngưỡng**:
```
Khoảng cách (ô)
     |
  12 |        EXPLORE
     |       (CALM)
  10 |-------|
     |      STRATEGIC (CAUTION)
   5 |-------|
     |    PANIC (DANGER)
   0 |_________|_________|__________
     0        Pacman   Ghost   12
     
Ket luận:
- dist(0-5):   Chế độ PANIC - chạy trốn
- dist(5-10):  Chế độ CAUTION - rút lui cẩn thận
- dist(10+):   Chế độ CALM - tìm chỗ an toàn
```

---

## 🚨 Chi Tiết Các Sub-Strategy

### Strategy A: ESCAPE PANIC (Chế độ Hoảng Sợ)

**Kích hoạt**: `distance <= DANGER_DISTANCE (5)`

**Mục đích**: Tối đa hoá khoảng cách **ngay lập tức**.

**Logic**:
```
Hành động: Xem xét tất cả các bước di chuyển hợp lệ
         → Chọn bước làm tăng khoảng cách nhất
```

**Pseudocode**:
```
function ESCAPE_PANIC(my_pos, pacman_pos, map):
    best_move = STAY
    max_distance = manhattan_distance(my_pos, pacman_pos)
    
    for each move in [UP, DOWN, LEFT, RIGHT]:
        if is_valid_move(my_pos, move, map):
            next_pos = apply_move(my_pos, move)
            new_distance = manhattan_distance(next_pos, pacman_pos)
            
            if new_distance > max_distance:
                max_distance = new_distance
                best_move = move
    
    return best_move
```

**Implementation**:
```python
def _escape_panic(self, pos, pacman_pos, map_state):
    """Panic mode: maximize distance to Pacman"""
    best_move = Move.STAY
    max_distance = self._manhattan_distance(pos, pacman_pos)
    
    # Xem xét tất cả 4 hướng
    for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
        if self._is_valid_move(pos, move, map_state):
            next_pos = self._apply_move(pos, move)
            distance = self._manhattan_distance(next_pos, pacman_pos)
            
            # Chọn hướng làm tăng khoảng cách nhiều nhất
            if distance > max_distance:
                max_distance = distance
                best_move = move
    
    return best_move
```

**Ví dụ Thực Tế**:
```
Tình huống:
  Bản đồ 5x5:
    0 1 2 3 4
  0 # # # # #
  1 # . . . #
  2 # . G . #  Ghost ở (2, 2)
  3 # . . . #
  4 # # # # #
  
  Pacman ở (2, 1) - GẦN QUÁĨ
  distance = |2-2| + |2-1| = 0 + 1 = 1  ⚠️ NGUY HIỂM!
  
Lựa chọn:
  Move UP:    next=(1,2), dist=|1-2|+|2-1|=1+1=2  ✓
  Move DOWN:  next=(3,2), dist=|3-2|+|2-1|=1+1=2  ✓
  Move LEFT:  next=(2,1), dist=|2-2|+|1-1|=0+0=0  ✗ (bị bắt!)
  Move RIGHT: next=(2,3), dist=|2-2|+|3-1|=0+2=2  ✓
  
→ Chọn: UP hoặc DOWN hoặc RIGHT (distance = 2)
→ Thường chọn UP (đầu tiên tìm thấy)
```

---

### Strategy B: MOVE AWAY STRATEGICALLY (Rút Lui Chiến Lược)

**Kích hoạt**: `5 < distance <= 10`

**Mục đích**: Cân bằng giữa **tăng khoảng cách** và **tìm chỗ bảo vệ**.

**Công thức Điểm Số**:
```
score = distance_to_pacman + (adjacent_walls × 0.5)

Ưu tiên:
  1. Tăng khoảng cách (weight = 1.0)
  2. Gần tường (weight = 0.5)
```

**Lý do Kết Hợp**:
- Tường làm chậm Pacman di chuyển
- Dead-end khó for Pacman tìm
- Khuyến khích Ghost di chuyển tới góc/cạnh

**Pseudocode**:
```
function MOVE_AWAY_STRATEGICALLY(my_pos, pacman_pos, map):
    best_move = STAY
    best_score = -∞
    
    for each move in [UP, DOWN, LEFT, RIGHT]:
        if is_valid_move(my_pos, move, map):
            next_pos = apply_move(my_pos, move)
            
            distance = manhattan_distance(next_pos, pacman_pos)
            walls = count_adjacent_walls(next_pos, map)
            
            score = distance + (walls × 0.5)
            
            if score > best_score:
                best_score = score
                best_move = move
    
    return best_move
```

**Implementation**:
```python
def _move_away_strategically(self, pos, pacman_pos, map_state):
    """Strategic retreat: distance + wall protection"""
    best_move = Move.STAY
    best_score = -float('inf')
    
    for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
        if self._is_valid_move(pos, move, map_state):
            next_pos = self._apply_move(pos, move)
            
            # Thành phần 1: Khoảng cách
            distance = self._manhattan_distance(next_pos, pacman_pos)
            
            # Thành phần 2: Số tường xung quanh
            walls = self._count_adjacent_walls(next_pos, map_state)
            
            # Kombinasyon: ưu tiên distance, thứ hai là walls
            score = distance + walls * 0.5
            
            if score > best_score:
                best_score = score
                best_move = move
    
    return best_move
```

**Ví dụ Tính Điểm**:
```
Tình huống:
  Ghost ở (5, 5)
  Pacman ở (5, 8)
  distance = 3

Lựa chọn:
  Move UP:    next=(4,5)
    - distance = |4-5|+|5-8| = 1+3 = 4
    - walls = 1 (one wall above)
    - score = 4 + 1×0.5 = 4.5
    
  Move DOWN:  next=(6,5)
    - distance = |6-5|+|5-8| = 1+3 = 4
    - walls = 0
    - score = 4 + 0×0.5 = 4.0
    
  Move LEFT:  next=(5,4)
    - distance = |5-5|+|4-8| = 0+4 = 4
    - walls = 2 (corner!)
    - score = 4 + 2×0.5 = 5.0  ⭐ TỐT NHẤT
    
  Move RIGHT: next=(5,6)
    - distance = |5-5|+|6-8| = 0+2 = 2
    - walls = 1
    - score = 2 + 1×0.5 = 2.5

→ Chọn: LEFT (score = 5.0)
  Vì vừa tăng khoảng cách vừa có tường bảo vệ
```

---

### Strategy C: EXPLORE DEAD-ENDS (Tìm Ngách Chết)

**Kích hoạt**: `distance > SAFE_DISTANCE (10)`

**Mục đích**: Tận dụng **vị trí an toàn** để quay trở lại vị trí khó tiếp cận.

**Logic**:
```
Khi Pacman còn xa:
  → Ghost không cần chạy ngay
  → Thay vào đó, tìm dead-ends (nơi có nhiều tường)
  → Dead-ends khó cho Pacman tiếp cận
  → Giữ vị trí chiến lược
```

**Pseudocode**:
```
function EXPLORE_DEAD_ENDS(my_pos, map):
    best_move = STAY
    best_wall_count = count_adjacent_walls(my_pos, map)
    
    for each move in [UP, DOWN, LEFT, RIGHT]:
        if is_valid_move(my_pos, move, map):
            next_pos = apply_move(my_pos, move)
            wall_count = count_adjacent_walls(next_pos, map)
            
            if wall_count > best_wall_count:
                best_wall_count = wall_count
                best_move = move
    
    return best_move
```

**Implementation**:
```python
def _explore_dead_ends(self, pos, map_state):
    """Low threat: explore dead-end corridors"""
    best_move = Move.STAY
    best_deadend_score = self._count_adjacent_walls(pos, map_state)
    
    # Tìm vị trí có nhiều tường xung quanh nhất
    for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
        if self._is_valid_move(pos, move, map_state):
            next_pos = self._apply_move(pos, move)
            wall_count = self._count_adjacent_walls(next_pos, map_state)
            
            if wall_count > best_deadend_score:
                best_deadend_score = wall_count
                best_move = move
    
    return best_move
```

**Giải Thích Count Adjacent Walls**:
```
Bản đồ 3x3:
    0 1 2
  0 # . #
  1 # G #
  2 # . #

Ghost ở (1, 1)
Adjacent positions:
  - (0, 1): wall (#) ✓ count=1
  - (2, 1): wall (#) ✓ count=2
  - (1, 0): wall (#) ✓ count=3
  - (1, 2): wall (#) ✓ count=4

Total: 4 walls = Hoàn toàn bao vây (dead-end)

Implementation:
def _count_adjacent_walls(self, pos, map_state):
    walls = 0
    for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
        next_pos = self._apply_move(pos, move)
        if not self._is_valid_position(next_pos, map_state):
            walls += 1  # Out of bounds or wall
    return walls
```

**Ví dụ Thực Tế**:
```
Mê cung (dead-ends highlighted with *)

Main corridor:    Dead-ends (safe):
  . . . . .         * . . *
  . G . . .         . . . .
  . . P . .         * . . *

Khi distance > 10 (an toàn):
  → Ghost nên di chuyển tới *, không ở main corridor
  → Dead-end khó cho Pacman vào → time để thoát
```

---

## 🛠️ Helper Methods

### 1. Manhattan Distance

```python
def _manhattan_distance(self, pos1, pos2):
    """
    Tính khoảng cách Manhattan (đô thị) giữa 2 điểm.
    Formula: |x1 - x2| + |y1 - y2|
    """
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
```

### 2. Valid Move Check

```python
def _is_valid_move(self, pos, move, map_state):
    """
    Kiểm tra xem bước di chuyển có hợp lệ không.
    Hợp lệ = vị trí tiếp theo nằm trong map và không là tường.
    """
    next_pos = self._apply_move(pos, move)
    return self._is_valid_position(next_pos, map_state)
```

### 3. Position Validation

```python
def _is_valid_position(self, pos, map_state):
    """
    Kiểm tra vị trí có nằm trong map và không phải tường.
    - cell = 0: empty ✓
    - cell = 1: wall ✗
    - cell = -1: unseen (assume không thể đi) ✗
    """
    row, col = pos
    height, width = map_state.shape
    
    # Check bounds
    if row < 0 or row >= height or col < 0 or col >= width:
        return False
    
    # Check wall or unseen
    return map_state[row, col] == 0
```

### 4. Apply Move

```python
def _apply_move(self, pos, move):
    """
    Áp dụng bước di chuyển, tính vị trí mới.
    Move enum có attribute .value = (delta_row, delta_col)
    """
    delta_row, delta_col = move.value
    return (pos[0] + delta_row, pos[1] + delta_col)
```

### 5. Count Adjacent Walls

```python
def _count_adjacent_walls(self, pos, map_state):
    """
    Đếm số tường hoặc biên xung quanh vị trí.
    Dùng cho strategy explore_dead_ends.
    Cao = dead-end = an toàn
    """
    walls = 0
    for move in [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]:
        next_pos = self._apply_move(pos, move)
        if not self._is_valid_position(next_pos, map_state):
            walls += 1
    return walls
```

---

## 📊 Flow Diagram Đầy Đủ

```
                    ┌──────────────────────────┐
                    │  Ghost.step() gọi lần i  │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │ Bước 1: Cập nhật memory  │
                    │ if enemy_position != None
                    │   last_known_enemy = ...│
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │ Bước 2: Xác định threat  │
                    │ threat = enemy_pos or    │
                    │          last_known_pos  │
                    └────────────┬─────────────┘
                                 │
                          ┌──────▼──────┐
                          │ threat      │
                          │ == None?    │
                          └──┬──────┬───┘
                        (yes)│      │(no)
                    ┌────────▼──┐   │
                    │EXPLORE    │   │
                    │ SAFELY    │   │
                    └───────────┘   │
                                    │
                         ┌──────────▼──────────┐
                         │ Bước 4: Tính distance│
                         │ d = manhattan(pos,  │
                         │     threat)         │
                         └──────────┬──────────┘
                                    │
            ┌───────────────────────┼───────────────────┐
            │                       │                   │
        dist ≤ 5              5 < dist ≤ 10          dist > 10
            │                       │                   │
            ▼                       ▼                   ▼
      ┌─────────────┐      ┌──────────────┐    ┌────────────────┐
      │ESCAPE PANIC │      │STRATEGIC     │    │EXPLORE DEAD    │
      │- Max        │      │MOVE          │    │ENDS            │
      │  distance   │      │- Balance:    │    │- Find walls    │
      │- Greedy OK  │      │  dist +walls │    │- Safe area     │
      └──────┬──────┘      └──────┬───────┘    └────────┬───────┘
             │                    │                     │
             └────────────┬───────┴─────────────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │ Return Move │
                   └─────────────┘
```

---

## 🎯 Tuning Parameters

### Ngưỡng Khoảng Cách

```python
# Default (cho maze 16x16)
DANGER_DISTANCE = 5    # Cảnh báo đỏ
SAFE_DISTANCE = 10     # An toàn xanh

# Cho maze nhỏ (8x8)
DANGER_DISTANCE = 3
SAFE_DISTANCE = 6

# Cho maze lớn (32x32)
DANGER_DISTANCE = 8
SAFE_DISTANCE = 15

# Dynamic based on map size
map_h, map_w = map_state.shape
self.DANGER_DISTANCE = (map_h + map_w) // 4
self.SAFE_DISTANCE = (map_h + map_w) // 2
```

### Trọng Số Scoring

```python
# Hiện tại (cân bằng)
score = distance + walls * 0.5

# Ưu tiên tường (dead-end seekers)
score = distance + walls * 1.0

# Ưu tiên khoảng cách (runners)
score = distance + walls * 0.2
```

---

## ✅ Checklist Implement Chi Tiết

### Phase 1: Cấu Trúc Cơ Bản
- [ ] Override `__init__` với constants
- [ ] Override `step` với 5-bước logic
- [ ] Memory tracking: `last_known_enemy_pos`

### Phase 2: Threat Assessment
- [ ] Implement `_manhattan_distance`
- [ ] Implement distance calculation in `step`
- [ ] Test: verify distance giảm khi xa Pacman

### Phase 3: Escape Mode
- [ ] Implement `_escape_panic`
- [ ] Verify: chọn bước làm **tăng** distance
- [ ] Test: di chuyển ngược hướng Pacman

### Phase 4: Strategic Mode
- [ ] Implement `_move_away_strategically`
- [ ] Implement `_count_adjacent_walls`
- [ ] Test: ưu tiên dead-ends

### Phase 5: Explore Mode
- [ ] Implement `_explore_dead_ends`
- [ ] Implement `_explore_safely`
- [ ] Test: di chuyển tới góc khi an toàn

### Phase 6: Helper Methods
- [ ] Implement `_is_valid_move`
- [ ] Implement `_is_valid_position`
- [ ] Implement `_apply_move`

### Phase 7: Testing & Debug
- [ ] Test vs example_student
- [ ] Monitor: escape_count, strategic_count, explore_count
- [ ] Tune thresholds nếu cần

---

##  🚀 Ví Dụ Chạy Đầy Đủ

```python
# Sequence of steps
map_state = [
    [1,1,1,1,1],
    [1,0,0,0,1],
    [1,0,G,0,1],  # G = Ghost at (2, 2)
    [1,0,0,0,1],
    [1,1,1,1,1]
]

step 50:
  - my_position = (2, 2)
  - enemy_position = (2, 1)  # Pacman at (2, 1)
  - distance = 1  <= DANGER_DISTANCE (5)
  - MODE: ESCAPE PANIC
  - Options: UP(2,2)→(1,2)=dist 2, DOWN→(3,2)=dist 2
  - Return: Move.UP (first valid with max distance)

step 51:
  - my_position = (1, 2)
  - enemy_position = (2, 1)  # Pacman moved too?
  - distance = 2  <= DANGER_DISTANCE (5)
  - MODE: ESCAPE PANIC
  - Try more distance...

step 60:
  - my_position = (1, 1)
  - enemy_position = None  # Lost sight!
  - last_known = (3, 1)
  - distance = 2  <= DANGER_DISTANCE
  - MODE: ESCAPE PANIC
  - Move based on last known position

step 65:
  - my_position = (1, 1)
  - enemy_position = (1, 4)  # Can see again!
  - distance = 3  <= DANGER_DISTANCE
  - MODE: ESCAPE PANIC
  - Update last_known to (1, 4)

step 120:
  - my_position = (2, 2)
  - enemy_position = (1, 0)  (if we could see)
  - distance = 3  <= SAFE_DISTANCE (10)
  - MODE: STRATEGIC MOVE
  - Calculate walls around each next position
  - Choose: distance + walls*0.5

step 180:
  - my_position = (3, 3)
  - enemy_position = None  (or far away)
  - distance = 15  > SAFE_DISTANCE (10)
  - MODE: EXPLORE DEAD ENDS
  - Count adjacent walls
  - Move towards corners

step 199:
  - Still alive! 🎉
  - Test successful!
```

---

## 🎓 Tóm Tắt

**Risk-Aware Strategy = Adaptive + Intelligent**

| Ngưỡng | Mode | Hành Động |
|--------|------|----------|
| ≤ 5 | PANIC | Tối đa hoá distance |
| 5-10 | CAUTION | Distance + wall cover |
| 10+ | CALM | Tìm dead-ends |

**Lợi ích**:
- ✅ Thích ứng động với threat
- ✅ Hiệu suất cao
- ✅ Khó dự đoán
- ✅ Code sạch & dễ debug

**Tiếp Theo**:
- Tuning parameters cho maze của bạn
- Add statistics tracking
- Optimize scoring function
- Maybe add A* pathfinding (advanced)

---

Good luck! 🍀
