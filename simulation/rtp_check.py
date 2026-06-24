"""
RTP simulation — run N spins and verify the paytable produces the expected RTP.

Usage:
    python -m simulation.rtp_check
    python -m simulation.rtp_check --spins 1000000 --bet 1.0 --target 0.97
"""
import argparse
import sys

from engine.evaluator import build_grid, evaluate_spin
from engine.reel_strips import build_all_strips

TARGET_RTP = 0.97
TOLERANCE  = 0.005   # ±0.5%
SPINS      = 10_000_000
BET        = 1.0
REELS      = 5


def run_simulation(spins: int, bet: float, target_rtp: float, tolerance: float) -> bool:
    strips = build_all_strips(REELS)
    total_wagered = 0.0
    total_won     = 0.0
    hit_count     = 0
    bonus_triggers = 0

    print(f"Running {spins:,} spins at bet={bet} …\n")

    for i in range(spins):
        grid = build_grid(strips)
        _, total_win, _, free_spins = evaluate_spin(grid, bet)

        total_wagered += bet
        total_won     += total_win

        if total_win > 0:
            hit_count += 1
        if free_spins > 0:
            bonus_triggers += 1

        if (i + 1) % 1_000_000 == 0:
            interim_rtp = total_won / total_wagered
            print(f"  {i + 1:>10,} spins — RTP so far: {interim_rtp:.4%}")

    rtp        = total_won / total_wagered
    hit_freq   = hit_count / spins
    bonus_freq = bonus_triggers / spins

    print(f"\n{'─' * 44}")
    print(f"  Final RTP       : {rtp:.4%}  (target {target_rtp:.0%} ± {tolerance:.1%})")
    print(f"  Hit frequency   : {hit_freq:.4%}  (1 in {1 / hit_freq:.1f} spins)")
    print(f"  Bonus triggers  : {bonus_freq:.4%}  ({bonus_triggers:,} / {spins:,})")
    print(f"{'─' * 44}")

    passed = abs(rtp - target_rtp) <= tolerance
    print(f"  {'PASS ✓' if passed else 'FAIL ✗'}  RTP {rtp:.4%} is {'within' if passed else 'outside'} target range")
    return passed


def main() -> None:
    parser = argparse.ArgumentParser(description="RTP simulation for slot engine")
    parser.add_argument("--spins",  type=int,   default=SPINS,      help="Number of spins")
    parser.add_argument("--bet",    type=float, default=BET,        help="Bet per spin")
    parser.add_argument("--target", type=float, default=TARGET_RTP, help="Target RTP (0–1)")
    parser.add_argument("--tol",    type=float, default=TOLERANCE,  help="Tolerance (0–1)")
    args = parser.parse_args()

    passed = run_simulation(args.spins, args.bet, args.target, args.tol)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
