from __future__ import annotations
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from .btc15 import build_signal
from .config import settings
from .crypto import run_crypto_once
from .discord import send_btc15_alert, send_status
from .pipeline import run_once


def in_scan_window(now: datetime) -> bool:
    return now.weekday() < 5 and (4 <= now.hour < 20)


def main():
    tz = ZoneInfo(settings.timezone)
    send_status("v2 worker started")
    last_equity_run = 0.0
    last_crypto_run = 0.0
    last_btc15_poll = 0.0
    last_btc15_alert_window: str | None = None

    while True:
        now = datetime.now(tz)
        mono = time.monotonic()

        if in_scan_window(now) and mono - last_equity_run >= max(settings.scan_interval_minutes, 1) * 60:
            try:
                ideas = run_once()
                print(f"{now.isoformat()} equity scan complete: {len(ideas)} qualifying ideas")
            except Exception as exc:
                print(f"equity scan failed: {type(exc).__name__}: {exc}")
                send_status(f"equity scan error: `{type(exc).__name__}: {str(exc)[:250]}`")
            finally:
                last_equity_run = mono

        if settings.crypto_enabled and mono - last_crypto_run >= max(settings.crypto_scan_interval_minutes, 1) * 60:
            try:
                crypto_ideas = run_crypto_once()
                print(f"{now.isoformat()} crypto scan complete: {len(crypto_ideas)} qualifying ideas")
            except Exception as exc:
                print(f"crypto scan failed: {type(exc).__name__}: {exc}")
                send_status(f"crypto scan error: `{type(exc).__name__}: {str(exc)[:250]}`")
            finally:
                last_crypto_run = mono

        if settings.btc15_enabled and mono - last_btc15_poll >= max(settings.btc15_poll_seconds, 10):
            try:
                signal = build_signal()
                print(
                    f"{now.isoformat()} BTC15 {signal.direction} {signal.confidence:.1f}% "
                    f"remaining={signal.seconds_remaining}s actionable={signal.actionable}"
                )
                window_key = signal.window_start
                may_alert = (
                    not settings.btc15_alert_once_per_window
                    or window_key != last_btc15_alert_window
                )
                if signal.actionable and may_alert:
                    send_btc15_alert(signal)
                    last_btc15_alert_window = window_key
            except Exception as exc:
                print(f"btc15 monitor failed: {type(exc).__name__}: {exc}")
            finally:
                last_btc15_poll = mono

        # Fast loop for the 15-minute model; equity/crypto are independently throttled above.
        time.sleep(5)


if __name__ == "__main__":
    main()
