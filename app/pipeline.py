from __future__ import annotations
from .config import settings
from .database import init_db, mark_alerted, save_idea
from .discord import send_trade_alert
from .market_data import AlpacaMarketData
from .outcomes import resolve_outcomes
from .research import research_for
from .scanner import rank_technicals
from .scoring import make_ideas


def run_once() -> list:
    init_db()
    md = AlpacaMarketData()
    resolve_outcomes(md)
    symbols = md.universe()
    candidates = md.prefilter(symbols)
    bars = md.bars_5m([c.symbol for c in candidates])
    technicals = rank_technicals(bars, settings.technical_limit)
    results = []
    for t in technicals[:settings.research_limit]:
        research = research_for(t)
        ideas = make_ideas(t, research)
        for idea in ideas:
            if idea.score < settings.min_entry_score or idea.status == "INVALID":
                continue
            fp, is_new = save_idea(idea)
            actionable = idea.status == "ACTIVE" or settings.send_watch_alerts
            if is_new and actionable:
                send_trade_alert(idea)
                mark_alerted(fp)
            results.append(idea)
    return sorted(results, key=lambda x: x.score, reverse=True)
