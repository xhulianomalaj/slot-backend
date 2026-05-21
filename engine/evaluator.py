from engine.paytable import LINE_COUNT, PAYLINES, PAYOUTS
from engine.reel_strips import spin_reel
from engine.symbols import CHERRY, SCATTER, WILD

# Scatters only award free spins — no monetary payout.
# Exactly 3 scatters trigger 10 free spins; no more than 3 appear on the grid.
FREE_SPINS_COUNT = 10
SCATTER_TRIGGER = 3
# Symbol used to replace any scatter beyond the cap of 3.
_SCATTER_FILL = CHERRY


# ─── Grid ─────────────────────────────────────────────────────────────────────

def build_grid(strips: list[list[str]]) -> list[list[str]]:
    """Spin every reel and return a grid[reel][row] (5 reels × 3 rows)."""
    return [spin_reel(strip) for strip in strips]


# ─── Payline evaluation ───────────────────────────────────────────────────────

def _evaluate_payline(
    grid: list[list[str]],
    payline: tuple[int, int, int, int, int],
    line_bet: float,
    line_id: int,
) -> dict | None:
    symbols = [grid[reel][row] for reel, row in enumerate(payline)]

    # Base symbol = first non-wild, non-scatter reading left-to-right.
    # An all-wild line pays as wild.
    base = next((s for s in symbols if s not in (WILD, SCATTER)), None)
    if base is None:
        base = WILD if symbols[0] == WILD else None
    if base is None:
        return None

    # Count the run from reel 0 — wilds extend the run.
    count = 0
    for s in symbols:
        if s == base or s == WILD:
            count += 1
        else:
            break

    if count < 3:
        return None

    match_count = min(count, 5)
    multiplier = PAYOUTS.get(base, {}).get(match_count)
    if not multiplier:
        return None

    amount = round(line_bet * multiplier, 2)
    positions = [{"reel": r, "row": payline[r]} for r in range(match_count)]
    return {
        "lineId": line_id,
        "symbolId": base,
        "matchCount": match_count,
        "amount": amount,
        "positions": positions,
    }


# ─── Scatter helpers ─────────────────────────────────────────────────────────

def _find_scatter_positions(grid: list[list[str]]) -> list[dict]:
    return [
        {"reel": reel, "row": row}
        for reel, col in enumerate(grid)
        for row, sym in enumerate(col)
        if sym == SCATTER
    ]


def _cap_scatters(grid: list[list[str]]) -> list[dict]:
    """Ensure at most SCATTER_TRIGGER scatters appear in the grid.

    Any scatter beyond the cap is replaced in-place with _SCATTER_FILL so the
    response never contains 4 or 5 scatter symbols.
    Returns the (possibly trimmed) list of scatter positions.
    """
    positions = _find_scatter_positions(grid)
    for extra in positions[SCATTER_TRIGGER:]:
        grid[extra["reel"]][extra["row"]] = _SCATTER_FILL
    return positions[:SCATTER_TRIGGER]


# ─── Full round evaluation ────────────────────────────────────────────────────

def evaluate_spin(
    grid: list[list[str]],
    bet: float,
) -> tuple[list[dict], float, list[int], int]:
    """
    Evaluate all paylines and scatter for a completed grid.

    Returns:
        winlines            — list of Winline dicts ready for the API response
        total_win           — sum of all winline amounts (rounded to 2 dp)
        teasing_reels       — reel indices to animate (exactly 2 scatters landed)
        free_spins_awarded  — FREE_SPINS_COUNT when 3 scatters land, else 0

    Rules:
        • Scatters award free spins only — no monetary payout.
        • At most SCATTER_TRIGGER (3) scatters appear; extras are capped.
        • When the scatter trigger fires, all payline wins are discarded.
    """
    # Cap the grid to at most 3 scatters and get their positions.
    scatter_positions = _cap_scatters(grid)
    scatter_count = len(scatter_positions)

    # Scatter trigger: award free spins and discard all payline wins.
    # Return a zero-amount scatter winline so the frontend can animate the
    # scatter symbols (glow highlight) without showing any monetary value.
    if scatter_count >= SCATTER_TRIGGER:
        scatter_wl = {
            "lineId": 0,
            "symbolId": SCATTER,
            "matchCount": scatter_count,
            "amount": 0.0,
            "positions": scatter_positions,
        }
        return [scatter_wl], 0.0, [], FREE_SPINS_COUNT

    # No trigger — evaluate paylines normally.
    line_bet = round(bet / LINE_COUNT, 6)
    winlines: list[dict] = []

    for i, payline in enumerate(PAYLINES):
        wl = _evaluate_payline(grid, payline, line_bet, i + 1)
        if wl:
            winlines.append(wl)

    # Teasing reels: exactly 2 scatters landed (near-miss anticipation).
    teasing_reels: list[int] = []
    if scatter_count == 2:
        scatter_reels = {p["reel"] for p in scatter_positions}
        teasing_reels = [r for r in range(5) if r not in scatter_reels]

    total_win = round(sum(wl["amount"] for wl in winlines), 2)
    return winlines, total_win, teasing_reels, 0
