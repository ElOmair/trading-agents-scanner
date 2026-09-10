from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math

import httpx
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings
from .database import engine
from .discord import send_meme_alert


SUPPORTED_CHAINS = {
    "solana",
    "ethereum",
    "base",
    "bsc",
    "monad",
}


@dataclass
class MemeIdea:
    chain: str
    symbol: str
    name: str
    token_address: str
    pair_address: str
    pair_url: str
    dex: str
    price_usd: float
    liquidity_usd: float
    volume_1h: float
    volume_24h: float
    buys_1h: int
    sells_1h: int
    change_1h_pct: float
    change_24h_pct: float
    pair_age_hours: float
    score: float
    quality: str
    action: str
    suggested_dollars: float
    stop_pct: float
    target1_pct: float
    target2_pct: float
    warnings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


class DexScreenerData:
    base_url = "https://api.dexscreener.com"

    def __init__(self):
        self.client = httpx.Client(
            timeout=30.0,
            headers={"User-Agent": "trading-agents-scanner/2.1"},
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def candidate_addresses(self) -> list[tuple[str, str]]:
        rows: list[dict] = []
        for endpoint in ("/token-profiles/latest/v1", "/token-boosts/top/v1"):
            response = self.client.get(f"{self.base_url}{endpoint}")
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list):
                rows.extend(payload)

        found: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for row in rows:
            chain = str(row.get("chainId") or "").lower()
            address = str(row.get("tokenAddress") or "")
            key = (chain, address)
            if chain in SUPPORTED_CHAINS and address and key not in seen:
                found.append(key)
                seen.add(key)
        return found[: settings.meme_candidate_limit]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def token_pairs(self, chain: str, address: str) -> list[dict]:
        response = self.client.get(
            f"{self.base_url}/token-pairs/v1/{chain}/{address}"
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []


def _number(value, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def _pair_age_hours(created_at_ms) -> float:
    created = _number(created_at_ms)
    if created <= 0:
        return 9999.0
    age_seconds = datetime.now(timezone.utc).timestamp() - created / 1000
    return max(age_seconds / 3600, 0.0)


def _score_pair(pair: dict, token_address: str) -> MemeIdea | None:
    base = pair.get("baseToken") or {}
    quote = pair.get("quoteToken") or {}
    base_address = str(base.get("address") or "")
    token = base if base_address.lower() == token_address.lower() else quote
    if not token.get("address"):
        return None

    liquidity = _number((pair.get("liquidity") or {}).get("usd"))
    volume = pair.get("volume") or {}
    txns = pair.get("txns") or {}
    changes = pair.get("priceChange") or {}
    h1 = txns.get("h1") or {}
    buys = int(_number(h1.get("buys")))
    sells = int(_number(h1.get("sells")))
    volume_1h = _number(volume.get("h1"))
    volume_24h = _number(volume.get("h24"))
    change_1h = _number(changes.get("h1"))
    change_24h = _number(changes.get("h24"))
    age_hours = _pair_age_hours(pair.get("pairCreatedAt"))

    if liquidity < settings.meme_min_liquidity_usd:
        return None
    if volume_1h < settings.meme_min_volume_1h_usd:
        return None
    if buys + sells < settings.meme_min_txns_1h:
        return None

    liquidity_score = min(25.0, 25 * liquidity / 250_000)
    volume_score = min(20.0, 20 * volume_1h / 150_000)
    activity_score = min(15.0, 15 * (buys + sells) / 300)
    buy_ratio = buys / max(buys + sells, 1)
    flow_score = max(0.0, min(15.0, (buy_ratio - 0.40) * 75))
    momentum_score = max(0.0, min(15.0, 7.5 + change_1h / 4))
    age_score = 10.0 if 6 <= age_hours <= 720 else (5.0 if age_hours > 1 else 0.0)
    score = round(
        liquidity_score + volume_score + activity_score
        + flow_score + momentum_score + age_score,
        1,
    )

    warnings: list[str] = []
    if age_hours < 6:
        warnings.append("Pair is under 6 hours old")
    if liquidity < 100_000:
        warnings.append("Liquidity is below $100K")
    if change_1h > 60:
        warnings.append("Price already ran more than 60% in 1h")
    if sells and buys / sells < 1.1:
        warnings.append("Buy/sell flow is weak")
    if not warnings:
        warnings.append("Contract and holder audit still required in Fomo")

    if score >= settings.meme_high_conviction_score and not any(
        "already ran" in warning or "under 6" in warning for warning in warnings
    ):
        quality, action = "A", "ENTER SMALL"
        suggested = settings.meme_a_size_dollars
    elif score >= settings.meme_min_alert_score:
        quality, action = "B+", "WATCH / WAIT FOR RETEST"
        suggested = settings.meme_b_size_dollars
    else:
        quality, action = "WATCH", "DO NOT ENTER YET"
        suggested = 0.0

    return MemeIdea(
        chain=str(pair.get("chainId") or ""),
        symbol=str(token.get("symbol") or "UNKNOWN"),
        name=str(token.get("name") or "Unknown token"),
        token_address=str(token.get("address") or ""),
        pair_address=str(pair.get("pairAddress") or ""),
        pair_url=str(pair.get("url") or ""),
        dex=str(pair.get("dexId") or ""),
        price_usd=_number(pair.get("priceUsd")),
        liquidity_usd=liquidity,
        volume_1h=volume_1h,
        volume_24h=volume_24h,
        buys_1h=buys,
        sells_1h=sells,
        change_1h_pct=change_1h,
        change_24h_pct=change_24h,
        pair_age_hours=age_hours,
        score=score,
        quality=quality,
        action=action,
        suggested_dollars=suggested,
        stop_pct=settings.meme_stop_pct,
        target1_pct=settings.meme_target1_pct,
        target2_pct=settings.meme_target2_pct,
        warnings=warnings,
    )


def scan_meme_candidates() -> list[MemeIdea]:
    data = DexScreenerData()
    ideas: list[MemeIdea] = []
    for chain, address in data.candidate_addresses():
        pairs = data.token_pairs(chain, address)
        if not pairs:
            continue
        pair = max(
            pairs,
            key=lambda item: _number((item.get("liquidity") or {}).get("usd")),
        )
        idea = _score_pair(pair, address)
        if idea and idea.score >= settings.meme_min_alert_score:
            ideas.append(idea)
    ideas.sort(key=lambda item: item.score, reverse=True)
    return ideas[: settings.meme_alert_limit]


def _init_table() -> None:
    with engine.begin() as connection:
        connection.execute(text(
            """
            CREATE TABLE IF NOT EXISTS meme_alerts (
              fingerprint VARCHAR(255) PRIMARY KEY,
              token_address VARCHAR(255) NOT NULL,
              created_at TIMESTAMP NOT NULL,
              score DOUBLE PRECISION NOT NULL,
              payload TEXT NOT NULL
            )
            """ if engine.dialect.name == "postgresql" else """
            CREATE TABLE IF NOT EXISTS meme_alerts (
              fingerprint TEXT PRIMARY KEY,
              token_address TEXT NOT NULL,
              created_at TEXT NOT NULL,
              score REAL NOT NULL,
              payload TEXT NOT NULL
            )
            """
        ))


def _save_new(idea: MemeIdea) -> bool:
    raw = f"{idea.chain}:{idea.token_address}:{int(idea.score // 5)}"
    fingerprint = hashlib.sha256(raw.encode()).hexdigest()
    with engine.begin() as connection:
        existing = connection.execute(
            text("SELECT fingerprint FROM meme_alerts WHERE fingerprint=:fp"),
            {"fp": fingerprint},
        ).fetchone()
        if existing:
            return False
        connection.execute(
            text(
                "INSERT INTO meme_alerts(fingerprint,token_address,created_at,score,payload) "
                "VALUES(:fp,:address,:created,:score,:payload)"
            ),
            {
                "fp": fingerprint,
                "address": idea.token_address,
                "created": datetime.now(timezone.utc),
                "score": idea.score,
                "payload": json.dumps(idea.to_dict()),
            },
        )
    return True


def run_meme_once() -> list[MemeIdea]:
    _init_table()
    ideas = scan_meme_candidates()
    for idea in ideas:
        if _save_new(idea):
            send_meme_alert(idea)
    return ideas
