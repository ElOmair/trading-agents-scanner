from __future__ import annotations
from datetime import date, datetime, timezone
import re

from .config import settings
from .models import ResearchResult, TechnicalSnapshot

RATING_SCORE = {"Buy": 95, "Overweight": 80, "Hold": 55, "Underweight": 35, "Sell": 10}
_CACHE: dict[str, tuple[datetime, ResearchResult]] = {}


def _extract_summary(state: dict) -> str:
    parts = []
    for k in ("market_report", "news_report", "sentiment_report", "fundamentals_report", "final_trade_decision"):
        v = state.get(k)
        if v:
            parts.append(str(v))
    txt = re.sub(r"\s+", " ", "\n".join(parts))
    return txt[:900]


def run_tradingagents(symbol: str, trade_date: str) -> ResearchResult:
    now = datetime.now(timezone.utc)
    cached = _CACHE.get(symbol)
    if cached and (now - cached[0]).total_seconds() < settings.research_cache_minutes * 60:
        return cached[1]
    if not settings.tradingagents_enabled:
        result = ResearchResult(symbol, "Hold", 55, "TradingAgents disabled")
        _CACHE[symbol] = (now, result)
        return result
    try:
        from tradingagents.default_config import DEFAULT_CONFIG
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        cfg = DEFAULT_CONFIG.copy()
        cfg["max_debate_rounds"] = 1
        cfg["max_risk_discuss_rounds"] = 1
        graph = TradingAgentsGraph(
            selected_analysts=("market", "social", "news", "fundamentals"),
            config=cfg,
        )
        state, signal = graph.propagate(symbol, trade_date, asset_type="stock")
        rating = str(signal).strip().title()
        if rating not in RATING_SCORE:
            rating = "Hold"
        result = ResearchResult(symbol, rating, float(RATING_SCORE[rating]), _extract_summary(state))
    except Exception as exc:
        result = ResearchResult(symbol, "Hold", 50, f"TradingAgents unavailable: {type(exc).__name__}: {exc}")
    _CACHE[symbol] = (now, result)
    return result


def research_for(snapshot: TechnicalSnapshot) -> ResearchResult:
    return run_tradingagents(snapshot.symbol, date.today().isoformat())
