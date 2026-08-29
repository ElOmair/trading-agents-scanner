from app.models import ResearchResult, TechnicalSnapshot
from app.scoring import make_ideas


def snap(direction="LONG"):
    return TechnicalSnapshot("TEST",100,99.5,98.5,99.2,58,2,1.8,0.7,96,103,90,direction)


def test_generates_two_ideas():
    out = make_ideas(snap(), ResearchResult("TEST","Buy",95,"ok"))
    assert len(out) == 2
    assert {x.setup for x in out} == {"PULLBACK","BREAKOUT"}


def test_conflicting_research_penalized():
    good = make_ideas(snap(), ResearchResult("TEST","Buy",95,""))[0]
    bad = make_ideas(snap(), ResearchResult("TEST","Sell",95,""))[0]
    assert good.score > bad.score


def test_short_geometry():
    out = make_ideas(snap("SHORT"), ResearchResult("TEST","Sell",95,""))
    for i in out:
        assert i.stop > (i.entry_low+i.entry_high)/2
        assert i.target2 < (i.entry_low+i.entry_high)/2
