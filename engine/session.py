import secrets
from dataclasses import dataclass, field

from engine.reel_strips import build_all_strips

AVAILABLE_BETS = [0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0, 50.0, 100.0, 200.0, 500.0, 1000.0]
DEFAULT_BET = 1.0


@dataclass
class Session:
    session_id: str
    balance: float
    currency: str
    available_bets: list[float]
    columns: int
    rows: int
    reel_strips: list[list[str]] = field(repr=False)
    # Server-side accounting
    rounds_played: int = 0
    total_wagered: float = 0.0
    total_won: float = 0.0
    # Server-authoritative free-spin state. free_spins_remaining is the number
    # of free spins the player has earned but not yet played; free_spin_bet is
    # the stake the feature is locked to (set when the feature is triggered or
    # bought) so the client cannot change bet size mid-feature.
    free_spins_remaining: int = 0
    free_spin_bet: float = 0.0
    # Per-spin log — used by the /stats endpoint for math verification.
    # Each entry: {n, bet, free, win, scatter, bal}
    spin_log: list[dict] = field(default_factory=list)


# In-memory session store. Replace with Redis / DB for production.
_sessions: dict[str, Session] = {}


def create_session(
    starting_balance: float = 1000.0,
    currency: str = "USD",
    columns: int = 5,
    rows: int = 3,
) -> Session:
    session_id = secrets.token_urlsafe(16)
    session = Session(
        session_id=session_id,
        balance=starting_balance,
        currency=currency,
        available_bets=AVAILABLE_BETS,
        columns=columns,
        rows=rows,
        reel_strips=build_all_strips(columns),
    )
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Session | None:
    return _sessions.get(session_id)
