from __future__ import annotations
from datetime import datetime
import httpx
from .config import settings
from .models import TradeIdea


def _color(score: float):
    if score >= 90: return 0x00C853
    if score >= 85: return 0x64DD17
    return 0xFFD600


def send_trade_alert(idea: TradeIdea):
    if settings.dry_run or not settings.discord_webhook_url:
        print(render_text(idea))
        return
    embed = {
        "title": f"🔥 {idea.score:.0f}/100 — {idea.symbol} {idea.direction}",
        "description": f"**{idea.setup}** • **{idea.status}**\nTradingAgents: **{idea.research_rating}**",
        "color": _color(idea.score),
        "fields": [
            {"name":"Current","value":f"${idea.current_price:.2f}","inline":True},
            {"name":"Entry","value":f"${idea.entry_low:.2f} – ${idea.entry_high:.2f}","inline":True},
            {"name":"Stop","value":f"${idea.stop:.2f}","inline":True},
            {"name":"Target 1","value":f"${idea.target1:.2f}","inline":True},
            {"name":"Target 2","value":f"${idea.target2:.2f}","inline":True},
            {"name":"R:R","value":f"{idea.rr1:.1f}:1 / {idea.rr2:.1f}:1","inline":True},
            {"name":"Suggested shares","value":str(idea.shares),"inline":True},
            {"name":"Technical","value":f"{idea.technical_score:.0f}","inline":True},
            {"name":"Research","value":f"{idea.research_score:.0f}","inline":True},
        ],
        "footer": {"text": "Research signal only — no order was placed"},
        "timestamp": datetime.utcnow().isoformat(),
    }
    if idea.research_summary:
        embed["fields"].append({"name":"Agent research","value":idea.research_summary[:900],"inline":False})
    r = httpx.post(settings.discord_webhook_url, json={"embeds":[embed]}, timeout=15)
    r.raise_for_status()


def send_status(message: str):
    if not settings.send_status_alerts:
        return
    if settings.dry_run or not settings.discord_webhook_url:
        print("STATUS:", message); return
    httpx.post(settings.discord_webhook_url, json={"content":f"🤖 **Scanner status** — {message}"}, timeout=15).raise_for_status()


def render_text(i: TradeIdea) -> str:
    return f"{i.symbol} {i.direction} {i.setup} {i.score}/100 | entry {i.entry_low}-{i.entry_high} | stop {i.stop} | T1 {i.target1} | T2 {i.target2} | {i.status}"


def send_outcome(symbol: str, outcome: str, fingerprint: str):
    msg = f"📊 **Trade outcome** — `{symbol}` → **{outcome}**\n`{fingerprint}`"
    if settings.dry_run or not settings.discord_webhook_url:
        print(msg); return
    httpx.post(settings.discord_webhook_url, json={"content": msg}, timeout=15).raise_for_status()
