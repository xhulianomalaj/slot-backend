# Slot Backend — Mathematically Certified Game Server

A FastAPI backend that powers a 5-reel × 3-row, 20-payline video slot. Every
spin outcome is generated and evaluated server-side; the client merely renders
what the server returns. Fully verifiable RTP, hit frequency, and volatility
via two independent tools (closed-form analysis + Monte Carlo simulation).

> **Certified RTP: 96.5 %** (1,000,000-spin Monte Carlo, ± 0.53 % at 95 % CI)
> Volatility: **LOW** (σ / bet = 2.73) — see [`MATH_MODEL.md`](MATH_MODEL.md).

---

## Why this project

This repository is a portfolio piece demonstrating production-grade slot-game
engineering:

- **Server-authoritative architecture** — the same pattern used by regulated
  iGaming products. The client cannot influence outcomes.
- **Mathematically certified RTP** — the paytable was tuned and verified against
  industry-standard targets, not guessed.
- **Two-tool verification pipeline**
  - `analyze_math.py` — exact closed-form RTP via rational arithmetic
    (no floating-point drift, no sampling noise).
  - `simulate_rtp.py` — 1 M-spin Monte Carlo against the same engine code,
    reporting RTP, volatility class, win-size distribution, max-win analysis,
    and risk-of-ruin curves.
- **Full audit trail** — every spin in a session is logged on the server and
  exposed via a read-only stats endpoint.

The full math model, methodology, and certification figures live in
[`MATH_MODEL.md`](MATH_MODEL.md).

---

## Tech Stack

| Layer            | Technology                       |
| ---------------- | -------------------------------- |
| API              | FastAPI 0.115+                   |
| Validation       | Pydantic v2                      |
| Server           | Uvicorn                          |
| Math libraries   | Standard library only (`fractions`, `math`) |
| Python           | 3.11+                            |

No third-party RNG, no PRNG seeding shenanigans — uses Python's
Mersenne-Twister via `random.randrange` for the strip stop selection.

---

## Project Layout

```
slot-backend/
├── api/
│   ├── models.py        Pydantic request / response schemas
│   └── routes.py        /session, /spin, /buy-bonus, /session/<id>/stats
├── engine/
│   ├── symbols.py       Symbol identifiers
│   ├── reel_strips.py   Strip composition + Fisher–Yates build + stop pick
│   ├── paytable.py      20 paylines + symbol multipliers
│   ├── evaluator.py     Payline + scatter evaluation
│   └── session.py       In-memory session store + spin log
├── main.py              FastAPI app entry point
├── analyze_math.py      Closed-form RTP analysis (exact, no simulation)
├── simulate_rtp.py      Monte Carlo certification harness
├── MATH_MODEL.md        Regulator-style math model document
└── requirements.txt
```

---

## Prerequisites

- **Python 3.11** or later

---

## Getting Started

```powershell
# From the slot-backend/ directory
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run the API server
uvicorn main:app --reload --port 8000
```

The API is now available at `http://localhost:8000` with interactive docs at
`http://localhost:8000/docs`.

---

## API Reference

| Method | Path                              | Purpose                                  |
| ------ | --------------------------------- | ---------------------------------------- |
| POST   | `/api/session`                    | Create a new player session              |
| POST   | `/api/spin`                       | Play one spin (paid or free)             |
| POST   | `/api/buy-bonus`                  | Pay a fixed multiplier to enter free spins |
| GET    | `/api/session/{id}/stats`         | Read-only RTP / hit-freq / scatter stats |

The `stats` endpoint returns observed metrics alongside the theoretical
targets so a player or auditor can compare a live session to the certified
math model in real time.

---

## Verifying the Math Yourself

Two independent tools, both driving the same engine code:

```powershell
# 1. Exact closed-form analysis (rational arithmetic)
python analyze_math.py

# 2. Monte Carlo certification — 1 M paid spins, ~20 s
python simulate_rtp.py 1000000
```

The Monte Carlo run reports:

- Total RTP, base-game RTP, scatter trigger rate (with 95 % CI)
- Hit frequency
- Per-symbol win counts and RTP contribution
- Volatility classification (industry σ / bet bands)
- Win-size distribution (loss / small / modest / good / big / huge / mega)
- Maximum theoretical and observed single-spin payout
- Risk-of-ruin curves across five bankroll/duration scenarios

For the certification methodology, exact paytable, strip composition, and
sign-off, see [`MATH_MODEL.md`](MATH_MODEL.md).

---

## Architectural Notes

- **Server-authoritative.** The client posts a bet; the server returns the
  grid, winlines, total win, and free-spin awards. The client never decides
  outcomes.
- **In-memory session store.** Sessions live in a process-local dict — fine for
  development and demos. Swap for Redis or a database for production.
- **Spin log.** Every paid and free spin is appended to `session.spin_log` so
  the `/stats` endpoint can compute observed RTP, hit frequency, and scatter
  rate without re-running the engine.
- **Single source of truth.** Both `analyze_math.py` and `simulate_rtp.py`
  import from `engine/`. There is no shadow implementation that could drift
  from the production code.

---

## License

This project is published for **viewing and study purposes only**. It is not
licensed for commercial redistribution. © 2026.
