from __future__ import annotations
import argparse
from urllib.parse import urlsplit
import httpx

from .config import settings
from .crypto import AlpacaCryptoData, run_crypto_once
from .database import init_db
from .discord import send_status
from .market_data import AlpacaMarketData
from .pipeline import run_once


def _database_summary(url: str) -> str:
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or "local"
        db = (parsed.path or "").lstrip("/") or "default"
        scheme = parsed.scheme or "unknown"
        return f"{scheme}://{host}/{db}"
    except Exception:
        return "configured"


def main():
    p = argparse.ArgumentParser(prog="ta-discord")
    p.add_argument(
        "command",
        choices=[
            "doctor", "scan", "crypto-scan", "db-init",
            "discord-test", "crypto-discord-test",
        ],
    )
    args = p.parse_args()
    if args.command == "doctor":
        print("database:", _database_summary(settings.database_url))
        print("alpaca configured:", bool(settings.alpaca_api_key and settings.alpaca_secret_key))
        print("discord configured:", bool(settings.discord_webhook_url))
        print("crypto discord configured:", bool(settings.crypto_discord_webhook_url))
        print("openai configured:", bool(settings.openai_api_key))
        print("tradingagents enabled:", settings.tradingagents_enabled)
        print("crypto enabled:", settings.crypto_enabled)
        if settings.alpaca_api_key:
            md = AlpacaMarketData(); print("equity universe symbols:", len(md.universe()))
            cmd = AlpacaCryptoData(); print("crypto pairs:", len(cmd.universe()))
    elif args.command == "scan":
        for i in run_once()[:20]: print(i.to_dict())
    elif args.command == "crypto-scan":
        for i in run_crypto_once()[:20]: print(i.to_dict())
    elif args.command == "db-init":
        init_db(); print("database initialized")
    elif args.command == "discord-test":
        send_status("Discord webhook test successful")
    elif args.command == "crypto-discord-test":
        if not settings.crypto_discord_webhook_url:
            raise RuntimeError("CRYPTO_DISCORD_WEBHOOK_URL is not configured")
        httpx.post(
            settings.crypto_discord_webhook_url,
            json={"content": "🪙 **Crypto scanner status** — webhook test successful"},
            timeout=15,
        ).raise_for_status()
        print("crypto Discord test sent")


if __name__ == "__main__": main()
