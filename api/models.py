from pydantic import BaseModel


class SpinRequest(BaseModel):
    bet: float
    sessionId: str | None = None
    isFreeSpins: bool = False


class BuyBonusRequest(BaseModel):
    bet: float
    sessionId: str | None = None


class SessionRequest(BaseModel):
    token: str | None = None


# ─── Shared sub-models ────────────────────────────────────────────────────────

class Position(BaseModel):
    reel: int
    row: int


class Winline(BaseModel):
    lineId: int
    symbolId: str
    matchCount: int
    amount: float
    positions: list[Position]


# ─── Responses ────────────────────────────────────────────────────────────────

class SpinResponse(BaseModel):
    grid: list[list[str]]
    totalWin: float
    winlines: list[Winline]
    teasingReels: list[int] = []
    freeSpinsAwarded: int = 0
    balance: float


class SessionResponse(BaseModel):
    sessionId: str
    balance: float
    currency: str
    availableBets: list[float]
    defaultBet: float
    columns: int
    rows: int
