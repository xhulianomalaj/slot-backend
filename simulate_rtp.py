"""
Monte Carlo RTP verification — slot-backend/simulate_rtp.py

Runs N paid spins using the REAL engine (reel strips + evaluator + paytable)
and reports observed vs theoretical statistics.

Free spins are handled exactly as the frontend does: when a scatter trigger
lands, FREE_SPINS_COUNT free spins run, and re-triggers accumulate normally.

Usage (run from slot-backend/ with venv active):
    python simulate_rtp.py              # 500 000 spins (default)
    python simulate_rtp.py 1000000      # 1 million
    python simulate_rtp.py 100000       # quick sanity-check (~10 s)
"""

import math
import sys
import time
from collections import defaultdict

# Force UTF-8 stdout so the Unicode box-drawing characters in the report
# render correctly under Windows cp1252 consoles.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from engine.evaluator import FREE_SPINS_COUNT, build_grid, evaluate_spin
from engine.paytable import LINE_COUNT, PAYOUTS
from engine.reel_strips import STRIP_WEIGHTS, build_all_strips
from engine.symbols import SCATTER

# ── Configuration ──────────────────────────────────────────────────────────────
BET     = 1.0   # RTP is bet-independent; 1.0 keeps numbers readable
COLUMNS = 5

# ── Theoretical targets ────────────────────────────────────────────────────────
# Derived analytically from strip weights + paytable (see analyze_math.py, which
# computes the base payline RTP by exact enumeration = 90.45% unzeroed). The paid
# base measured here is a touch lower because >=3 scatters zero that spin's
# payline wins (a ~0.2% effect). The simulation is the authoritative number.
THEO_BASE_RTP     = 0.9024    # ~90.2 % — paid paylines only, after scatter-zeroing
THEO_SCATTER_RATE = 0.006526  # ~1 in 153 paid spins (exact, hypergeometric)

# Two versions of total-RTP theory:
#   APPROX — analyze_math.py formula: base × (1 + f × p)     — ignores re-triggers
#   EXACT  — geometric series:        base / (1 − f × p)      — counts re-triggers
_fp = FREE_SPINS_COUNT * THEO_SCATTER_RATE
THEO_TOTAL_RTP_APPROX = THEO_BASE_RTP * (1 + _fp)          # 95.97 %
THEO_TOTAL_RTP_EXACT  = THEO_BASE_RTP / (1 - _fp)          # 96.39 %

# Industry volatility classification (std-dev of per-paid-spin win / bet):
#   < 3.5   Low            (HF > 30%, max win typically <  500x)
#   3.5–6   Medium         (HF 25-35%, max win typically <2000x)
#   6–9     High           (HF 20-30%, max win typically <5000x)
#   > 9     Very High      (HF < 25%, max win typically 5000x+)
def _volatility_class(std_dev: float) -> str:
    if std_dev < 3.5:  return "LOW"
    if std_dev < 6.0:  return "MEDIUM"
    if std_dev < 9.0:  return "HIGH"
    return "VERY HIGH"


# ── Maximum theoretical win (single spin) ─────────────────────────────────────
# All 15 cells = WILD → every payline matches WILD 5x → 20 × WILD_5x × line_bet
# = 20 × 2580 × (bet/20) = 2580 × bet.  Per the engine's _cap_scatters, this is
# only achievable if no scatter lands (otherwise scatter trigger zeros wins).
def _max_single_spin_win() -> float:
    return LINE_COUNT * PAYOUTS["wild"][5] / LINE_COUNT   # = WILD_5x multiplier


# ── Risk-of-ruin scenarios ────────────────────────────────────────────────────
# Each tuple = (starting_bankroll_in_bet_units, max_spins_before_giving_up).
# A player who exhausts their bankroll = ruined; otherwise they "survive".
RUIN_SCENARIOS = [
    (50,    100),    #  $50 budget,  100 spins
    (100,   200),    #  $100 budget, 200 spins
    (200,   500),    #  $200 budget, 500 spins
    (500,  1000),    #  $500 budget, 1000 spins
    (1000, 2000),    # $1000 budget, 2000 spins
]
RUIN_TRIALS = 2000   # number of independent player trials per scenario


