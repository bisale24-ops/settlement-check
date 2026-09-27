"""Write docs/catalogue.json: the Panta catalogue with everything a buyer cannot read taken out.

The report says what is wrong with the catalogue. This is the other half — the part a client can
consume. A market stays in only if all three hold:

  * the catalogue serves it as tradeable (`primary` or `secondary`);
  * a Solana account exists at its id, so it can actually be traded;
  * the card arrived complete — a question and a resolution rule a buyer can read.

Everything else is counted, by reason, so the file says what it left out and why rather than
silently shrinking. Read-only: the catalogue, the card, one `getAccountInfo` per market.

    ./run.sh is not needed — `python3 demo/catalogue.py` with a Panta key in the usual place.
"""
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from settlementcheck import chain, classify, panta  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "catalogue.json"
TRADEABLE = ("primary", "secondary")


def sources_of(card):
    raw = card.get("sources") or card.get("sourcesOfTruth") or card.get("oracle") or ""
    if isinstance(raw, str):
        return [s.strip() for s in raw.split(",") if s.strip()]
    return [str(s).strip() for s in raw if str(s).strip()]


def clean(rows, account_owner=chain.account_owner, card_of=panta.market, sleep=time.sleep):
    kept, left_out = [], {"not tradeable": 0, "no account on chain": 0, "card stripped": 0}
    for row in rows:
        market_id = row["marketId"]
        if row.get("phase") not in TRADEABLE:
            left_out["not tradeable"] += 1
            continue
        if account_owner(market_id) is None:
            left_out["no account on chain"] += 1
            continue
        card = card_of(market_id)
        sleep(0.1)
        if classify.is_stripped(card):
            left_out["card stripped"] += 1
            continue
        kept.append({
            "marketId": market_id,
            "question": classify.stated_question(card),
            "resolutionRule": classify.stated_rule(card),
            "sources": sources_of(card),
            "phase": row.get("phase"),
            "endTime": card.get("endTime") or row.get("endTime"),
            "url": f"https://panta.market/market/{market_id}",
        })
    return kept, left_out


def listing(passes=4, sleep=time.sleep):
    """Several reads of the catalogue, merged.

    Each `GET /markets/` hands back a different slice (three passes minutes apart returned 40, 50
    and 17 tradeable markets out of 100), so one read is not the catalogue. Merging a few gets
    closer to it, and the file records how many rows that produced.
    """
    found = {}
    for _ in range(passes):
        for row in panta.markets():
            found.setdefault(row["marketId"], row)
        sleep(1.0)
    return list(found.values())


def main():
    rows = listing()
    kept, left_out = clean(rows)
    payload = {
        "taken_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "GET /markets/ and GET /markets/{id}/ on live-api.panta.market, "
                  "getAccountInfo on Solana mainnet",
        "rule": "tradeable phase, an account on chain, and a card carrying a question and a rule",
        "read": len(rows),
        "kept": len(kept),
        "left_out": left_out,
        "markets": kept,
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(rows)} read, {len(kept)} kept, left out: "
          + ", ".join(f"{v} {k}" for k, v in left_out.items()) + f" -> {OUT}")


if __name__ == "__main__":
    main()
