# Slot Game Math Model

**Game:** Popular-Slot 5-Reel Video Slot (LDW profile)
**Document Version:** 1.3
**Engine Reference:** `slot-backend/engine/`
**Verification Method:** Exact closed-form analysis on a fixed certified reelset, confirmed by Monte Carlo (20,000,000 paid spins)

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
wins remain rare — the standard volatility-shaping technique. The game ships a
single **fixed, certified reel arrangement** (the hardcoded `REEL_STRIPS` in
`engine/reel_strips.py`): both the symbol *composition* above and the stop
*order* are fixed and identical for every session. The RTP is therefore one
deterministic, exactly-computed number.

---

## 3. Paytable

Multipliers are expressed in units of **line bet** (`bet / 20`).

| Symbol | 3-of-a-kind | 4-of-a-kind | 5-of-a-kind |
| ------ | ----------: | ----------: | ----------: |
| WILD   |         116 |         799 |       7,415 |
| SEVEN  |          52 |         328 |       4,277 |
| BAR    |          28 |         122 |         670 |
| BELL   |          17 |          67 |         309 |
| PLUM   |           9 |          34 |         155 |
| CHERRY |           6 |          26 |         135 |
| ORANGE |           5 |          22 |         113 |
| LEMON  |           5 |          18 |          93 |

SCATTER pays no line credits; its only function is to award free spins.

This is a **"popular-slot" LDW (losses-disguised-as-wins) paytable**: the low
symbols (CHERRY, LEMON, ORANGE, PLUM, BELL) still pay 3-of-a-kind, but only tiny
sub-bet amounts, so most "wins" return less than the stake. The return is
back-loaded into a steep, rare premium tail (SEVEN/WILD 5-of-a-kind).

> **Display note:** these multipliers are in *line-bet* units. On a 20-line bet
> the headline figures divide by 20 in *total-bet* terms — e.g. WILD ×5 = 7,415
> line units = **371 × total bet** on one line; SEVEN ×5 = 4,277 line units =
> **214 × total bet**.

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
pure-WILD combination. See `analyze_math.py`. This enumeration depends only on
the per-reel symbol *marginals*, so it is **arrangement-independent** — it holds
for the fixed certified reelset and matches the Monte Carlo base RTP to
floating-point precision (`R_b = 90.9492 %` unzeroed).

### 5.2 Total RTP with free-spin feature

Because the reelset is fixed, the total RTP is a single deterministic number,
computed in closed form by `analyze_math.py`:

$$
R_{\text{total}} \;=\; \big(R_b - V_{\text{scatter}}\big) \cdot \frac{1}{1 - N \cdot p_t}
$$

- **Unzeroed base payline RTP** `R_b = 90.9492 %` (arrangement-independent,
  `9^5` enumeration; §5.1).
- **Scatter-void loss** `V_scatter = 0.2995 %` — the payline return zeroed on
  spins that fire the scatter trigger. With a fixed reelset this is now
  **exactly computable**: enumerate all grids with ≥ 3 scatter-showing reels and
  subtract their payline contribution. No Monte-Carlo estimate is required.
- **Zeroed base** `R_b − V_scatter = 90.6497 %`.
- **Free-spin multiplier** `1 / (1 − N·p_t) = 1 / (1 − 10·t) = 1.06981`, with
  scatter trigger `t = 0.6526 %`.

$$
R_{\text{total}} \;=\; 90.6497 \% \times 1.06981 \;=\; \mathbf{96.9784\,\%}
$$

This is **exact** — a single deterministic value, not a bracket. House edge
`1 − R = 3.04 %`.

### 5.3 Certification figures

The closed-form total above is exact. An independent **20,000,000-spin Monte
Carlo** on the same fixed reelset measured **96.955 %**, within Monte-Carlo
noise of the exact 96.9784 % — confirming the closed-form result.

