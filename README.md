# TradingAgents Discord Scanner v2

Research-only U.S. equities scanner designed for **Railway + Postgres + Discord**. It does not place orders.

## Pipeline

1. Pull active U.S. equities from Alpaca.
2. Fetch batched full-market snapshots.
3. Filter on price, dollar volume, daily move, and activity.
4. Fetch 5-minute bars only for the top candidates.
5. Calculate EMA9/EMA20, VWAP, RSI, ATR, relative volume, momentum and S/R.
6. Run TradingAgents only on the best technical candidates.
7. Create both pullback and breakout entries.
8. Score each entry 0-100.
9. Persist unique ideas in Postgres/SQLite.
10. Send qualifying ideas to Discord and suppress duplicates.

## Score

- Technical setup: 25%
- Entry location: 25%
- Momentum/volume: 15%
- TradingAgents research: 10%
- Risk/reward: 20%
- Market context placeholder: 5%

Default alert threshold: **80**. High conviction threshold: **90**.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[research,dev]"
cp .env.example .env
# fill in Alpaca/OpenAI/Discord values

ta-discord doctor
ta-discord discord-test
ta-discord scan
```

Run continuously:

```bash
python -m app.worker
```

## Discord webhook

Discord → Server Settings → Integrations → Webhooks → New Webhook. Copy the URL into `DISCORD_WEBHOOK_URL` in Railway Variables. Never commit it.

## Railway deployment

1. Push this folder to a GitHub repository.
2. In Railway, **New Project → Deploy from GitHub repo**.
3. Add a Railway PostgreSQL service.
4. Railway exposes `DATABASE_URL` to the app; if it doesn't, add a reference variable from Postgres.
5. Add variables from `.env.example`:
   - `ALPACA_API_KEY`
   - `ALPACA_SECRET_KEY`
   - `DISCORD_WEBHOOK_URL`
   - `OPENAI_API_KEY`
   - `TRADINGAGENTS_ENABLED=true`
6. Deploy. Railway uses the included Dockerfile and starts `python -m app.worker`.

## First production test

Before allowing alerts, set:

```env
DRY_RUN=true
PREFILTER_LIMIT=20
TECHNICAL_LIMIT=8
RESEARCH_LIMIT=2
```

Check Railway logs for one or two scan cycles. Then set `DRY_RUN=false`.

## Alert behavior

A unique fingerprint consists of symbol + direction + setup + entry zone + coarse score bucket. The same setup won't post every five minutes. A materially different entry/score can produce a new alert.

## Safety / scope

This application produces research signals only. It has no broker-order module. `Suggested shares` is derived from `MAX_RISK_DOLLARS` and modeled stop distance; it is not an instruction to trade.
