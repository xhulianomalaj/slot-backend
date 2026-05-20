import random

from engine.symbols import (
    BAR, BELL, CHERRY, LEMON, ORANGE, PLUM, SCATTER, SEVEN, WILD,
)

# Strip weights — each value is how many times that symbol appears on the strip.
# Higher count = more stops = higher probability of landing in the 3-row window.
# Outer reels (0, 4) are weighted heavier on low-value symbols so long combos
# are rare, keeping RTP well-controlled on 5-of-a-kind pays.
STRIP_WEIGHTS: list[dict[str, int]] = [
    # Reel 0 — leftmost
    {CHERRY: 8, LEMON: 7, ORANGE: 6, PLUM: 5, BELL: 4, BAR: 3, SEVEN: 2, WILD: 1, SCATTER: 2},
    # Reel 1
    {CHERRY: 7, LEMON: 7, ORANGE: 6, PLUM: 5, BELL: 4, BAR: 3, SEVEN: 2, WILD: 1, SCATTER: 2},
    # Reel 2 — middle: one extra scatter for near-miss anticipation
    {CHERRY: 7, LEMON: 6, ORANGE: 5, PLUM: 5, BELL: 4, BAR: 3, SEVEN: 2, WILD: 1, SCATTER: 3},
    # Reel 3
    {CHERRY: 8, LEMON: 7, ORANGE: 6, PLUM: 5, BELL: 4, BAR: 3, SEVEN: 2, WILD: 1, SCATTER: 2},
    # Reel 4 — rightmost: hardest reel to complete 5-of-a-kind
    {CHERRY: 9, LEMON: 8, ORANGE: 6, PLUM: 5, BELL: 4, BAR: 3, SEVEN: 2, WILD: 1, SCATTER: 2},
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