| Metric                          |          Value | Source                |
| ------------------------------- | -------------: | --------------------- |
| **Total RTP** (exact)           | **96.98 %** (96.9784 %) | closed form  |
| Total RTP (20 M MC confirm)     |       96.955 % | Monte Carlo           |
| Base-game RTP, unzeroed (exact) |      90.9492 % | `9^5` enumeration     |
| Scatter-void loss               |       0.2995 % | exact grid enumeration |
| Base-game RTP, zeroed (exact)   |      90.6497 % | closed form           |
| Free-spin multiplier            |        1.06981 | `1/(1 − 10·t)`        |
| House edge `1 − R`              |         3.04 % | closed form           |
| Scatter trigger rate `t`        |       0.6526 % | 1 in 153.2 spins      |
| Free spins per trigger `T`      |        ≈ 10.70 | geometric model       |
| Hit frequency (paid spins)      |        42.55 % | closed form / MC      |

Because the reelset is fixed, every figure here is a single exact number, not a
range — there is no session-to-session variation in the long-run RTP.

### 5.4 Convergence

| Sample size required | Confidence interval (95 %) on measured RTP |
| -------------------- | ------------------------------------------ |
|        27,500 spins  | ± 5 %                                      |
|       687,000 spins  | ± 1 %                                      |
|    68,700,000 spins  | ± 0.1 %                                    |

The closed-form total RTP is exact, so no sampling is needed to certify it;
these sizes only describe how quickly a *Monte-Carlo* run converges on the
known value. They scale with `σ² ≈ 4.23²` (§6). A live player completing 100
spins has a ± 83 % CI around the long-run RTP — short-term observation has no
diagnostic value.

---

## 6. Volatility

| Statistic                     | Value      | Interpretation               |
| ----------------------------- | ---------- | ---------------------------- |
| Std-dev of per-spin total win | 4.23 × bet | **MEDIUM volatility**        |
| Hit frequency (any payout)    | 42.55 %    | Frequent small wins (LDW)    |
| % spins paying 0 < x ≤ 1×     | 23.37 %    | Sub-bet LDW "wins"           |
| % spins paying > 5×           | 5.13 %     | Moderate "good win" rate     |
| % spins paying > 20×          | 0.337 %    | Rare big-win events          |
| % spins paying > 100×         | 0.013 %    | Extremely rare huge wins     |

**Industry classification cutoffs** (std-dev / bet):

| Class      | σ/bet   |
| ---------- | ------- |
| Low        | < 3.5   |
| Medium     | 3.5–6   |
| High       | 6–9     |
| Very High  | > 9     |

At `σ/bet = 4.23` the game sits squarely in the **MEDIUM** band — a
"popular-slot" LDW profile with a steep, rare top tail rather than a
session-length grind. The defining feature is the **losses-disguised-as-wins
(LDW)** structure: 23.37 % of spins are **sub-bet "wins"** (a payout smaller
than the stake), so although the game pays *something* on 42.55 % of spins, it
returns *more than the stake* on only ~19 %. In fact **54.1 % of all *winning*
spins pay ≤ 1 × the bet** (23.37 % sub-bet out of 42.55 % total winning spins),
the textbook LDW signature.

---

## 7. Win-Size Distribution

From the 20 M-spin certification run on the fixed reelset:

| Win range (× bet)        | Frequency | 1 in N spins |
| ------------------------ | --------: | -----------: |
| 0 (loss)                 |  56.80 %  |          1.8 |
| 0 < x ≤ 1   (small)      |  23.37 %  |          4.3 |
| 1 < x ≤ 5   (modest)     |  14.71 %  |          6.8 |
| 5 < x ≤ 20  (good)       |   4.79 %  |         20.9 |
| 20 < x ≤ 100 (big)       |   0.324 % |          308 |
| 100 < x ≤ 500 (huge)     |   0.013 % |        7,849 |
| > 500 (mega)             | 0.0001 %  |      909,091 |

