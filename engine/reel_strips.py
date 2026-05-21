import random

from engine.symbols import (
    BAR, BELL, CHERRY, LEMON, ORANGE, PLUM, SCATTER, SEVEN, WILD,
)

# Strip weights — each value is how many times that symbol appears on the strip.
# All reels use exactly 33 stops with exactly 1 scatter each.
#
# Scatter maths (hypergeometric, s=1, n=33):
#   P(scatter visible on any reel) = 3/33 = 9.09%
#   P(trigger ≥3 scatter across grid) ≈ 0.653% → 1 in ~153 spins
#   P(near-miss, exactly 2 scatter)  ≈ 6.2%  → 1 in ~16 spins
#
# Reel 4 is the hardest to complete premium 5-of-a-kind (fewest seven/bar).
STRIP_WEIGHTS: list[dict[str, int]] = [
    # Reel 0 — leftmost  (total: 33)
    {CHERRY: 7, LEMON: 6, ORANGE: 5, PLUM: 4, BELL: 4, BAR: 3, SEVEN: 2, WILD: 1, SCATTER: 1},
    # Reel 1              (total: 33)
    {CHERRY: 6, LEMON: 6, ORANGE: 5, PLUM: 4, BELL: 4, BAR: 3, SEVEN: 2, WILD: 2, SCATTER: 1},
    # Reel 2 — middle    (total: 33)
    {CHERRY: 7, LEMON: 6, ORANGE: 5, PLUM: 4, BELL: 4, BAR: 3, SEVEN: 2, WILD: 1, SCATTER: 1},
    # Reel 3              (total: 33)
    {CHERRY: 6, LEMON: 6, ORANGE: 5, PLUM: 4, BELL: 4, BAR: 3, SEVEN: 2, WILD: 2, SCATTER: 1},
    # Reel 4 — rightmost (total: 33) — fewer premium symbols, harder to 5-of-a-kind
    {CHERRY: 8, LEMON: 7, ORANGE: 5, PLUM: 4, BELL: 3, BAR: 3, SEVEN: 1, WILD: 1, SCATTER: 1},
]


def build_strip(weights: dict[str, int]) -> list[str]:
    """Expand symbol weights into a flat strip, then shuffle (Fisher-Yates)."""
    strip: list[str] = []
    for symbol, count in weights.items():
        strip.extend([symbol] * count)
    random.shuffle(strip)
    return strip


def build_all_strips(num_reels: int = 5) -> list[list[str]]:
    """Build one strip per reel, cycling STRIP_WEIGHTS if num_reels > 5."""
    return [
        build_strip(STRIP_WEIGHTS[i % len(STRIP_WEIGHTS)])
        for i in range(num_reels)
    ]


def spin_reel(strip: list[str]) -> list[str]:
    """Pick a uniformly random stop and return 3 consecutive symbols."""
    stop = random.randrange(len(strip))
    n = len(strip)
    return [
        strip[stop],
        strip[(stop + 1) % n],
        strip[(stop + 2) % n],
    ]
