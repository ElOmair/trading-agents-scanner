from __future__ import annotations
from datetime import datetime, timezone
import json
import pandas as pd
from .database import record_outcome, unresolved_ideas
from .discord import send_outcome

TERMINAL = {"STOP", "T1", "T2", "AMBIGUOUS", "NO_ENTRY_EXPIRED"}


def evaluate_idea(payload: dict, created_at: datetime, bars: pd.DataFrame, max_age_hours: int = 48) -> str | None:
    if bars is None or bars.empty:
        return None
    created = pd.Timestamp(created_at)
    if created.tzinfo is None:
        created = created.tz_localize("UTC")
    else:
        created = created.tz_convert("UTC")
    d = bars[bars.timestamp >= created].copy()
    if d.empty:
        return None
    low, high = float(payload["entry_low"]), float(payload["entry_high"])
    stop, t1, t2 = float(payload["stop"]), float(payload["target1"]), float(payload["target2"])
    direction = payload["direction"]
    entered = False
    for _, b in d.iterrows():
        if not entered:
            entered = float(b.low) <= high and float(b.high) >= low
            if not entered:
                continue
        if direction == "LONG":
            hit_stop = float(b.low) <= stop
            hit_t1 = float(b.high) >= t1
            hit_t2 = float(b.high) >= t2
        else:
            hit_stop = float(b.high) >= stop
            hit_t1 = float(b.low) <= t1
            hit_t2 = float(b.low) <= t2
        if hit_stop and (hit_t1 or hit_t2):
            return "AMBIGUOUS"
        if hit_t2:
            return "T2"
        if hit_t1:
            return "T1"
        if hit_stop:
            return "STOP"
    age_hours = (datetime.now(timezone.utc) - created.to_pydatetime()).total_seconds() / 3600
    if not entered and age_hours >= max_age_hours:
        return "NO_ENTRY_EXPIRED"
    return None


def resolve_outcomes(market_data) -> int:
    rows = unresolved_ideas()
    if not rows:
        return 0
    parsed = []
    symbols = set()
    for fp, created_at, payload in rows:
        p = json.loads(payload)
        parsed.append((fp, created_at, p))
        symbols.add(p["symbol"])
    bars_map = market_data.bars_5m(symbols, lookback_hours=72)
    resolved = 0
    for fp, created_at, payload in parsed:
        outcome = evaluate_idea(payload, created_at, bars_map.get(payload["symbol"]))
        if outcome in TERMINAL:
            record_outcome(fp, outcome)
            send_outcome(payload["symbol"], outcome, fp)
            resolved += 1
    return resolved
