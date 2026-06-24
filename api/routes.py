from fastapi import APIRouter, HTTPException

from api.models import (
    BuyBonusRequest,
    SessionRequest,
    SessionResponse,
    SpinRequest,
    SpinResponse,
)
from engine.evaluator import FREE_SPINS_COUNT, build_grid, evaluate_spin
from engine.session import DEFAULT_BET, Session, create_session, get_session
from engine.symbols import SCATTER

router = APIRouter()

# Cost = bet × this multiplier (must match BUY_BONUS_MULTIPLIER in frontend).
# Priced at the feature's fair value: a bought feature is FREE_SPINS_COUNT free
# spins (plus re-triggers) worth ~9.65× bet at the base rate, so a ~10× cost
# gives the bonus buy the same ~96.5% RTP as the base game. (At the old 80× the
# bonus buy returned only ~12% — a player trap.)
BUY_BONUS_MULTIPLIER = 10


def _resolve_session(session_id: str | None) -> Session:
    """Return the named session, or auto-create one for dev convenience."""
    if session_id:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    return create_session()


@router.post("/session", response_model=SessionResponse)
def start_session(req: SessionRequest) -> SessionResponse:
    session = create_session()
    return SessionResponse(
        sessionId=session.session_id,
        balance=session.balance,
        currency=session.currency,
        availableBets=session.available_bets,
        defaultBet=DEFAULT_BET,
        columns=session.columns,
        rows=session.rows,
    )


@router.post("/spin", response_model=SpinResponse)
def spin(req: SpinRequest) -> SpinResponse:
    session = _resolve_session(req.sessionId)

    if req.isFreeSpins:
        # Free spins are server-authoritative: the client cannot claim a free
        # spin it did not earn, and cannot change the stake mid-feature.
        if session.free_spins_remaining <= 0:
            raise HTTPException(status_code=400, detail="No free spins remaining")
        session.free_spins_remaining -= 1
        bet = session.free_spin_bet            # stake locked at trigger / bonus buy
    else:
        if req.bet > session.balance:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        session.balance = round(session.balance - req.bet, 2)
        session.total_wagered = round(session.total_wagered + req.bet, 2)
        bet = req.bet

    session.rounds_played += 1

    grid = build_grid(session.reel_strips)
    winlines, total_win, teasing_reels, free_spins_awarded = evaluate_spin(grid, bet)

    # Award / re-trigger free spins. A base spin locks the stake the whole
    # feature is played at; a re-trigger only extends the remaining count.
    if free_spins_awarded > 0:
        if not req.isFreeSpins:
            session.free_spin_bet = bet
        session.free_spins_remaining += free_spins_awarded

    session.balance   = round(session.balance + total_win, 2)
    session.total_won = round(session.total_won + total_win, 2)
    session.spin_log.append({
        "n":       session.rounds_played,
        "bet":     bet,
        "free":    req.isFreeSpins,
        "win":     total_win,
        "scatter": free_spins_awarded > 0,
        "bal":     session.balance,
    })

    return SpinResponse(
        grid=grid,
        totalWin=total_win,
        winlines=winlines,
        teasingReels=teasing_reels,
        freeSpinsAwarded=free_spins_awarded,
        balance=session.balance,
    )


@router.get("/session/{session_id}/stats")
def session_stats(session_id: str) -> dict:
    """Read-only stats for math verification.  No game state is changed.

    Call after playing any number of spins:
      GET http://localhost:8000/api/session/<sessionId>/stats
    Returns observed RTP, hit frequency, scatter rate, and the full spin log.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    log        = session.spin_log
    n_total    = len(log)
    paid       = [s for s in log if not s["free"]]
    n_paid     = len(paid)

    wagered    = round(sum(s["bet"] for s in paid), 2)
    won_total  = round(sum(s["win"] for s in log), 2)
    obs_rtp    = round(won_total / wagered, 6) if wagered > 0 else 0.0
    hit_freq   = round(sum(1 for s in paid if s["win"] > 0) / n_paid, 6) if n_paid > 0 else 0.0
    scatters   = sum(1 for s in log if s["scatter"])
    scat_rate  = round(scatters / n_paid, 6) if n_paid > 0 else 0.0

    return {
        "sessionId":             session_id,
        "totalSpins":            n_total,
        "paidSpins":             n_paid,
        "freeSpins":             n_total - n_paid,
        "totalWagered":          wagered,
        "totalWon":              won_total,
        "observedRTP":           obs_rtp,
        "theoreticalRTP":        0.969,
        "hitFrequency":          hit_freq,
        "scatterTriggers":       scatters,
        "observedScatterRate":   scat_rate,
        "theoreticalScatterRate": 0.006526,
        "log":                   log,
    }


@router.post("/buy-bonus", response_model=SpinResponse)
def buy_bonus(req: BuyBonusRequest) -> SpinResponse:
    session = _resolve_session(req.sessionId)

    cost = round(req.bet * BUY_BONUS_MULTIPLIER, 2)
    if cost > session.balance:
        raise HTTPException(status_code=400, detail="Insufficient balance for bonus buy")

    session.balance = round(session.balance - cost, 2)
    session.total_wagered = round(session.total_wagered + cost, 2)
    session.rounds_played += 1

    # Grant the free-spin feature server-side, stake locked to this bet, so the
    # follow-up isFreeSpins spins are authorized and paid at the right stake.
    session.free_spin_bet = req.bet
    session.free_spins_remaining += FREE_SPINS_COUNT

    # Guarantee 3 scatters on reels 0, 2, 4 (middle row) — same as mock.
    grid = build_grid(session.reel_strips)
    for reel in (0, 2, 4):
        grid[reel][1] = SCATTER  # row 1 = middle

    return SpinResponse(
        grid=grid,
        totalWin=0,
        winlines=[],
        teasingReels=[],
        freeSpinsAwarded=FREE_SPINS_COUNT,
        balance=session.balance,
    )
