from __future__ import annotations
import math
from .config import settings
from .models import ResearchResult, TechnicalSnapshot, TradeIdea


def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))


def _rr(entry: float, stop: float, target: float, direction: str) -> float:
    risk = entry - stop if direction == "LONG" else stop - entry
    reward = target - entry if direction == "LONG" else entry - target
    return reward / risk if risk > 0 else 0


def make_ideas(t: TechnicalSnapshot, r: ResearchResult, market_score: float = 70) -> list[TradeIdea]:
    direction = t.direction
    atr = t.atr14
    price = t.price
    ideas = []
    if direction == "LONG":
        pull_center = max(t.vwap, t.ema9)
        pull_low, pull_high = pull_center - 0.12 * atr, pull_center + 0.12 * atr
        pull_stop = min(t.support, pull_low - 0.8 * atr)
        pull_t1, pull_t2 = pull_high + 1.6 * atr, pull_high + 2.6 * atr
        breakout_low, breakout_high = t.resistance, t.resistance + 0.12 * atr
        breakout_stop = breakout_low - 0.9 * atr
        breakout_t1, breakout_t2 = breakout_high + 1.5 * atr, breakout_high + 2.5 * atr
    else:
        pull_center = min(t.vwap, t.ema9)
        pull_low, pull_high = pull_center - 0.12 * atr, pull_center + 0.12 * atr
        pull_stop = max(t.resistance, pull_high + 0.8 * atr)
        pull_t1, pull_t2 = pull_low - 1.6 * atr, pull_low - 2.6 * atr
        breakout_low, breakout_high = t.support - 0.12 * atr, t.support
        breakout_stop = breakout_high + 0.9 * atr
        breakout_t1, breakout_t2 = breakout_low - 1.5 * atr, breakout_low - 2.5 * atr
    specs = [
        ("PULLBACK", pull_low, pull_high, pull_stop, pull_t1, pull_t2),
        ("BREAKOUT", breakout_low, breakout_high, breakout_stop, breakout_t1, breakout_t2),
    ]
    for setup, low, high, stop, t1, t2 in specs:
        entry = (low + high) / 2
        rr1, rr2 = _rr(entry, stop, t1, direction), _rr(entry, stop, t2, direction)
        if direction == "LONG":
            if low <= price <= high: status = "ACTIVE"
            elif setup == "PULLBACK" and price > high: status = "WAIT_PULLBACK"
            elif setup == "BREAKOUT" and price < low: status = "WAIT_BREAKOUT"
            else: status = "INVALID"
        else:
            if low <= price <= high: status = "ACTIVE"
            elif setup == "PULLBACK" and price < low: status = "WAIT_PULLBACK"
            elif setup == "BREAKOUT" and price > high: status = "WAIT_BREAKOUT"
            else: status = "INVALID"
        dist = abs(price - entry) / max(atr, 1e-6)
        entry_location = clamp(100 - dist * 24)
        momentum = clamp(50 + abs(t.momentum_15m_pct) * 20 + min(t.rel_volume, 3) * 10)
        rr_score = clamp((rr2 / 3.0) * 100)
        research_score = r.score
        if direction == "LONG" and r.rating in {"Sell", "Underweight"}: research_score *= 0.45
        if direction == "SHORT" and r.rating in {"Buy", "Overweight"}: research_score *= 0.45
        score = (
            t.technical_score * 0.25 + entry_location * 0.25 + momentum * 0.15 +
            research_score * 0.10 + rr_score * 0.20 + market_score * 0.05
        )
        risk_per_share = abs(entry - stop)
        shares = math.floor(settings.max_risk_dollars / risk_per_share) if risk_per_share > 0 else 0
        ideas.append(TradeIdea(
            symbol=t.symbol, direction=direction, setup=setup, entry_low=round(low,2), entry_high=round(high,2),
            stop=round(stop,2), target1=round(t1,2), target2=round(t2,2), rr1=round(rr1,2), rr2=round(rr2,2),
            score=round(clamp(score),1), status=status, current_price=round(price,2), technical_score=round(t.technical_score,1),
            research_score=round(research_score,1), momentum_score=round(momentum,1), entry_location_score=round(entry_location,1),
            risk_reward_score=round(rr_score,1), market_score=round(market_score,1), research_rating=r.rating,
            research_summary=r.summary, shares=max(shares,0),
        ))
    return ideas
