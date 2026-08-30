from __future__ import annotations
from datetime import datetime
import httpx
from .config import settings
from .models import TradeIdea


def _color(score: float):
    if score >= 90: return 0x00C853
    if score >= 85: return 0x64DD17
    return 0xFFD600


def _action(status: str) -> str:
    return {
        "ACTIVE": "🟢 ENTRY ZONE ACTIVE",
        "WAIT_BREAKOUT": "⏳ WAIT FOR BREAKOUT",
        "WAIT_PULLBACK": "↩️ WAIT FOR PULLBACK",
        "INVALID": "⛔ INVALID — DO NOT ENTER",
    }.get(status, status.replace("_", " "))


def _stock_quality(score: float) -> str:
    if score >= 90: return "🔥 HIGH CONVICTION"
    if score >= 85: return "💪 STRONG"
    return "👀 QUALIFIED WATCH"


def _crypto_quality(score: float) -> str:
    if score >= settings.crypto_high_conviction_score: return "🔥 HIGH CONVICTION"
    return "👀 QUALIFIED WATCH"


def _crypto_price(value: float) -> str:
    a = abs(value)
    if a >= 100:
        decimals = 2
    elif a >= 1:
        decimals = 4
    elif a >= 0.01:
        decimals = 6
    else:
        decimals = 8
    return f"${value:,.{decimals}f}"


def send_trade_alert(idea: TradeIdea):
    if settings.dry_run or not settings.discord_webhook_url:
        print(render_text(idea))
        return
    embed = {
        "title": f"📈 {idea.score:.0f}/100 — {idea.symbol} {idea.direction}",
        "description": f"**ACTION: {_action(idea.status)}**\n**QUALITY: {_stock_quality(idea.score)}**\n{idea.setup}",
        "color": _color(idea.score),
        "fields": [
            {"name":"Current","value":f"${idea.current_price:.2f}","inline":True},
            {"name":"Entry","value":f"${idea.entry_low:.2f} – ${idea.entry_high:.2f}","inline":True},
            {"name":"Stop / Invalidation","value":f"${idea.stop:.2f}","inline":True},
            {"name":"Target 1","value":f"${idea.target1:.2f}","inline":True},
            {"name":"Target 2","value":f"${idea.target2:.2f}","inline":True},
            {"name":"R:R (T1 / T2)","value":f"{idea.rr1:.1f}:1 / {idea.rr2:.1f}:1","inline":True},
            {"name":"Suggested shares","value":str(idea.shares),"inline":True},
            {"name":"Technical","value":f"{idea.technical_score:.0f}/100","inline":True},
            {"name":"Momentum","value":f"{idea.momentum_score:.0f}/100","inline":True},
            {"name":"Entry quality","value":f"{idea.entry_location_score:.0f}/100","inline":True},
        ],
        "footer": {"text": "Research signal only — wait for the stated trigger; no order was placed"},
        "timestamp": datetime.utcnow().isoformat(),
    }
    r = httpx.post(settings.discord_webhook_url, json={"embeds":[embed]}, timeout=15)
    r.raise_for_status()


def send_crypto_alert(idea: TradeIdea):
    webhook = settings.crypto_discord_webhook_url
    if settings.dry_run or not webhook:
        print("CRYPTO:", render_text(idea))
        return
    embed = {
        "title": f"🪙 {idea.score:.0f}/100 — {idea.symbol} {idea.direction}",
        "description": f"**ACTION: {_action(idea.status)}**\n**QUALITY: {_crypto_quality(idea.score)}**\n{idea.setup} • 24/7 crypto scanner",
        "color": _color(idea.score),
        "fields": [
            {"name":"Current","value":_crypto_price(idea.current_price),"inline":True},
            {"name":"Entry","value":f"{_crypto_price(idea.entry_low)} – {_crypto_price(idea.entry_high)}","inline":True},
            {"name":"Stop / Invalidation","value":_crypto_price(idea.stop),"inline":True},
            {"name":"Target 1","value":_crypto_price(idea.target1),"inline":True},
            {"name":"Target 2","value":_crypto_price(idea.target2),"inline":True},
            {"name":"R:R (T1 / T2)","value":f"{idea.rr1:.1f}:1 / {idea.rr2:.1f}:1","inline":True},
            {"name":"Technical","value":f"{idea.technical_score:.0f}/100","inline":True},
            {"name":"Momentum","value":f"{idea.momentum_score:.0f}/100","inline":True},
            {"name":"Entry quality","value":f"{idea.entry_location_score:.0f}/100","inline":True},
        ],
        "footer": {"text": "Research signal only — wait for the stated trigger; no crypto order was placed"},
        "timestamp": datetime.utcnow().isoformat(),
    }
    httpx.post(webhook, json={"embeds":[embed]}, timeout=15).raise_for_status()


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
