from app.meme import _score_pair


def test_scores_liquid_active_pair():
    pair = {
        "chainId": "solana",
        "dexId": "raydium",
        "url": "https://dexscreener.com/solana/pair",
        "pairAddress": "pair",
        "pairCreatedAt": 1,
        "baseToken": {"address": "token", "symbol": "MEME", "name": "Meme"},
        "quoteToken": {"address": "quote", "symbol": "SOL", "name": "Solana"},
        "priceUsd": "0.001",
        "liquidity": {"usd": 250000},
        "volume": {"h1": 150000, "h24": 900000},
        "txns": {"h1": {"buys": 220, "sells": 80}},
        "priceChange": {"h1": 12, "h24": 40},
    }
    idea = _score_pair(pair, "token")
    assert idea is not None
    assert idea.score >= 75
    assert idea.token_address == "token"
    assert idea.suggested_dollars > 0


def test_rejects_thin_liquidity():
    pair = {
        "chainId": "solana",
        "baseToken": {"address": "token", "symbol": "MEME", "name": "Meme"},
        "quoteToken": {"address": "quote", "symbol": "SOL", "name": "Solana"},
        "liquidity": {"usd": 1000},
        "volume": {"h1": 100000},
        "txns": {"h1": {"buys": 100, "sells": 20}},
    }
    assert _score_pair(pair, "token") is None
