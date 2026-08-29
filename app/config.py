from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    discord_webhook_url: str = ""
    crypto_discord_webhook_url: str = ""
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
    crypto_min_entry_score: float = 80

    # Zero-cost default: deterministic market/entry scoring only.
    # Set TRADINGAGENTS_ENABLED=true later if an LLM provider is configured.
    tradingagents_enabled: bool = False
    send_watch_alerts: bool = True
    send_status_alerts: bool = True
    dry_run: bool = False
    timezone: str = "America/New_York"


settings = Settings()