def _ruin_probability(
    strips: list[list[str]],
    bankroll_units: int,
    max_spins: int,
) -> tuple[float, float]:
    """Run RUIN_TRIALS independent players. Each starts with bankroll_units × BET
    and bets BET per spin until bankrupt or max_spins reached.
    Returns (probability_of_ruin, average_spins_per_trial).
    """
    ruined  = 0
    spins_taken = 0
    for _ in range(RUIN_TRIALS):
        bal    = bankroll_units * BET
        played = 0
        while bal >= BET and played < max_spins:
            bal -= BET
            grid = build_grid(strips)
            winlines, win, _, fs = evaluate_spin(grid, BET)
            bal += win
            played += 1
            if fs > 0:
                # Free spins don't cost money but do contribute to balance
                pending = fs
                while pending > 0 and played < max_spins:
                    pending -= 1
                    grid = build_grid(strips)
                    _, fwin, _, frs = evaluate_spin(grid, BET)
                    bal += fwin
                    if frs > 0:
                        pending += frs
        if bal < BET:
            ruined += 1
        spins_taken += played
    return ruined / RUIN_TRIALS, spins_taken / RUIN_TRIALS



# ── Free-spin runner ───────────────────────────────────────────────────────────

def _run_free_spins(
    strips: list[list[str]],
    sym_wins: dict,
) -> tuple[float, int, int]:
    """Execute the free-spin feature, allowing re-triggers.

    Updates sym_wins in-place with every winning combination hit.
    Returns (total_win, total_free_spins_played, retrigger_count).
    """
    pending      = FREE_SPINS_COUNT
    total_win    = 0.0
    spins_played = 0
    retriggers   = 0

    while pending > 0:
        pending -= 1
        spins_played += 1
        grid = build_grid(strips)
        winlines, win, _, fs = evaluate_spin(grid, BET)
        total_win += win
        for wl in winlines:
            if wl["symbolId"] != SCATTER:
                sym_wins[wl["symbolId"]][wl["matchCount"]] += 1
        if fs > 0:
            pending    += fs
            retriggers += 1

    return total_win, spins_played, retriggers


# ── Main simulation ────────────────────────────────────────────────────────────

