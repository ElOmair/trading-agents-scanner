import pandas as pd
from app.scanner import analyze_symbol


def test_analyze_symbol():
    n=40
    df=pd.DataFrame({
      "timestamp":pd.date_range("2026-08-28 13:30",periods=n,freq="5min",tz="UTC"),
      "open":[100+i*.1 for i in range(n)],
      "high":[100.4+i*.1 for i in range(n)],
      "low":[99.7+i*.1 for i in range(n)],
      "close":[100.2+i*.1 for i in range(n)],
      "volume":[1000+i*10 for i in range(n)],
    })
    x=analyze_symbol("TEST",df)
    assert x is not None
    assert 0 <= x.technical_score <= 100
