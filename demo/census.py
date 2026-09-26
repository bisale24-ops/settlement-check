"""The measurement behind every number in the README, so none of them is typed by hand.

Reads the whole catalogue the API will hand over, opens each market's own card, and prints the
two populations apart. Run it yourself: `.venv/bin/python demo/census.py`.
"""
import collections
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from settlementcheck import chain, classify, panta  # noqa: E402


def main():
    rows = panta.markets()
    verdicts, from_card, from_list = [], 0, 0
    for row in rows:
        card = panta.market(row["marketId"])
        for field in ("totalVolumeUsdc", "volumeUsdc"):
            if float(row.get(field) or 0) > float(card.get(field) or 0):
                card[field] = row[field]
        card.setdefault("phase", row.get("phase"))
        from_card += bool((card.get("title") or "").strip())
        from_list += bool((row.get("title") or "").strip())
        verdicts.append(classify.judge(card, lambda _a: None, chain.looks_like_address))
        time.sleep(0.1)

    n = len(verdicts)
    print(f"catalogue rows the API will hand over: {n}")
    print(f"  question present in the LISTING row title : {from_list}")
    print(f"  question present in the CARD title        : {from_card}")

    print(f"\n{'population':12} {'markets':>7} {'no question':>12} {'volume':>12} {'on silent':>12}")
    for name, want in (("tradeable", True), ("settled", False)):
        part = [v for v in verdicts if v.tradeable is want]
        if not part:
            continue
        mute = [v for v in part if v.kind == classify.UNSTATED]
        vol = sum(v.volume or 0 for v in part)
        mvol = sum(v.volume or 0 for v in mute)
        pct = round(100 * len(mute) / len(part))
        print(f"{name:12} {len(part):7} {f'{len(mute)} ({pct}%)':>12} ${vol:>11,.0f} ${mvol:>11,.0f}")

    kinds = collections.Counter(v.kind for v in verdicts)
    print("\nverdicts (on-chain lookups skipped here; the CLI does them):")
    for kind in classify.ORDER:
        vol = sum(v.volume or 0 for v in verdicts if v.kind == kind)
        print(f"  {kind:14} {kinds[kind]:3}  ${vol:,.0f}")

    print("\nvolume against the market's own history "
          "(complete histories only — a truncated one proves nothing):")
    silent = silent_volume = checked = unknown = 0
    for verdict in verdicts:
        traded = chain.traded_on_chain(verdict.market_id)
        if traded is None:
            unknown += 1
            continue
        checked += 1
        if not traded and (verdict.volume or 0) > 0:
            silent += 1
            silent_volume += verdict.volume
    print(f"  histories read in full : {checked}   too long to read: {unknown}")
    print(f"  never had an order here but report volume: {silent}")
    print(f"  volume riding on those: ${silent_volume:,.0f}")

    oracles = collections.Counter((v.oracle or "(empty)") for v in verdicts)
    print("\nmost common settlement sources:")
    for value, count in oracles.most_common(5):
        print(f"  {count:3}  {value[:80]}")


if __name__ == "__main__":
    main()
