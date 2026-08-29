from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Literal

Direction = Literal["LONG", "SHORT"]
SetupType = Literal["PULLBACK", "BREAKOUT"]
Status = Literal["ACTIVE", "WAIT_PULLBACK", "WAIT_BREAKOUT", "INVALID"]


@dataclass
class Candidate:
    symbol: str
    price: float
    prev_close: float
    day_change_pct: float
    day_volume: float
    prev_volume: float
    dollar_volume: float
    prefilter_score: float


@dataclass
class TechnicalSnapshot:
    symbol: str
    price: float
    ema9: float
    ema20: float
    vwap: float
    rsi14: float
    atr14: float
    rel_volume: float
    momentum_15m_pct: float
    support: float
    resistance: float
    technical_score: float
    direction: Direction


@dataclass
class ResearchResult:
    symbol: str
    rating: str
    score: float
    summary: str


@dataclass
class TradeIdea:
    symbol: str
    direction: Direction
    setup: SetupType
    entry_low: float
    entry_high: float
    stop: float
    target1: float
    target2: float
    rr1: float
    rr2: float
    score: float
    status: Status
    current_price: float
    technical_score: float
    research_score: float
    momentum_score: float
    entry_location_score: float
    risk_reward_score: float
    market_score: float
    research_rating: str
    research_summary: str
    shares: int

    def to_dict(self):
        return asdict(self)