def simulate(n_paid: int) -> None:
    print(f"\nBuilding reel strips for {n_paid:,} paid spins …")
    strips = build_all_strips(COLUMNS)

    wagered           = 0.0
    won_paid          = 0.0
    won_free          = 0.0
    scatter_triggers  = 0
    retriggers        = 0
    free_spins_total  = 0
    hit_paid          = 0     # paid spins with any monetary win > 0

    # Symbol win counts (both paid and free spins):  {sym: {3: n, 4: n, 5: n}}
    sym_wins: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))

    # Win-size distribution buckets (in units of bet, including free-spin sequence)
    win_buckets = {
        "0x           (loss)":          0,
        "0 < x <= 1   (small)":         0,
        "1 < x <= 5   (modest)":        0,
        "5 < x <= 20  (good)":          0,
        "20 < x <= 100 (big)":          0,
        "100 < x <= 500 (huge)":        0,
        "x > 500      (mega)":          0,
    }
    max_spin_win = 0.0   # largest single (paid + its free spins) total

    # Welford online variance for per-paid-spin total win (paid + free contribution)
    _count = 0
    _mean  = 0.0
    _M2    = 0.0

    t0 = time.perf_counter()

    for i in range(n_paid):
        grid = build_grid(strips)
        winlines, win, _, fs = evaluate_spin(grid, BET)

        wagered    += BET
        won_paid   += win
        spin_total  = win

        if win > 0:
            hit_paid += 1
        for wl in winlines:
            if wl["symbolId"] != SCATTER:
                sym_wins[wl["symbolId"]][wl["matchCount"]] += 1

        if fs > 0:
            scatter_triggers += 1
            fs_win, fs_played, rtrig = _run_free_spins(strips, sym_wins)
            won_free         += fs_win
            free_spins_total += fs_played
            retriggers       += rtrig
            spin_total       += fs_win

        # Welford online variance
        _count += 1
        delta   = spin_total - _mean
        _mean  += delta / _count
        _M2    += delta * (spin_total - _mean)

        # Bucket and track max
        ratio = spin_total / BET
        if   ratio == 0:           win_buckets["0x           (loss)"] += 1
        elif ratio <= 1:           win_buckets["0 < x <= 1   (small)"] += 1
        elif ratio <= 5:           win_buckets["1 < x <= 5   (modest)"] += 1
        elif ratio <= 20:          win_buckets["5 < x <= 20  (good)"] += 1
        elif ratio <= 100:         win_buckets["20 < x <= 100 (big)"] += 1
        elif ratio <= 500:         win_buckets["100 < x <= 500 (huge)"] += 1
        else:                      win_buckets["x > 500      (mega)"] += 1
        if spin_total > max_spin_win:
            max_spin_win = spin_total

        # Progress update every 100 000 spins
        if (i + 1) % 100_000 == 0:
            pct     = (i + 1) / n_paid * 100
            obs_rtp = (won_paid + won_free) / wagered
            rate    = (i + 1) / (time.perf_counter() - t0)
            print(f"  {pct:5.1f}%  spins={i+1:>9,}  "
                  f"obs_total_RTP={obs_rtp:.4f}  ({rate:,.0f}/s)", flush=True)

    elapsed  = time.perf_counter() - t0
    total_won = won_paid + won_free

    base_rtp     = won_paid  / wagered
    total_rtp    = total_won / wagered
    hit_freq     = hit_paid  / n_paid
    scatter_rate = scatter_triggers / n_paid

    variance = _M2 / _count if _count > 1 else 0.0
    std_dev  = math.sqrt(variance)
    ci_half  = 1.96 * std_dev / (math.sqrt(n_paid) * BET)   # 95 % CI

    # ── Print report ───────────────────────────────────────────────────────────
    W = 72
    print()
    print("=" * W)
    print("  MONTE CARLO RTP VERIFICATION")
    print(f"  {n_paid:,} paid  +  {free_spins_total:,} free spins  "
          f"|  {elapsed:.1f} s  @  {n_paid/elapsed:,.0f} paid/s")
    print("=" * W)

    def _row(label: str, obs: float, theo: float) -> None:
        diff = obs - theo
        flag = "OK" if abs(diff) < 0.01 else "!!"
        print(f"  {label:<38}  {obs:.6f}    {theo:.6f}    {diff:+.6f}  {flag}")

    print(f"\n  {'Metric':<38}  {'Observed':>10}  {'Theoretical':>12}  {'Diff':>10}  OK?")
    print("  " + "-" * (W - 2))
    _row("Base RTP  (paid wins only)",    base_rtp,     THEO_BASE_RTP)
    _row("Total RTP — no-retrigger est.", total_rtp,    THEO_TOTAL_RTP_APPROX)
    _row("Total RTP — with-retrigger est", total_rtp,   THEO_TOTAL_RTP_EXACT)
    _row("Scatter trigger rate",          scatter_rate, THEO_SCATTER_RATE)

    print()
    print(f"  Hit frequency (paid wins >= 0.01)  {hit_freq:.4f}  "
          f"({hit_freq*100:.2f}% of paid spins)")
    print(f"  Scatter triggers                  {scatter_triggers:,}  "
          f"(re-triggers: {retriggers:,})")
    print(f"  Free spins played                 {free_spins_total:,}")

    print()
    print(f"  Volatility  std-dev / BET          {std_dev:.4f}")
    print(f"  95% CI for total RTP (this run)    ± {ci_half:.4f}  "
          f"({ci_half*100:.2f}%)")

    # How many spins are required for a given accuracy
    needed = {
        "±5%":   int((1.96 * std_dev / (0.05 * BET)) ** 2),
        "±1%":   int((1.96 * std_dev / (0.01 * BET)) ** 2),
        "±0.1%": int((1.96 * std_dev / (0.001 * BET)) ** 2),
    }
    print()
    print("  ─── Spins needed for reliable RTP estimation ───")
    for label, n_req in needed.items():
        print(f"  {label} accuracy  →  {n_req:>12,} spins")
    browser_100_ci = 1.96 * std_dev / math.sqrt(100) * 100
    print(f"\n  Implication: 100 browser spins has a ±{browser_100_ci:.1f}% CI —")
    print(f"  far too noisy to verify 96% RTP.  Use this script instead.")

    # ── Symbol win breakdown ───────────────────────────────────────────────────
    print()
    print(f"  ─── Symbol win breakdown (paid + free spins combined) ───")
    print(f"  {'Symbol':<10}  {'3x':>10}  {'4x':>10}  {'5x':>10}  "
          f"{'Won':>12}  {'RTP contrib':>11}")
    print("  " + "-" * 68)

    sym_order = ["cherry", "lemon", "orange", "plum", "bell", "bar", "seven", "wild"]
    for sym in sym_order:
        counts  = sym_wins.get(sym, {})
        pay     = PAYOUTS.get(sym, {})
        line_bet = BET / LINE_COUNT
        sym_won = sum(counts.get(k, 0) * pay.get(k, 0) * line_bet for k in (3, 4, 5))
        contrib = sym_won / wagered
        c3, c4, c5 = counts.get(3, 0), counts.get(4, 0), counts.get(5, 0)
        print(f"  {sym:<10}  {c3:>10,}  {c4:>10,}  {c5:>10,}  "
              f"{sym_won:>12.2f}  {contrib:>10.4f}")

    print()
    print(f"  Total wagered : {wagered:>14,.2f}")
    print(f"  Won (paid)    : {won_paid:>14,.2f}   base RTP = {base_rtp*100:.3f}%")
    print(f"  Won (free)    : {won_free:>14,.2f}")
    print(f"  Won (total)   : {total_won:>14,.2f}   total RTP = {total_rtp*100:.3f}%")
    print("=" * W)

    # ── Volatility classification ──────────────────────────────────────────────
    vol_class   = _volatility_class(std_dev)
    house_edge  = (1.0 - total_rtp) * 100
    print()
    print(f"  ─── Volatility & house edge ───")
    print(f"  Volatility index (std-dev / bet)    : {std_dev:.4f}")
    print(f"  Volatility classification           : {vol_class}")
    print(f"  House edge (1 - RTP)                : {house_edge:.3f}%")
    print(f"  Hit frequency                       : {hit_freq*100:.2f}%")

    # ── Win-size distribution ──────────────────────────────────────────────────
    print()
    print(f"  ─── Win-size distribution (per paid spin, including free wins) ───")
    print(f"  {'Win range (x bet)':<26}  {'Count':>10}  {'% of paid':>10}  {'1 in N':>10}")
    print("  " + "-" * 64)
    for label, count in win_buckets.items():
        pct = count / n_paid * 100
        one_in = ("--" if count == 0 else f"{n_paid/count:,.1f}")
        print(f"  {label:<26}  {count:>10,}  {pct:>9.3f}%  {one_in:>10}")

    # ── Maximum theoretical / observed win ─────────────────────────────────────
    # The "all 15 cells WILD" grid (which would pay 20 lines × WILD 5x = 2580x bet)
    # is IMPOSSIBLE with these strips: reels 0/2/4 carry a single WILD each, so a
    # reel's 3-cell window can never show more than one wild — a reel (let alone the
    # whole grid) can never be filled with wilds.
    per_line_max = PAYOUTS["wild"][5] / LINE_COUNT   # one 5-wild payline, in × bet
    print()
    print(f"  ─── Maximum win analysis ───")
    print(f"  All-WILD grid (would be 2580x)  : IMPOSSIBLE  "
          f"(reels 0/2/4 have 1 wild; a 3-cell window shows <=1 wild)")
    print(f"  Single payline maximum (WILD 5x): {per_line_max:>10.2f}x bet  "
          f"(five wilds on one line — already extremely rare)")
    print(f"  Largest spin observed this run  : {max_spin_win/BET:>10.2f}x bet  "
          f"(a spin can stack several winning lines)")

    # ── Ruin probability (separate quick MC) ───────────────────────────────────
    print()
    print(f"  ─── Player risk-of-ruin (Monte Carlo, {hit_freq:.2f} hit-freq game) ───")
    print(f"  Each row: {RUIN_TRIALS:,} trials, player bets {BET} flat, plays until ")
    print(f"  bankroll = 0 OR limit reached.")
    print(f"  {'Bankroll':>10}  {'Limit':>10}  {'P(ruin)':>10}  {'Avg spins':>12}")
    print("  " + "-" * 50)
    for bankroll_units, max_spins in RUIN_SCENARIOS:
        p_ruin, avg_spins = _ruin_probability(strips, bankroll_units, max_spins)
        print(f"  {bankroll_units:>10,}  {max_spins:>10,}  {p_ruin*100:>9.2f}%  {avg_spins:>12,.0f}")

    # ── Multiplier correction for target RTP ───────────────────────────────────
    target_rtp = 0.96
    scale = target_rtp / total_rtp
    print()
    print(f"  ─── Multiplier correction to reach {target_rtp*100:.0f}% total RTP ───")
    print(f"  Observed total RTP:  {total_rtp*100:.3f}%")
    print(f"  Target  total RTP:   {target_rtp*100:.1f}%")
    print(f"  Scale factor:        {scale:.4f}  (multiply ALL payouts by this)")
    print()
    print(f"  Proposed new multipliers (current × {scale:.4f}, rounded):")
    print(f"  {'Symbol':<10}  {'3x cur':>8} → {'3x new':>6}  "
          f"{'4x cur':>8} → {'4x new':>6}  "
          f"{'5x cur':>8} → {'5x new':>6}")
    print("  " + "-" * 66)
    for sym in sym_order:
        pay = PAYOUTS.get(sym, {})
        m3, m4, m5 = pay.get(3, 0), pay.get(4, 0), pay.get(5, 0)
        n3, n4, n5 = round(m3 * scale), round(m4 * scale), round(m5 * scale)
        print(f"  {sym:<10}  {m3:>8} → {n3:>6}  {m4:>8} → {n4:>6}  {m5:>8} → {n5:>6}")
    print()
    print("  NOTE: Run the simulation again after applying new multipliers to")
    print(f"  verify the observed RTP converges to ~{target_rtp*100:.0f}%.")
    print("=" * W)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500_000
    simulate(n)
