from engine.symbols import (
    BAR, BELL, CHERRY, LEMON, ORANGE, PLUM, SCATTER, SEVEN, WILD,
)

# Payout multipliers expressed in units of line bet (= total bet / LINE_COUNT).
# "POPULAR-SLOT" LDW profile: low symbols pay TINY 3-of-a-kinds so most wins are
# sub-bet ("losses disguised as wins"), with the return back-loaded into a steep,
# rare premium tail. Calibrated by EXACT enumeration to total RTP ~97.0% (verified
# by 20M-spin Monte Carlo — see simulate_rtp.py / simulation/rtp_check.py and
# MATH_MODEL.md). Hit frequency ~41%, sigma/bet ~4.1 (MEDIUM volatility).
PAYOUTS: dict[str, dict[int, float]] = {
    SEVEN:   {3: 52,   4: 328,  5: 4277},
    WILD:    {3: 116,  4: 799,  5: 7415},
    BAR:     {3: 28,   4: 122,  5: 670},
    BELL:    {3: 17,   4: 67,   5: 309},
    CHERRY:  {3: 6,    4: 26,   5: 135},
    PLUM:    {3: 9,    4: 34,   5: 155},
    ORANGE:  {3: 5,    4: 22,   5: 113},
    LEMON:   {3: 5,    4: 18,   5: 93},
    # SCATTER pays no money — 3 anywhere awards FREE_SPINS_COUNT free spins only.
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
