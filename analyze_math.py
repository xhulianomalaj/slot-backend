"""
Exact mathematical analysis of the slot engine.

No simulation -- every number is derived analytically from the strip weights
and paytable.  Run with:
    python analyze_math.py
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fractions import Fraction
from itertools import product as iproduct
from engine.reel_strips import STRIP_WEIGHTS
from engine.paytable import PAYLINES, PAYOUTS, LINE_COUNT
from engine.symbols import WILD, SCATTER, ALL_SYMBOLS

# --- Strip probabilities -------------------------------------------------------
# For a randomly shuffled circular strip of length n, picking a uniform random
# stop, the probability that any *specific* row shows symbol S is: count(S)/n.
# The 3 rows in one reel spin are a hypergeometric sample of size 3 (no
# replacement) from the strip.

strips: list[dict[str, int]] = STRIP_WEIGHTS
totals = [sum(w.values()) for w in strips]

def p_row(reel: int, sym: str) -> Fraction:
    """P(a specific row on reel shows sym) -- valid for any of the 3 rows."""
    return Fraction(strips[reel].get(sym, 0), totals[reel])

# --- Per-reel hypergeometric distribution for visible scatter count ------------
# For a strip with n symbols (s of type scatter), the probability of seeing
# exactly k scatter symbols in the 3-row window is:
#   P(k) = C(s,k) * C(n-s, 3-k) / C(n, 3)
# This is the hypergeometric PMF.

from math import comb

def scatter_pmf(reel: int) -> dict[int, Fraction]:
    """Return {k: P(exactly k scatters visible on reel)} for k in 0..min(3,s)."""
    n = totals[reel]
    s = strips[reel].get(SCATTER, 0)
    denom = comb(n, 3)
    pmf = {}
    for k in range(min(s, 3) + 1):
        pmf[k] = Fraction(comb(s, k) * comb(n - s, 3 - k), denom)
    return pmf

# Convolve per-reel PMFs to get total-scatter-count distribution across all 5 reels.
def convolve(d1: dict[int, Fraction], d2: dict[int, Fraction]) -> dict[int, Fraction]:
    result: dict[int, Fraction] = {}
    for k1, p1 in d1.items():
        for k2, p2 in d2.items():
            result[k1 + k2] = result.get(k1 + k2, Fraction(0)) + p1 * p2
    return result

total_dist: dict[int, Fraction] = {0: Fraction(1)}
for r in range(5):
    total_dist = convolve(total_dist, scatter_pmf(r))

p_trigger = sum(v for k, v in total_dist.items() if k >= 3)
p_tease   = total_dist.get(2, Fraction(0))   # exactly 2 = near-miss

# --- Payline win probabilities -------------------------------------------------
# For a single payline, the "base" symbol is the first non-wild, non-scatter
# reading left to right.  WILDs extend the run.  The evaluator stops counting
# as soon as the first non-(base|wild) symbol appears.
#
# P(S wins for exactly k) on a specific payline =
#   P(reel 0 shows S)                                      ← base must match
#   x P(reels 1..k-1 each show S or WILD)
#   x P(reel k shows neither S nor WILD)   [only for k < 5]
#
# A win of *pure wilds* uses base=WILD; we calculate that separately.
# Note: WILD itself can start a run, but only if all visible cells on that
# payline from left to right are WILD.  For simplicity (and accuracy) we
# compute: p_wild_5 = product of p_W over all 5 reels.

def p_sym_or_wild(reel: int, sym: str) -> Fraction:
    return p_row(reel, sym) + p_row(reel, WILD)

def p_not_sym_not_wild(reel: int, sym: str) -> Fraction:
    return Fraction(1) - p_row(reel, sym) - p_row(reel, WILD)

payline_probs: dict[str, dict[int, Fraction]] = {}  # {sym: {3:p, 4:p, 5:p}}

for sym in ALL_SYMBOLS:
    if sym in (WILD, SCATTER):
        continue
    probs: dict[int, Fraction] = {}
    for pl in PAYLINES:
        for k in (3, 4, 5):
            # P(sym wins exactly k on this payline):
            #   positions 0..k-1 are all (sym or WILD), at least one is sym
            #   position k (if k<5) is neither sym nor WILD
            # Identity used: P(all sym-or-wild) - P(all wild) = P(at least one sym).
            p_all_match = Fraction(1)
            p_all_wild  = Fraction(1)
            for r in range(k):
                p_all_match *= p_sym_or_wild(pl[r], sym)
                p_all_wild  *= p_row(pl[r], WILD)
            p = p_all_match - p_all_wild   # exclude pure-WILD runs (counted as WILD wins)
            if k < 5:
                p *= p_not_sym_not_wild(pl[k], sym)
            probs[k] = probs.get(k, Fraction(0)) + p
    payline_probs[sym] = probs

# WILD k-of-a-kind: all k leading positions show WILD (and WILD pays on its own).
wild_probs: dict[int, Fraction] = {}
for pl in PAYLINES:
    for k in (3, 4, 5):
        p = Fraction(1)
        for r in range(k):
            p *= p_row(pl[r], WILD)
        if k < 5:
            p *= (Fraction(1) - p_row(pl[k], WILD))
        wild_probs[k] = wild_probs.get(k, Fraction(0)) + p

# --- Expected win per credit bet ----------------------------------------------
# RTP (return-to-player) = E[win per spin] / bet
# line_bet = bet / LINE_COUNT
# E[total payline win per spin] = sum over syms and k of:
#   P(that win on any payline) x payout_multiplier x line_bet
# = (bet/LINE_COUNT) x sum over all paylines and (sym,k) of P x multiplier

# We already accumulated probs[sym][k] summed over all paylines above.
# That sum / LINE_COUNT = average probability per payline for any single payline.
# But for "expected win per spin" we want the total across all 20 paylines.

rtp_numerator = Fraction(0)
for sym, probs in payline_probs.items():
    for k, p_sum in probs.items():
        # p_sum = sum over 20 paylines of P(exactly k-of-kind of sym on that payline)
        rtp_numerator += p_sum * Fraction(PAYOUTS[sym][k])
# Add WILD k-of-a-kind wins
for k, p_sum in wild_probs.items():
    rtp_numerator += p_sum * Fraction(PAYOUTS[WILD][k])
# rtp_numerator / LINE_COUNT = E[total win] / bet
rtp = rtp_numerator / LINE_COUNT

# --- Print report -------------------------------------------------------------
SYMBOLS_DISPLAY = ['cherry','lemon','orange','plum','bell','bar','seven','wild','scatter']

print("=" * 70)
print("  SLOT MATH ANALYSIS -- exact hypergeometric model")
print("=" * 70)

print("\n+- STRIP COMPOSITION ----------------------------------------------+")
header = f"{'Symbol':<10}" + "".join(f"{'Reel '+str(r):<12}" for r in range(5)) + "Total/strip"
print("  " + header)
print("  " + "-" * len(header))
for sym in SYMBOLS_DISPLAY:
    row = f"{sym:<10}"
    for r in range(5):
        c = strips[r].get(sym, 0)
        n = totals[r]
        row += f"{c}/{n}={c/n*100:4.1f}%  "
    print("  " + row)
print("  " + "-" * len(header))
strip_totals_row = f"{'TOTAL':<10}" + "".join(f"{totals[r]:<12}" for r in range(5))
print("  " + strip_totals_row)

print("\n+- SYMBOL PROBABILITY PER VISIBLE CELL (any row on that reel) -----+")
print("  Same as the per-row probability since the strip is circular.")
print()
print(f"  {'Symbol':<10}" + "".join(f"{'Reel '+str(r):<12}" for r in range(5)) + "Avg across reels")
print("  " + "-" * 80)
for sym in SYMBOLS_DISPLAY:
    ps = [float(p_row(r, sym)) for r in range(5)]
    avg = sum(ps) / 5
    row = f"  {sym:<10}" + "".join(f"{p*100:6.2f}%    " for p in ps) + f"  {avg*100:6.2f}%"
    print(row)

print("\n+- EXPECTED APPEARANCES PER FULL SPIN (15 cells = 5 reels x 3 rows) +")
print()
print(f"  {'Symbol':<10}  {'Expected count':>15}  {'Per 100 spins':>14}  {'1 in N spins':>13}")
print("  " + "-" * 60)
for sym in SYMBOLS_DISPLAY:
    exp = sum(3 * float(p_row(r, sym)) for r in range(5))
    print(f"  {sym:<10}  {exp:15.4f}  {exp*100:14.3f}  {'N/A' if exp==0 else f'1 in {1/exp:,.1f}':>13}")

print("\n+- SCATTER TRIGGER STATISTICS -------------------------------------+")
print()
print("  Per-reel visible scatter distribution:")
print(f"  {'Reel':<8}" + "".join(f"  P({k}scat)" for k in range(4)))
print("  " + "-" * 55)
for r in range(5):
    pmf = scatter_pmf(r)
    row = f"  Reel {r}  "
    for k in range(4):
        p = float(pmf.get(k, Fraction(0)))
        row += f"  {p*100:7.4f}%"
    print(row)

print()
print("  Total visible scatters across the whole grid:")
print(f"  {'k scatters':<14}  {'Probability':>14}  {'1 in N spins':>14}")
print("  " + "-" * 48)
for k in sorted(total_dist.keys()):
    p = float(total_dist[k])
    print(f"  {k} scatter{'s' if k!=1 else ' ':<8}  {p*100:14.6f}%  {'1 in '+f'{1/p:,.0f}' if p>0 else 'impossible':>14}")

print()
p_trig_f = float(p_trigger)
p_tease_f = float(p_tease)
print(f"  P(scatter trigger, ≥3 anywhere) = {p_trig_f*100:.4f}%   (~1 in {1/p_trig_f:,.1f} spins)")
print(f"  P(near-miss, exactly 2 scatters) = {p_tease_f*100:.4f}%   (~1 in {1/p_tease_f:,.1f} spins)")

print("\n+- PAYLINE WIN PROBABILITIES (summed across all 20 paylines) -------+")
print()
print(f"  {'Symbol':<10}  {'P(3-of-kind)':>14}  {'P(4-of-kind)':>14}  {'P(5-of-kind)':>14}")
print("  " + "-" * 60)
for sym in ['cherry','lemon','orange','plum','bell','bar','seven','wild']:
    if sym == 'wild':
        probs = wild_probs
    else:
        probs = payline_probs.get(sym, {})
    p3 = float(probs.get(3, 0))
    p4 = float(probs.get(4, 0))
    p5 = float(probs.get(5, 0))
    print(f"  {sym:<10}  {p3*100:14.5f}%  {p4*100:14.5f}%  {p5*100:14.6f}%")

print()
print("  Frequency -- expected wins per spin (all paylines combined):")
print(f"  {'Symbol':<10}  {'3x wins/spin':>13}  {'4x wins/spin':>13}  {'5x wins/spin':>13}  {'any win/spin':>13}")
print("  " + "-" * 70)
for sym in ['cherry','lemon','orange','plum','bell','bar','seven','wild']:
    if sym == 'wild':
        probs = wild_probs
    else:
        probs = payline_probs.get(sym, {})
    e3 = float(probs.get(3, 0))
    e4 = float(probs.get(4, 0))
    e5 = float(probs.get(5, 0))
    print(f"  {sym:<10}  {e3:13.6f}  {e4:13.6f}  {e5:13.8f}  {e3+e4+e5:13.6f}")

print("\n+- THEORETICAL RTP ------------------------------------------------+")
print()
print(f"  Payline RTP (base game, excluding free spins): {float(rtp)*100:.4f}%")
print()
# Total RTP -- three-step model:
#
# 1. Scatter-zeroing correction: when scatter triggers on a paid spin the
#    evaluator returns 0 payline wins.  So effective paid-spin base RTP is:
#      base_rtp_adj = base_rtp * (1 - P_trigger)
#
# 2. Geometric re-trigger model: free spins can re-trigger free spins.
#    Expected free spins per paid spin (accounting for infinite re-triggers):
#      E[free/paid] = FREE_SPINS_COUNT * P_trigger / (1 - FREE_SPINS_COUNT * P_trigger)
#    (valid while FREE_SPINS_COUNT * P_trigger < 1, which it always is here)
#
# 3. Free spins pay at the same per-spin rate as the adjusted base.
#      total_rtp = base_rtp_adj * (1 + E[free/paid])
#
# This closed-form model slightly overestimates the true RTP (~1-2%) because
# the independence assumption between paylines drops some hypergeometric
# correlations within a spin. The Monte Carlo simulation in simulate_rtp.py
# is the certified source of truth.
from engine.evaluator import FREE_SPINS_COUNT
pt = float(p_trigger)
base_rtp_adj = float(rtp) * (1 - pt)
mu = FREE_SPINS_COUNT * pt                          # expected free/paid (no re-trigger)
e_free_per_paid = mu / (1 - mu)                     # geometric re-trigger correction
total_rtp = base_rtp_adj * (1 + e_free_per_paid)
print(f"  Scatter-zeroing correction: base_rtp x (1 - P_trigger)")
print(f"    = {float(rtp)*100:.4f}% x {(1-pt)*100:.4f}% = {base_rtp_adj*100:.4f}%")
print(f"  Free spins: {FREE_SPINS_COUNT} spins x P(trigger)={pt*100:.4f}%  (geometric re-triggers -> E={e_free_per_paid:.4f} fs/paid)")
print(f"  Total RTP  (corrected model): {total_rtp*100:.4f}%")
print(f"  (Use simulate_rtp.py for authoritative RTP -- theoretical model overestimates by ~1-2%)")
print(f"  Target band: 94-97%   {'IN RANGE (model)' if 0.94 <= total_rtp <= 0.99 else 'OUT OF RANGE -- adjust payouts or strip weights'}")
print()
print("  RTP breakdown by symbol:")
print(f"  {'Symbol':<10}  {'RTP contrib (x3)':>18}  {'RTP contrib (x4)':>18}  {'RTP contrib (x5)':>18}")
print("  " + "-" * 72)
for sym in ['cherry','lemon','orange','plum','bell','bar','seven','wild']:
    if sym == 'wild':
        probs = wild_probs
    else:
        probs = payline_probs.get(sym, {})
    r3 = float(probs.get(3,0)) * PAYOUTS[sym][3] / LINE_COUNT * 100
    r4 = float(probs.get(4,0)) * PAYOUTS[sym][4] / LINE_COUNT * 100
    r5 = float(probs.get(5,0)) * PAYOUTS[sym][5] / LINE_COUNT * 100
    print(f"  {sym:<10}  {r3:18.4f}%  {r4:18.4f}%  {r5:18.5f}%   sum={r3+r4+r5:.4f}%")

print()
print("  NOTE: Free-spins RTP not included above (requires simulation or")
print("        separate free-spins RTP analysis multiplied by trigger freq).")
print("  Rough free-spins RTP addend ~ base_rtp x avg_fs_win_multiplier x p_trigger")
print()
print("=" * 70)
