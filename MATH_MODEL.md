# Slot Game Math Model

**Game:** Classic 5-Reel Video Slot
**Document Version:** 1.1
**Engine Reference:** `slot-backend/engine/`
**Verification Method:** Monte Carlo (5,000,000 paid spins) + closed-form analysis

---

## 1. Game Specification

| Parameter            | Value                                            |
| -------------------- | ------------------------------------------------ |
| Reels × visible rows | 5 × 3                                            |
| Stops per reel       | 33 (independent strip per reel)                  |
| Paylines             | 20 (fixed)                                       |
| Bet model            | 1 unit total per spin → `line_bet = bet / 20`    |
| Paying symbols       | 8 (CHERRY, LEMON, ORANGE, PLUM, BELL, BAR, SEVEN, WILD) |
| Special symbols      | SCATTER (1 per reel, fixed)                      |
| WILD substitution    | Yes — substitutes for all paying symbols         |
| Free-spin trigger    | ≥ 3 SCATTER anywhere on the grid                 |
| Free-spin award      | 10 free spins, re-triggerable                    |

The engine source is the single point of truth: both the analytical model
(`analyze_math.py`) and the Monte Carlo simulation (`simulate_rtp.py`) drive the
exact same evaluator (`engine/evaluator.py`) used by the production server.

---

## 2. Reel Strip Composition

Each reel uses a 33-stop strip; one SCATTER per reel is held constant.

| Symbol  | Reel 0 | Reel 1 | Reel 2 | Reel 3 | Reel 4 |
| ------- | -----: | -----: | -----: | -----: | -----: |
| CHERRY  |    7   |    6   |    7   |    6   |    8   |
| LEMON   |    6   |    6   |    6   |    6   |    7   |
| ORANGE  |    5   |    5   |    5   |    5   |    5   |
| PLUM    |    4   |    4   |    4   |    4   |    4   |
| BELL    |    4   |    4   |    4   |    4   |    3   |
| BAR     |    3   |    3   |    3   |    3   |    3   |
| SEVEN   |    2   |    2   |    2   |    2   |    1   |
| WILD    |    1   |    2   |    1   |    2   |    1   |
| SCATTER |    1   |    1   |    1   |    1   |    1   |
| **Σ**   | **33** | **33** | **33** | **33** | **33** |

Reel 4 carries fewer high-paying symbols (SEVEN, BELL) so 5-of-a-kind premium
wins remain rare — the standard volatility-shaping technique. Strips are
re-shuffled (Fisher–Yates) once per session at strip-build time; the symbol
*composition* above is fixed, only the stop *order* varies between sessions.

---

## 3. Paytable

Multipliers are expressed in units of **line bet** (`bet / 20`).

| Symbol | 3-of-a-kind | 4-of-a-kind | 5-of-a-kind |
| ------ | ----------: | ----------: | ----------: |
| WILD   |         103 |         516 |       2,580 |
| SEVEN  |          52 |         218 |       1,032 |
| BAR    |          26 |         103 |         516 |
| BELL   |          17 |          65 |         258 |
| CHERRY |          10 |          44 |         159 |
| PLUM   |           9 |          30 |         103 |
| ORANGE |           5 |          21 |          65 |
| LEMON  |           5 |          16 |          52 |

SCATTER pays no line credits; its only function is to award free spins.

> **Display note:** these multipliers are in *line-bet* units. On a 20-line bet
> the headline figures divide by 20 in *total-bet* terms — e.g. WILD ×5 = 2,580
> line units = **129 × total bet** on one line; SEVEN ×5 = **51.6 × total bet**.

---

## 4. Probability Model

**Single-cell symbol probability** (for reel `r`, payline row `j`):

$$
P(\text{cell}_{r,j} = s) = \frac{w_{r,s}}{33}
$$

where `w_{r,s}` is the strip weight in §2.

**Scatter trigger** (≥ 3 scatter on the visible 5 × 3 grid). Each reel
independently shows the scatter on at least one of three rows with probability
`P(scatter visible on reel r) = 3/33`. Aggregating with the binomial /
hypergeometric expansion across 5 reels:

$$
P(\text{trigger}) \approx 0.6526\% \;\;(\sim 1 \text{ in } 153 \text{ paid spins})
$$

**Free-spin geometric model** (re-triggers). Each free spin independently has
the same trigger probability `p_t`. With `N = 10` free spins per trigger, the
expected number of free spins per paid trigger event is

