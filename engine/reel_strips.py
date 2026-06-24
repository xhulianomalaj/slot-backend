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

# ─── Certified fixed reelset ──────────────────────────────────────────────────
# The live game uses a FIXED, certified reel ORDER — it is NOT reshuffled per
# session — so the RTP is a single deterministic number: 96.98% (exact, see
# analyze_math.py). Each strip has exactly the composition in STRIP_WEIGHTS above
# (33 stops, 1 scatter); only the arrangement is frozen. This array MUST stay
# byte-identical to the mock's REEL_STRIPS in my-slot
# (src/infrastructure/network/MockNetworkManager.ts) so client and server
# evaluate the same reels. STRIP_WEIGHTS is kept for the composition-only maths
# in analyze_math.py.
REEL_STRIPS: list[list[str]] = [
    ["lemon", "bar", "orange", "bell", "seven", "seven", "bell", "cherry", "lemon", "plum", "scatter", "orange", "lemon", "bar", "cherry", "wild", "cherry", "cherry", "bell", "orange", "lemon", "lemon", "plum", "bar", "plum", "cherry", "bell", "orange", "orange", "lemon", "plum", "cherry", "cherry"],
    ["lemon", "bell", "bell", "bell", "cherry", "orange", "bar", "plum", "orange", "lemon", "cherry", "orange", "scatter", "orange", "seven", "lemon", "plum", "bar", "cherry", "seven", "bar", "lemon", "wild", "lemon", "plum", "bell", "cherry", "lemon", "orange", "plum", "wild", "cherry", "cherry"],
    ["cherry", "cherry", "bar", "orange", "bell", "orange", "lemon", "plum", "orange", "bell", "plum", "bell", "lemon", "cherry", "plum", "bar", "bell", "lemon", "lemon", "cherry", "seven", "cherry", "lemon", "bar", "lemon", "cherry", "plum", "scatter", "wild", "seven", "orange", "cherry", "orange"],
    ["bar", "plum", "orange", "plum", "lemon", "orange", "lemon", "seven", "cherry", "bell", "wild", "bell", "orange", "bar", "lemon", "seven", "lemon", "cherry", "bar", "cherry", "scatter", "lemon", "cherry", "bell", "plum", "orange", "plum", "wild", "cherry", "bell", "cherry", "orange", "lemon"],
    ["cherry", "plum", "scatter", "plum", "orange", "orange", "cherry", "bar", "seven", "bar", "wild", "cherry", "cherry", "orange", "lemon", "cherry", "lemon", "lemon", "cherry", "lemon", "bell", "bell", "bell", "orange", "orange", "lemon", "cherry", "plum", "lemon", "bar", "plum", "lemon", "cherry"],
]


def build_all_strips(num_reels: int = 5) -> list[list[str]]:
    """Return the fixed certified reelset (fresh copies), cycling if num_reels > 5."""
    return [list(REEL_STRIPS[i % len(REEL_STRIPS)]) for i in range(num_reels)]


def spin_reel(strip: list[str]) -> list[str]:
    """Pick a uniformly random stop and return 3 consecutive symbols."""
    stop = random.randrange(len(strip))
    n = len(strip)
    return [
        strip[stop],
        strip[(stop + 1) % n],
        strip[(stop + 2) % n],
    ]
