from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
import math
from statistics import NormalDist

import httpx
import pandas as pd

from .config import settings


@dataclass
class BTC15Signal:
    generated_at: str
    window_start: str
    window_end: str
    seconds_remaining: int
    reference_source: str
    reference_open: float
    current_price: float
    move_from_open_pct: float
    direction: str
    probability: float
    fair_price_cents: float
    max_buy_price_cents: float
    suggested_contracts: int
    estimated_cost_at_max_buy: float
    max_risk_dollars: float
    take_profit_price_cents: float
    exit_probability_pct: float
    confidence: float
    realized_vol_1m_pct: float
    momentum_1m_pct: float
    momentum_3m_pct: float
    trend_score: float
    orderbook_imbalance: float
    spread_bps: float
    actionable: bool
    reason: str

    def to_dict(self):
        return asdict(self)


class BTC15Data:
    base = "https://data.alpaca.markets"

    def __init__(self):
        self.headers = {
            "APCA-API-KEY-ID": settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
        }
        self.client = httpx.Client(timeout=20.0, headers=self.headers)

    def bars_1m(self, lookback_minutes: int = 120) -> pd.DataFrame:
        start = (datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)).isoformat()
        r = self.client.get(
            f"{self.base}/v1beta3/crypto/us/bars",
            params={"symbols":"BTC/USD","timeframe":"1Min","start":start,"limit":10000,"sort":"asc"},
        )
        r.raise_for_status()
        rows = (r.json().get("bars") or {}).get("BTC/USD") or []
        if not rows:
            raise RuntimeError("No BTC/USD one-minute bars returned by Alpaca")
        df = pd.DataFrame(rows).rename(columns={"t":"timestamp","o":"open","h":"high","l":"low","c":"close","v":"volume"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df[["timestamp","open","high","low","close","volume"]]

    def latest_trade(self) -> float:
        r = self.client.get(f"{self.base}/v1beta3/crypto/us/latest/trades", params={"symbols":"BTC/USD"})
        r.raise_for_status()
        trade = (r.json().get("trades") or {}).get("BTC/USD") or {}
        price = float(trade.get("p") or 0)
        if price <= 0:
            raise RuntimeError("No BTC/USD latest trade returned by Alpaca")
        return price

    def orderbook(self) -> tuple[float, float]:
        r = self.client.get(f"{self.base}/v1beta3/crypto/us/latest/orderbooks", params={"symbols":"BTC/USD"})
        r.raise_for_status()
        book = (r.json().get("orderbooks") or {}).get("BTC/USD") or {}
        asks = book.get("a") or []
        bids = book.get("b") or []
        if not asks or not bids:
            return 0.0, 999.0
        ask = float(asks[0].get("p") or 0)
        bid = float(bids[0].get("p") or 0)
        mid = (ask + bid) / 2 if ask > 0 and bid > 0 else 0
        spread_bps = ((ask - bid) / mid * 10000) if mid > 0 else 999.0
        bid_size = sum(float(x.get("s") or 0) for x in bids[:5])
        ask_size = sum(float(x.get("s") or 0) for x in asks[:5])
        total = bid_size + ask_size
        imbalance = (bid_size - ask_size) / total if total > 0 else 0.0
        return imbalance, spread_bps


def _quarter_window(now: datetime) -> tuple[datetime, datetime]:
    start_minute = (now.minute // 15) * 15
    start = now.replace(minute=start_minute, second=0, microsecond=0)
    return start, start + timedelta(minutes=15)


def _ema(series: pd.Series, span: int) -> float:
    return float(series.ewm(span=span, adjust=False).mean().iloc[-1])


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def build_signal(now: datetime | None = None) -> BTC15Signal:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    start, end = _quarter_window(now)
    seconds_remaining = max(0, int((end - now).total_seconds()))

    md = BTC15Data()
    bars = md.bars_1m()
    price = md.latest_trade()
    imbalance, spread_bps = md.orderbook()

    window_rows = bars[bars.timestamp >= pd.Timestamp(start)]
    reference_open = float(bars.close.iloc[-1]) if window_rows.empty else float(window_rows.open.iloc[0])

    closes = bars.close.astype(float)
    log_returns = (closes / closes.shift(1)).apply(lambda x: math.log(x) if pd.notna(x) and x > 0 else float("nan")).dropna()
    recent_returns = log_returns.tail(60)
    sigma_1m = max(float(recent_returns.std(ddof=1) or 0), 0.00005)

    mom1 = (price / float(closes.iloc[-1]) - 1.0) * 100
    anchor3 = float(closes.iloc[-4]) if len(closes) >= 4 else float(closes.iloc[0])
    mom3 = (price / anchor3 - 1.0) * 100

    ema3 = _ema(closes.tail(30), 3)
    ema8 = _ema(closes.tail(30), 8)
    trend_raw = (ema3 / ema8 - 1.0) * 10000 if ema8 > 0 else 0.0
    trend_score = _clip(50 + trend_raw * 2.0, 0, 100)

    current_log_edge = math.log(price / reference_open) if reference_open > 0 else 0.0
    remaining_minutes = max(seconds_remaining / 60.0, 0.25)
    drift_per_min = _clip((mom3 / 100.0) / 3.0, -0.0015, 0.0015)
    expected_remaining = drift_per_min * remaining_minutes * 0.30
    denom = sigma_1m * math.sqrt(remaining_minutes)
    z = (current_log_edge + expected_remaining) / max(denom, 1e-9)
    base_up = NormalDist().cdf(_clip(z, -4.0, 4.0))

    trend_adjust = _clip((trend_score - 50) / 100 * 0.08, -0.04, 0.04)
    book_adjust = _clip(imbalance * 0.04, -0.03, 0.03)
    p_up = _clip(0.5 + (base_up - 0.5) * 0.82 + trend_adjust + book_adjust, 0.03, 0.97)

    if p_up >= 0.5:
        direction = "UP"
        probability = p_up
    else:
        direction = "DOWN"
        probability = 1.0 - p_up

    confidence = probability * 100
    fair_cents = probability * 100
    max_buy_cents = max(1.0, (probability - settings.btc15_min_edge) * 100)
    contract_cost = max_buy_cents / 100.0
    suggested_contracts = max(0, math.floor(settings.btc15_max_risk_dollars / contract_cost)) if contract_cost > 0 else 0
    estimated_cost = suggested_contracts * contract_cost
    take_profit_cents = max(max_buy_cents, min(99.0, fair_cents - settings.btc15_take_profit_discount_cents))

    within_time = settings.btc15_min_seconds_remaining <= seconds_remaining <= settings.btc15_max_seconds_remaining
    confidence_ok = confidence >= settings.btc15_min_confidence
    spread_ok = spread_bps <= 25
    actionable = bool(within_time and confidence_ok and spread_ok and suggested_contracts > 0)

    reasons = []
    if not within_time: reasons.append("outside preferred entry window")
    if not confidence_ok: reasons.append(f"confidence below {settings.btc15_min_confidence:.0f}%")
    if not spread_ok: reasons.append("BTC proxy spread too wide")
    if actionable: reasons.append("probability, timing, liquidity and risk filters passed")

    return BTC15Signal(
        generated_at=now.isoformat(), window_start=start.isoformat(), window_end=end.isoformat(),
        seconds_remaining=seconds_remaining,
        reference_source="Alpaca BTC/USD proxy — BRTI settlement feed not connected",
        reference_open=round(reference_open,2), current_price=round(price,2),
        move_from_open_pct=round((price/reference_open-1)*100,4) if reference_open>0 else 0.0,
        direction=direction, probability=round(probability,4), fair_price_cents=round(fair_cents,1),
        max_buy_price_cents=round(max_buy_cents,1), suggested_contracts=suggested_contracts,
        estimated_cost_at_max_buy=round(estimated_cost,2), max_risk_dollars=round(settings.btc15_max_risk_dollars,2),
        take_profit_price_cents=round(take_profit_cents,1), exit_probability_pct=round(settings.btc15_exit_probability*100,1),
        confidence=round(confidence,1), realized_vol_1m_pct=round(sigma_1m*100,4),
        momentum_1m_pct=round(mom1,4), momentum_3m_pct=round(mom3,4), trend_score=round(trend_score,1),
        orderbook_imbalance=round(imbalance,3), spread_bps=round(spread_bps,2),
        actionable=actionable, reason="; ".join(reasons),
    )