The bottom two bands (small + modest) are the LDW core; the `huge` and `mega`
bands are the rare premium tail. A single spin exceeded 500 × bet only about
once in every ~900,000 spins across the 20 M run.

---

## 8. Maximum Theoretical Win

The paytable's combinatorial maximum is **7,415 × bet** — every line paying
WILD 5-of-a-kind (20 × 7,415 line-bet = 148,300 line-bet = 7,415 × total bet),
which requires **all 15 visible cells to display WILD**. Given the fixed reelset
(reels 0/2/4 carry only one WILD each), this is **unreachable** from a single
spin: those reels can never show three WILDs in three consecutive stops, so a
3-cell window shows ≤ 1 WILD. The single-payline maximum is WILD 5-of-a-kind =
7,415 line-bet units = **370.75 × total bet** (≈ 371 ×); a spin can stack
several winning lines above that.

The largest single spin observed across the 20 M certified spins was **650 ×
bet** (multi-line stacking) — the realistic max-win figure, far below the
unreachable 7,415 × paytable cap.

---

## 9. Risk-of-Ruin Analysis

Flat-bet player; 2,000 independent trials per scenario.

| Starting bankroll | Spin limit | P(ruin) | Avg spins played |
| ----------------: | ---------: | ------: | ---------------: |
|       50 × bet    |        100 |   3.80 %|               99 |
|      100 × bet    |        200 |   0.60 %|              200 |
|      200 × bet    |        500 |   0.05 %|              500 |
|      500 × bet    |      1,000 |   0.00 %|            1,000 |
|    1,000 × bet    |      2,000 |   0.00 %|            2,000 |

A 50-bet bankroll carries a ~3.8 % short-session ruin risk and a 100-bet
bankroll ~0.6 % — consistent with a MEDIUM-volatility LDW game where the return
is back-loaded into a rare premium tail and most "wins" are sub-bet.

---

## 10. Verification Methodology

1. **Reel strips** are a **fixed certified reelset** — the hardcoded
   `REEL_STRIPS` in `engine/reel_strips.py`. The strip order is the same for
   every session; only the stop selection per spin is random, using Python's
   Mersenne-Twister PRNG via `random.randrange` (uniform per reel).
2. **Spin generation** picks a uniform stop per reel and returns three
   consecutive symbols (with wraparound).
3. **Evaluation** (`engine/evaluator.py`):
   - Determine `base` symbol = first non-WILD non-SCATTER on the payline.
   - Count the leading run where each symbol equals `base` or `WILD`.
   - Each line pays the **greater** of the substituted-symbol combination and a
     leading pure-WILD combination (e.g. 3 WILDs = WILD ×3 (116) beats LEMON ×5
     (93)); lookup `(symbol, count)` in the paytable; multiply by `line_bet`.
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
| RTP target                 | ~97 % ± 1 %                         |
| RTP (exact, closed form)   | **96.9784 %** on the fixed reelset (within target) |
| RTP (20 M MC confirm)      | 96.955 % — within MC noise of the exact value |
| Volatility class           | MEDIUM (σ/bet = 4.23)               |
| Engine determinism         | Verified — identical seed produces identical sequence |
| Math vs. engine agreement  | Closed-form total 96.9784 % = 20 M MC 96.955 % (confirming) |

The game is mathematically certified for deployment with a stated RTP of
**96.98 %**. Because the reelset is a single fixed certified arrangement, this
is one **exact deterministic number** — not a shuffle-averaged value or a
session-dependent range.

---

## 12. Reproduction Steps

```powershell
cd slot-backend
.\.venv\Scripts\Activate.ps1

# Closed-form analysis
python analyze_math.py

# Certification run (20 M spins, ~8 min)
python simulate_rtp.py 20000000
```

Both scripts use the exact production code path; no shadow implementation
exists. Any change to `engine/paytable.py`, `engine/reel_strips.py`, or
`engine/evaluator.py` invalidates this document and requires a re-run.
