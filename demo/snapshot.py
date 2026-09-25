"""Take one snapshot of the live catalogue and write it where the page can render it.

Separated from the page on purpose: the snapshot needs an API key and a Solana endpoint, the page
needs neither. Nothing that runs in a browser ever sees a credential, and the published page is a
file, not a service.

    .venv/bin/python demo/snapshot.py --cards 40 --settlements 12
"""
import argparse
import dataclasses
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from settlementcheck import chain, classify, panta  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "snapshot.json"


def collect(cards_wanted, settlements):
    listed = panta.markets()
    rank = {"primary": 0, "secondary": 1, "resolved": 2, "cancelled": 3}
    listed.sort(key=lambda m: rank.get(m.get("phase"), 4))
    cards = []
    for row in listed[:cards_wanted]:
        card = panta.market(row["marketId"])
        for field in ("totalVolumeUsdc", "volumeUsdc"):
            if float(row.get(field) or 0) > float(card.get(field) or 0):
                card[field] = row[field]
        card.setdefault("phase", row.get("phase"))
        cards.append(card)
        time.sleep(0.1)

    # Spend the settlement budget on markets that can answer: one still trading has not settled.
    order = sorted(cards, key=lambda c: (c.get("phase") in ("primary", "secondary")))
    found = {}
    for card in order[:settlements]:
        try:
            found[card["marketId"]] = chain.settlement(card["marketId"])
        except chain.ChainError:
            pass
    settlement_of = lambda mid: found.get(mid, classify.NOT_LOOKED)  # noqa: E731

    return [classify.judge(card, chain.account_owner, chain.looks_like_address, settlement_of)
            for card in cards]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cards", type=int, default=40)
    parser.add_argument("--settlements", type=int, default=12)
    args = parser.parse_args()

    verdicts = collect(args.cards, args.settlements)
    rows = []
    for verdict in verdicts:
        row = dataclasses.asdict(verdict)
        row["settled_by"] = list(verdict.settled_by)
        row["settlement_seen"] = list(verdict.settlement_seen)
        row["claim_versus_chain"] = verdict.claim_versus_chain
        rows.append(row)

    tradeable = [v for v in verdicts if v.tradeable]
    settled = [v for v in verdicts if not v.tradeable]
    mute = lambda group: sum(1 for v in group if v.kind == classify.UNSTATED)  # noqa: E731
    payload = {
        "taken_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "counts": {
            "markets": len(verdicts),
            "tradeable": len(tradeable),
            "tradeable_unstated": mute(tradeable),
            "settled": len(settled),
            "settled_unstated": mute(settled),
            "settlements_read": sum(1 for v in verdicts if v.settled_by),
            "claims_uma": sum(1 for v in verdicts if v.claims_uma),
        },
        "settlers": sorted({address for v in verdicts for address in v.settled_by}),
        "markets": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} — {payload['counts']}")


if __name__ == "__main__":
    main()