$$
\mathbb{E}[\text{free spins per trigger}] = \frac{N}{1 - N \cdot p_t} = \frac{10}{1 - 0.0653} \approx 10.70
$$

---

## 5. Return-to-Player (RTP)

### 5.1 Closed-form derivation

The base-game payline RTP `R_b` is computed exactly by enumerating all `9^5`
symbol combinations for a single payline — every line shares the same per-reel
marginals, so all 20 lines have identical expected value — and applying the
engine's exact payout rule: the left-to-right run with WILD substitution,
paying the **greater** of the substituted-symbol combination and a leading
pure-WILD combination. See `analyze_math.py`. This enumeration is
shuffle-independent and matches the Monte Carlo base RTP to floating-point
precision (`R_b ≈ 90.80 %`).

### 5.2 Total RTP with free-spin feature

Treating the feature as a geometric series of independent spins:

$$
R_{\text{total}} \;\approx\; R_b \cdot (1 - p_t) \cdot \frac{1}{1 - N \cdot p_t}
$$

The `(1 - p_t)` factor approximates the engine zeroing payline wins on any spin
where the scatter trigger fires. It is a close estimate only; the exact
scatter-zeroing loss is captured by the Monte Carlo (§5.3), which is
authoritative.

### 5.3 Certified figures (5,000,000-spin Monte Carlo)

| Metric                     |        Value | 95 % CI half-width |
| -------------------------- | -----------: | -----------------: |
| **Total RTP**              |  **97.05 %** |          ± 0.23 %  |
| Base-game RTP (paid only)  |     90.80 %  |          ± 0.23 %  |
| Free-spin contribution     |      6.24 %  |                    |
| House edge `1 − R`         |      2.95 %  |                    |
| Scatter trigger rate       |     0.647 %  |          ± 0.002 % |
| Hit frequency (paid spins) |     41.78 %  |                    |

Independent re-shuffled runs span **96.83 % – 97.05 %** total RTP. Because the
strips are re-shuffled once per session (`build_all_strips`) and a spin reads
three *consecutive* strip positions, the strip ORDER mildly affects the
scatter-zeroing correlation (the per-line marginals — and thus the 90.80 % base
— are shuffle-independent). The shuffle-averaged certified RTP is therefore
**≈ 96.9 %**, stated conservatively. The closed-form base enumeration (§5.1)
yields the same 90.80 % base, in agreement with the simulation.

### 5.4 Convergence

| Sample size required | Confidence interval (95 %) on total RTP |
| -------------------- | --------------------------------------- |
|        10,390 spins  | ± 5 %                                   |
|       259,751 spins  | ± 1 %                                   |
|    25,975,103 spins  | ± 0.1 %                                 |

A live player completing 100 spins has a ± 51 % CI around the long-run RTP —
short-term observation has no diagnostic value.

---

## 6. Volatility

| Statistic                     | Value      | Interpretation             |
| ----------------------------- | ---------- | -------------------------- |
| Std-dev of per-spin total win | 2.60 × bet | **LOW volatility**         |
| Hit frequency (any payout)    | 41.78 %    | Frequent small wins        |
| % spins paying 0 < x ≤ 1×     | 21.56 %    | Consolation (sub-bet) wins |
| % spins paying ≥ 5×           | 4.69 %     | Moderate "good win" rate   |
| % spins paying ≥ 20×          | 0.26 %     | Rare big-win events        |
| % spins paying ≥ 100×         | 0.0002 %   | Extremely rare huge wins   |

**Industry classification cutoffs** (std-dev / bet):

| Class      | σ/bet   |
| ---------- | ------- |
| Low        | < 3.5   |
| Medium     | 3.5–6   |
| High       | 6–9     |
| Very High  | > 9     |

A `σ/bet = 2.60` profile is consistent with classic-style slots optimised for
session length over jackpot drama. Note that ~21.6 % of spins are **sub-bet
"consolation" wins** (a payout smaller than the stake), so the game pays
*something* on ~42 % of spins but returns *more than the stake* on only ~20.9 %.

---

## 7. Win-Size Distribution

From the 5 M-spin certification run:

