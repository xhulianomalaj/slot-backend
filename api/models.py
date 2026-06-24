from pydantic import BaseModel, Field


class SpinRequest(BaseModel):
    # bet must be positive; the route additionally checks it is on the official
    # bet ladder. gt=0 alone blocks the negative-bet balance-minting exploit.
    bet: float = Field(gt=0)
    sessionId: str | None = None
    isFreeSpins: bool = False


class BuyBonusRequest(BaseModel):
    bet: float = Field(gt=0)
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
