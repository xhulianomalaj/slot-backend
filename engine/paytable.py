from engine.symbols import (
    BAR, BELL, CHERRY, LEMON, ORANGE, PLUM, SCATTER, SEVEN, WILD,
)

# Multipliers × line bet.
# Scatter is the exception — it multiplies × total bet (evaluated separately).
PAYOUTS: dict[str, dict[int, float]] = {
    SEVEN:   {3: 50,   4: 200,  5: 1000},
    WILD:    {3: 100,  4: 500,  5: 2500},
    BAR:     {3: 25,   4: 100,  5: 500},
    BELL:    {3: 15,   4: 60,   5: 250},
    CHERRY:  {3: 10,   4: 40,   5: 150},
    PLUM:    {3: 8,    4: 30,   5: 100},
    ORANGE:  {3: 5,    4: 20,   5: 60},
    LEMON:   {3: 5,    4: 15,   5: 50},
    SCATTER: {3: 5,    4: 20,   5: 100},
}

# 20 paylines — each tuple is (row_reel0, row_reel1, …, row_reel4).
# Row 0 = top, 1 = middle, 2 = bottom.
# Adjacent reels differ by at most 1 row (no 2-row jumps).
PAYLINES: list[tuple[int, int, int, int, int]] = [
    (1, 1, 1, 1, 1),  #  1 — middle row straight
    (0, 0, 0, 0, 0),  #  2 — top row straight
    (2, 2, 2, 2, 2),  #  3 — bottom row straight
    (0, 1, 2, 1, 0),  #  4 — V-down
    (2, 1, 0, 1, 2),  #  5 — V-up
    (1, 0, 1, 0, 1),  #  6 — zigzag high
    (1, 2, 1, 2, 1),  #  7 — zigzag low
    (0, 0, 1, 2, 2),  #  8 — diagonal down-right
    (2, 2, 1, 0, 0),  #  9 — diagonal up-right
    (0, 1, 1, 1, 0),  # 10 — shallow V-down
    (2, 1, 1, 1, 2),  # 11 — shallow V-up
    (1, 0, 0, 0, 1),  # 12 — U-shape top
    (1, 2, 2, 2, 1),  # 13 — U-shape bottom
    (0, 1, 0, 1, 0),  # 14 — hi-lo alternating
    (2, 1, 2, 1, 2),  # 15 — lo-hi alternating
    (0, 0, 1, 0, 0),  # 16 — top dip centre
    (2, 2, 1, 2, 2),  # 17 — bottom dip centre
    (1, 1, 0, 1, 1),  # 18 — mid peak up
    (1, 1, 2, 1, 1),  # 19 — mid peak down
    (0, 1, 2, 2, 1),  # 20 — slide down
]

LINE_COUNT = len(PAYLINES)  # 20
