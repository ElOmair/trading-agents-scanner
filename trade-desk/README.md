# Hanif Trade Desk

A snapshot-based chart and order-review workspace. This version does not run a live broker connection or submit orders.

## Working features

- Interactive 15-minute underlying candles with EMA 9/21, session VWAP, Wilder RSI/ATR and the first regular-session 15-minute opening range.
- Unusual Whales call wall, put wall and gamma flip overlays, labeled by snapshot date.
- Imported equity and option executions. Option markers indicate execution time on the underlying chart, not the stock's price at fill or the option's price history. The fill list retains every execution.
- Actual imported OCC contracts with expiry, bid/ask, Greeks, IV and quote timestamps. Available expirations are filtered by current New York calendar date, not fabricated from today plus N days.
- Stock and long-option sizing with zero allowed. Options use the entire premium as risk and a spend cap. Fees, portfolio exposure and live buying power require broker revalidation.
- Copy an explicit REVIEW ONLY request to ChatGPT / RobinAI. No approval, execution, credential handling, watchlist mutations or Discord messages occur in this page.
- Import/export versioned snapshots. An import lives in page memory; reload restores the packaged snapshot. No browser credential storage.

## Connector responsibilities

| Provider | Current use | Boundary |
|---|---|---|
| Alpaca connector | Historical bars and option chain snapshots | Exposed connector is data-only; it is not Alpaca's Trading API |
| Unusual Whales | Provider-calculated GEX levels | Flow and walls are context, not proof of directional intent |
| RobinAI | Account eligibility, actual fills, review handoff | Refresh accounts/quotes/funds before a trade; submit only under an explicit authorized workflow |
| GitHub | Source changes and review | Existing scanner runtime remains research-only |

Connecting a provider in ChatGPT does not give an external website its credentials or a permanent stream. This first version is refreshed by the agent through connector tools, then snapshot import or a private Site version update. Continuous operation requires a separately authenticated backend and data entitlements. Do not send browser code to undocumented broker endpoints or embed chat connector tokens.

## Running the chart

Serve `dist` with any static HTTP server. Open `index.html` over HTTP, not file://, because snapshots are fetched. There is no package installation or JavaScript build. Chart library version: TradingView Lightweight Charts 5.0.8, Apache-2.0, with bundled license and attribution.

```sh
python -m http.server 8000 --directory dist
node test-engine.js
```

No account data should be committed to a public GitHub repository. The private Site package has its own owner-only snapshot. The public source includes an empty snapshot; import a private snapshot to use it.

## Snapshot contract

Root fields: `schemaVersion: 1`, `capturedAt` ISO timestamp, `timeframe: "15Min"`, `feed`, `bars`, `gex`, `contracts`, `fills`, optional `market`, `fillScope` and masked `account.label`.

`bars` maps uppercase symbols to strictly increasing OHLCV rows: `timestamp`, `open`, `high`, `low`, `close`, `volume`, optional volume-weighted bar `vwap`. Use complete ascending, deduplicated bars. The UI filters regular trading hours in New York time, removes unfinished bars using the capture time, and never invents missing IEX bars. IEX volumes and indicators differ from consolidated SIP. Fewer than 22 valid bars yields no price map.

`gex` maps symbols to the unmodified `get_gex_levels` object, including `date`, `time`, `source`, `call_wall`, `put_wall`, `gamma_flip`. Do not derive provider walls from arbitrary strike gamma rows. Treat missing data as missing.

`contracts` rows: `symbol` (OCC), `underlying`, `type` (`call`/`put`), `strike`, `expiry` (YYYY-MM-DD), `bid`, `ask`, `quoteTime`, `feed`, `iv`, `delta`, `theta`, `multiplier`, `openInterest`, `volume`. Numeric unavailable values must be null. Do not call indicative data real-time or executable. Confirm multiplier and deliverable eligibility in the broker before sizing a real order.

`fills` rows: `id`, `underlying`, `asset` (`stock`/`option`), `side`, `quantity`, `price`, `time`; options add `type`, `strike`, `expiry`, `multiplier`, `positionEffect`. Price is the actual per-unit fill price; options are quoted premium, and debit is premium × multiplier × quantity. Preserve per-execution times; never use order creation time as an actual fill timestamp. An incomplete imported time window is not a positions ledger or performance report.

## Refresh procedure

1. Read account eligibility through RobinAI; choose the explicitly requested account, or follow the tool's account selection requirements. Mask identifiers in output. Do not infer permission from a nickname.
2. Fetch Alpaca market clock and 15-minute bars for watched symbols and symbols in recent fills. Disclose feed. Follow pagination and sort/deduplicate bars.
3. Fetch actual option contracts and snapshot quotes for the requested DTE range, and UW GEX levels for each symbol. Preserve timestamps and unavailable fields.
4. Fetch RobinAI equity and option orders for the specified account/time range. Follow all returned cursors. Normalize executions only, not open order instructions.
5. Build a version 1 snapshot, validate it with `TradeEngine.validate`, and import it or update the existing private Site. Keep portfolio data out of public GitHub branches.
6. On a proposed trade, refresh executable quotes, funds, current account eligibility, approval levels, spread, liquidity, expiration, multiplier and fees. Recompute size. If it is zero, there is no trade. Review and any later placement use the native broker tools and their current requirements.

## Validation and limitations

Node assertions cover risk caps, zero sizing, prior-candle breakout levels, flat RSI, VWAP session reset, daylight-saving time and invalid imports. Static JavaScript and asset references are checked. Browser/WebMCP runtime testing was unavailable in this build context; no automated execution is claimed.

Pine Script does not run in this workspace. EMA/ATR concepts are implemented in JavaScript. The stock-volatility calculation is not implied volatility. Underlying stock stop/target levels do not predict an option's stop/target premium. A stop can gap or slip. No historical outcome or win rate is asserted.
