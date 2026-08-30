from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    discord_webhook_url: str = ""
    crypto_discord_webhook_url: str = ""
    btc15_discord_webhook_url: str = ""
    openai_api_key: str = ""
    database_url: str = "sqlite:///./scanner.db"

    min_price: float = 5.0
    min_dollar_volume: float = 5_000_000
    prefilter_limit: int = 60
    technical_limit: int = 20
    research_limit: int = 8
    min_entry_score: float = 80
    high_conviction_score: float = 90
    scan_interval_minutes: int = 5
    research_cache_minutes: int = 30
    max_risk_dollars: float = 100

    # Crypto runs continuously and uses the same deterministic indicators/scorer.
    crypto_enabled: bool = True
    crypto_scan_interval_minutes: int = 5
    crypto_technical_limit: int = 20
    crypto_min_entry_score: float = 75
    crypto_min_technical_score: float = 65
    crypto_high_conviction_score: float = 80

    # BTC 15-minute prediction research. BRTI is the settlement benchmark, but the
    # public CF Benchmarks web page must not be scraped. This engine uses Alpaca
    # BTC/USD as a live proxy unless an official/licensed benchmark feed is added.
    btc15_enabled: bool = True
    btc15_poll_seconds: int = 30
    btc15_min_confidence: float = 64
    btc15_min_edge: float = 0.05
    btc15_min_seconds_remaining: int = 90
    btc15_max_seconds_remaining: int = 600
    btc15_alert_once_per_window: bool = True
    btc15_max_risk_dollars: float = 10.0
    btc15_exit_probability: float = 0.55
    btc15_take_profit_discount_cents: float = 2.0

    # Zero-cost default: deterministic market/entry scoring only.
    # Set TRADINGAGENTS_ENABLED=true later if an LLM provider is configured.
    tradingagents_enabled: bool = False
    send_watch_alerts: bool = True
    send_status_alerts: bool = True
    dry_run: bool = False
    timezone: str = "America/New_York"


settings = Settings()
