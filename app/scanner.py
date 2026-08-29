from __future__ import annotations
import math
import pandas as pd
from .indicators import atr, ema, rsi, session_vwap
from .models import TechnicalSnapshot


def analyze_symbol(symbol: str, df: pd.DataFrame) -> TechnicalSnapshot | None:
    if df is None or len(df) < 25:
        return None
    d = df.copy().reset_index(drop=True)
    d["ema9"] = ema(d.close, 9)
    d["ema20"] = ema(d.close, 20)
    d["rsi14"] = rsi(d.close, 14)
    d["atr14"] = atr(d, 14)
    latest_date = d.timestamp.dt.date.iloc[-1]
    session = d[d.timestamp.dt.date == latest_date].copy()
    session["vwap"] = session_vwap(session)
    last = d.iloc[-1]
    slast = session.iloc[-1]
    price = float(last.close)
    ema9v, ema20v = float(last.ema9), float(last.ema20)
    vwapv = float(slast.vwap) if not math.isnan(float(slast.vwap)) else price
    rsiv = float(last.rsi14) if not math.isnan(float(last.rsi14)) else 50.0
    atrv = max(float(last.atr14), price * 0.003)
    recent = d.tail(20)
    support = float(recent.low.min())
    resistance = float(recent.high.max())
    base_vol = max(float(d.volume.tail(20).iloc[:-1].mean() or 1), 1)
    rel_volume = float(last.volume) / base_vol
    momentum = (price / float(d.close.iloc[-4]) - 1) * 100 if len(d) >= 4 else 0
    long_votes = sum([price > ema9v, ema9v > ema20v, price > vwapv, rsiv >= 52, momentum > 0])
    short_votes = sum([price < ema9v, ema9v < ema20v, price < vwapv, rsiv <= 48, momentum < 0])
    direction = "LONG" if long_votes >= short_votes else "SHORT"
    votes = max(long_votes, short_votes)
    trend_score = votes / 5 * 70
    volume_score = min(rel_volume, 3) / 3 * 20
    momentum_score = min(abs(momentum), 2) / 2 * 10
    tech_score = min(100.0, trend_score + volume_score + momentum_score)
    return TechnicalSnapshot(
        symbol=symbol, price=price, ema9=ema9v, ema20=ema20v, vwap=vwapv,
        rsi14=rsiv, atr14=atrv, rel_volume=rel_volume, momentum_15m_pct=momentum,
        support=support, resistance=resistance, technical_score=tech_score, direction=direction,
    )


def rank_technicals(bars: dict[str, pd.DataFrame], limit: int) -> list[TechnicalSnapshot]:
    out = [x for s, df in bars.items() if (x := analyze_symbol(s, df)) is not None]
    return sorted(out, key=lambda x: x.technical_score, reverse=True)[:limit]
