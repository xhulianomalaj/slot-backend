from engine.paytable import LINE_COUNT, PAYLINES, PAYOUTS
from engine.reel_strips import spin_reel
from engine.symbols import SCATTER, WILD

# Free-spins awarded per scatter count (3→10, 4→15, 5→20).
FREE_SPINS_MAP: dict[int, int] = {3: 10, 4: 15, 5: 20}


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


# ─── Scatter evaluation ───────────────────────────────────────────────────────

def _find_scatter_positions(grid: list[list[str]]) -> list[dict]:
    return [
        {"reel": reel, "row": row}
        for reel, col in enumerate(grid)
        for row, sym in enumerate(col)
        if sym == SCATTER
    ]


def _evaluate_scatter(grid: list[list[str]], total_bet: float) -> dict | None:
    positions = _find_scatter_positions(grid)
    if len(positions) < 3:
        return None

    match_count = min(len(positions), 5)
    multiplier = PAYOUTS.get(SCATTER, {}).get(match_count, 0)
    amount = round(total_bet * multiplier, 2)
    return {
        "lineId": 0,
        "symbolId": SCATTER,
        "matchCount": match_count,
        "amount": amount,
        "positions": positions,
    }


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
        free_spins_awarded  — 10 / 15 / 20 for 3 / 4 / 5 scatters, else 0
    """
    line_bet = round(bet / LINE_COUNT, 6)
    winlines: list[dict] = []

    for i, payline in enumerate(PAYLINES):
        wl = _evaluate_payline(grid, payline, line_bet, i + 1)
        if wl:
            winlines.append(wl)

    scatter_wl = _evaluate_scatter(grid, bet)
    if scatter_wl:
        winlines.append(scatter_wl)

    scatter_positions = _find_scatter_positions(grid)
    scatter_count = len(scatter_positions)

    teasing_reels: list[int] = []
    if scatter_count == 2:
        scatter_reels = {p["reel"] for p in scatter_positions}
        teasing_reels = [r for r in range(5) if r not in scatter_reels]

    free_spins_awarded = FREE_SPINS_MAP.get(min(scatter_count, 5), 0) if scatter_count >= 3 else 0
    total_win = round(sum(wl["amount"] for wl in winlines), 2)

    return winlines, total_win, teasing_reels, free_spins_awarded
