from __future__ import annotations
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import settings
from .crypto import run_crypto_once
from .discord import send_status
from .pipeline import run_once


def in_scan_window(now: datetime) -> bool:
    return now.weekday() < 5 and (4 <= now.hour < 20)


def main():
    tz = ZoneInfo(settings.timezone)
    send_status("v2 worker started")
    last_crypto_run = 0.0
    while True:
        now = datetime.now(tz)
        try:
            if in_scan_window(now):
                ideas = run_once()
                print(f"{now.isoformat()} equity scan complete: {len(ideas)} qualifying ideas")
            else:
                print(f"{now.isoformat()} equities outside scan window")
        except Exception as exc:
            print(f"equity scan failed: {type(exc).__name__}: {exc}")
            send_status(f"equity scan error: `{type(exc).__name__}: {str(exc)[:250]}`")

        if settings.crypto_enabled:
            elapsed = time.monotonic() - last_crypto_run
            if elapsed >= max(settings.crypto_scan_interval_minutes, 1) * 60:
                try:
                    crypto_ideas = run_crypto_once()
                    print(f"{now.isoformat()} crypto scan complete: {len(crypto_ideas)} qualifying ideas")
                except Exception as exc:
                    print(f"crypto scan failed: {type(exc).__name__}: {exc}")
                    send_status(f"crypto scan error: `{type(exc).__name__}: {str(exc)[:250]}`")
                finally:
                    last_crypto_run = time.monotonic()

        time.sleep(max(settings.scan_interval_minutes, 1) * 60)


if __name__ == "__main__":
    main()
