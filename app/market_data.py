from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Iterable
import httpx
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings
from .models import Candidate


class AlpacaMarketData:
    trading_base = "https://paper-api.alpaca.markets"
    data_base = "https://data.alpaca.markets"

    def __init__(self):
        self.headers = {
            "APCA-API-KEY-ID": settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
        }
        self.client = httpx.Client(timeout=30.0, headers=self.headers)

    def validate(self):
        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            raise RuntimeError("ALPACA_API_KEY and ALPACA_SECRET_KEY are required")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def universe(self) -> list[str]:
        self.validate()
        r = self.client.get(
            f"{self.trading_base}/v2/assets",
            params={"status": "active", "asset_class": "us_equity"},
        )
        r.raise_for_status()
        assets = r.json()
        return [
            a["symbol"] for a in assets
            if a.get("tradable") and a.get("exchange") in {"NASDAQ", "NYSE", "AMEX", "ARCA"}
            and "/" not in a.get("symbol", "")
        ]

    def _chunks(self, symbols: list[str], size: int = 200):
        for i in range(0, len(symbols), size):
            yield symbols[i:i+size]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def snapshots(self, symbols: list[str]) -> dict:
        out = {}
        for chunk in self._chunks(symbols):
            r = self.client.get(
                f"{self.data_base}/v2/stocks/snapshots",
                params={"symbols": ",".join(chunk), "feed": "iex"},
            )
            r.raise_for_status()
            out.update(r.json())
        return out

    def prefilter(self, symbols: list[str]) -> list[Candidate]:
        snaps = self.snapshots(symbols)
        candidates: list[Candidate] = []
        for symbol, s in snaps.items():
            daily = s.get("dailyBar") or {}
            prev = s.get("prevDailyBar") or {}
            trade = s.get("latestTrade") or {}
            price = float(trade.get("p") or daily.get("c") or 0)
            prev_close = float(prev.get("c") or 0)
            volume = float(daily.get("v") or 0)
            prev_volume = float(prev.get("v") or 0)
            if price < settings.min_price or prev_close <= 0:
                continue
            dollar_volume = price * volume
            if dollar_volume < settings.min_dollar_volume:
                continue
            change = (price / prev_close - 1) * 100
            rel = volume / prev_volume if prev_volume > 0 else 0
            score = min(100.0, abs(change) * 9 + min(rel, 4) * 12 + min(dollar_volume / 50_000_000, 3) * 8)
            candidates.append(Candidate(symbol, price, prev_close, change, volume, prev_volume, dollar_volume, score))
        return sorted(candidates, key=lambda x: x.prefilter_score, reverse=True)[:settings.prefilter_limit]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def bars_5m(self, symbols: Iterable[str], lookback_hours: int = 36) -> dict[str, pd.DataFrame]:
        start = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()
        result: dict[str, pd.DataFrame] = {}
        for chunk in self._chunks(list(symbols), 100):
            r = self.client.get(
                f"{self.data_base}/v2/stocks/bars",
                params={
                    "symbols": ",".join(chunk),
                    "timeframe": "5Min",
                    "start": start,
                    "limit": 10000,
                    "adjustment": "raw",
                    "feed": "iex",
                },
            )
            r.raise_for_status()
            bars = r.json().get("bars", {})
            for symbol, rows in bars.items():
                if not rows:
                    continue
                df = pd.DataFrame(rows).rename(columns={"t":"timestamp","o":"open","h":"high","l":"low","c":"close","v":"volume"})
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
                result[symbol] = df[["timestamp","open","high","low","close","volume"]]
        return result
