from fastapi import APIRouter, HTTPException

from api.models import (
    BuyBonusRequest,
    SessionRequest,
    SessionResponse,
    SpinRequest,
    SpinResponse,
)
from engine.evaluator import build_grid, evaluate_spin
from engine.session import DEFAULT_BET, Session, create_session, get_session
from engine.symbols import SCATTER

router = APIRouter()

# Cost = bet × this multiplier (must match BUY_BONUS_MULTIPLIER in frontend).
BUY_BONUS_MULTIPLIER = 80


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

    if not req.isFreeSpins:
        if req.bet > session.balance:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        session.balance = round(session.balance - req.bet, 2)
        session.total_wagered = round(session.total_wagered + req.bet, 2)

    session.rounds_played += 1

    grid = build_grid(session.reel_strips)
    winlines, total_win, teasing_reels, free_spins_awarded = evaluate_spin(grid, req.bet)

    session.balance = round(session.balance + total_win, 2)
    session.total_won = round(session.total_won + total_win, 2)

    return SpinResponse(
        grid=grid,
        totalWin=total_win,
        winlines=winlines,
        teasingReels=teasing_reels,
        freeSpinsAwarded=free_spins_awarded,
        balance=session.balance,
    )


@router.post("/buy-bonus", response_model=SpinResponse)
def buy_bonus(req: BuyBonusRequest) -> SpinResponse:
    session = _resolve_session(req.sessionId)

    cost = round(req.bet * BUY_BONUS_MULTIPLIER, 2)
    if cost > session.balance:
        raise HTTPException(status_code=400, detail="Insufficient balance for bonus buy")

    session.balance = round(session.balance - cost, 2)
    session.total_wagered = round(session.total_wagered + cost, 2)
    session.rounds_played += 1

    # Guarantee 3 scatters on reels 0, 2, 4 (middle row) — same as mock.
    grid = build_grid(session.reel_strips)
    for reel in (0, 2, 4):
        grid[reel][1] = SCATTER  # row 1 = middle

    return SpinResponse(
        grid=grid,
        totalWin=0,
        winlines=[],
        teasingReels=[],
        freeSpinsAwarded=10,
        balance=session.balance,
    )