| Win range (× bet)        | Frequency | 1 in N spins |
| ------------------------ | --------: | -----------: |
| 0 (loss)                 |  57.574 % |          1.7 |
| 0 < x ≤ 1   (small)      |  21.561 % |          4.6 |
| 1 < x ≤ 5   (modest)     |  16.172 % |          6.2 |
| 5 < x ≤ 20  (good)       |   4.436 % |         22.5 |
| 20 < x ≤ 100 (big)       |   0.257 % |          390 |
| 100 < x ≤ 500 (huge)     |  0.0002 % |      454,545 |
| > 500 (mega)             |        0  |            – |

---

## 8. Maximum Theoretical Win

The paytable's combinatorial maximum is **2,580 × bet** — every line paying
WILD 5-of-a-kind, which requires **all 15 visible cells to display WILD**. Given
the strip composition (reels 0/2/4 carry only one WILD each), this is
**unreachable** from a single spin: those reels can never show three WILDs in
three consecutive stops. The single-payline maximum is WILD 5-of-a-kind =
2,580 line-bet units = **129 × total bet**; a spin can stack several winning
lines above that.

The realised maximum across 5 M certified spins was **174.55 × bet**; across
independent runs the observed ceiling is **~175 – 220 × bet** — the realistic
max-win figure, far below the unreachable 2,580 × paytable cap.

---

## 9. Risk-of-Ruin Analysis

Flat-bet player; 2,000 independent trials per scenario.

| Starting bankroll | Spin limit | P(ruin) | Avg spins played |
| ----------------: | ---------: | ------: | ---------------: |
|       50 × bet    |        100 |   1.70 %|              100 |
|      100 × bet    |        200 |   0.10 %|              200 |
|      200 × bet    |        500 |   0.00 %|              500 |
|      500 × bet    |      1,000 |   0.00 %|            1,000 |
|    1,000 × bet    |      2,000 |   0.00 %|            2,000 |

A 100-bet bankroll has effectively zero short-session ruin risk — consistent
with low volatility and frequent small wins.

---

## 10. Verification Methodology

1. **Reel strips** are defined declaratively in `engine/reel_strips.py` and
   shuffled (Fisher–Yates) at strip-build time. Stop selection uses Python's
   Mersenne-Twister PRNG via `random.randrange`.
2. **Spin generation** picks a uniform stop per reel and returns three
   consecutive symbols (with wraparound).
3. **Evaluation** (`engine/evaluator.py`):
   - Determine `base` symbol = first non-WILD non-SCATTER on the payline.
   - Count the leading run where each symbol equals `base` or `WILD`.
   - Each line pays the **greater** of the substituted-symbol combination and a
     leading pure-WILD combination (e.g. 3 WILDs = WILD ×3 (103) beats LEMON ×5
     (52)); lookup `(symbol, count)` in the paytable; multiply by `line_bet`.
   - 4th and 5th SCATTERs on a single grid are replaced by CHERRY by
     `_cap_scatters` (free-spin count caps at one award per spin).
   - On scatter trigger, payline wins on that spin are zeroed and free spins
     are queued.
4. **Free spins** run with the same evaluator; re-triggers add to the pending
   queue.
5. **Certification** (`simulate_rtp.py`) runs ≥ 1 M paid spins, tracks Welford
   online variance, and reports the metrics in §5–9.

---

## 11. Statistical Sign-off

| Item                       | Result                              |
| -------------------------- | ----------------------------------- |
| RTP target                 | ~96 % ± 1 %                         |
| RTP measured (5 M spins)   | 97.05 % ± 0.23 % (within target)    |
| RTP repeatability (runs)   | 96.83 %, 96.94 %, 97.05 %  →  mean ≈ 96.9 % |
| Volatility class           | LOW (σ/bet 2.60)                    |
| Engine determinism         | Verified — identical seed produces identical sequence |
| Math vs. engine agreement  | Closed-form base 90.80 % = sim base 90.80 % |

The game is mathematically certified for deployment with a stated RTP of
**96.9 %** (shuffle-averaged; individual runs span 96.8 – 97.1 %).

---

## 12. Reproduction Steps

```powershell
cd slot-backend
.\.venv\Scripts\Activate.ps1

# Closed-form analysis
python analyze_math.py

# Certification run (5 M spins, ~2 min)
python simulate_rtp.py 5000000
```

Both scripts use the exact production code path; no shadow implementation
exists. Any change to `engine/paytable.py`, `engine/reel_strips.py`, or
`engine/evaluator.py` invalidates this document and requires a re-run.
