from __future__ import annotations
import argparse
from urllib.parse import urlsplit
from .config import settings
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
    p.add_argument("command", choices=["doctor", "scan", "db-init", "discord-test"])
    args = p.parse_args()
    if args.command == "doctor":
        print("database:", _database_summary(settings.database_url))
        print("alpaca configured:", bool(settings.alpaca_api_key and settings.alpaca_secret_key))
        print("discord configured:", bool(settings.discord_webhook_url))
        print("openai configured:", bool(settings.openai_api_key))
        print("tradingagents enabled:", settings.tradingagents_enabled)
        if settings.alpaca_api_key:
            md = AlpacaMarketData(); print("universe symbols:", len(md.universe()))
    elif args.command == "scan":
        for i in run_once()[:20]: print(i.to_dict())
    elif args.command == "db-init": init_db(); print("database initialized")
    elif args.command == "discord-test": send_status("Discord webhook test successful")


if __name__ == "__main__": main()
