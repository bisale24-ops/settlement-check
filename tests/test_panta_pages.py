"""markets() must follow a working cursor and must not loop on a cursor that repeats rows."""
from settlementcheck import panta


def run(monkeypatch, pages_by_cursor):
    calls = []

    def fake_page(limit=50, status="", cursor=None):
        calls.append((status, cursor))
        return pages_by_cursor.get((status, cursor), ([], None))
    monkeypatch.setattr(panta, "page", fake_page)
    monkeypatch.setattr(panta.time, "sleep", lambda _s: None)
    return panta.markets(slices=("",)), calls


def rows(*ids):
    return [{"marketId": i} for i in ids]


def test_follows_an_advancing_cursor(monkeypatch):
    out, _ = run(monkeypatch, {("", None): (rows("a", "b"), "c1"), ("", "c1"): (rows("c"), None)})
    assert [r["marketId"] for r in out] == ["a", "b", "c"]


def test_stops_when_the_cursor_brings_the_same_rows_back(monkeypatch):
    out, calls = run(monkeypatch, {("", None): (rows("a", "b"), "c1"), ("", "c1"): (rows("a", "b"), "c1")})
    assert [r["marketId"] for r in out] == ["a", "b"]
    assert len(calls) == 2
