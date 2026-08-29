from datetime import datetime, timezone
import pandas as pd
from app.outcomes import evaluate_idea

BASE={"entry_low":99.5,"entry_high":100.5,"stop":98,"target1":102,"target2":104,"direction":"LONG"}

def bars(rows):
    return pd.DataFrame(rows, columns=["timestamp","open","high","low","close","volume"])

def test_no_entry_not_counted():
    now=datetime.now(timezone.utc)
    df=bars([[pd.Timestamp(now),101,101.5,100.8,101,1000]])
    assert evaluate_idea(BASE,now,df,max_age_hours=999) is None

def test_target_after_entry():
    now=datetime.now(timezone.utc)
    df=bars([
      [pd.Timestamp(now),101,101.2,99.8,100.2,1000],
      [pd.Timestamp(now)+pd.Timedelta(minutes=5),100.2,102.2,99.9,102,1000],
    ])
    assert evaluate_idea(BASE,now,df) == "T1"

def test_same_bar_stop_target_ambiguous():
    now=datetime.now(timezone.utc)
    df=bars([[pd.Timestamp(now),100,102.5,97.5,100,1000]])
    assert evaluate_idea(BASE,now,df) == "AMBIGUOUS"
