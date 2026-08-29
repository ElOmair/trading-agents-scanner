from __future__ import annotations
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from .config import settings
from .discord import send_status
from .pipeline import run_once


def in_scan_window(now: datetime) -> bool:
    return now.weekday() < 5 and (4 <= now.hour < 20)


def main():
    tz = ZoneInfo(settings.timezone)
    send_status("v2 worker started")
    while True:
        now = datetime.now(tz)
        try:
            if in_scan_window(now):
                ideas = run_once()
                print(f"{now.isoformat()} scan complete: {len(ideas)} qualifying ideas")
            else:
                print(f"{now.isoformat()} outside scan window")
        except Exception as exc:
            print(f"scan failed: {type(exc).__name__}: {exc}")
            send_status(f"scan error: `{type(exc).__name__}: {str(exc)[:250]}`")
        time.sleep(max(settings.scan_interval_minutes, 1) * 60)


if __name__ == "__main__":
    main()
