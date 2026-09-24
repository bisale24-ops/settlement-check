"""settlement-check — what decides this market, and could anyone else have checked it?"""
import argparse
import sys

from . import chain, classify, panta, report


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="settlement-check", description=__doc__)
    parser.add_argument("--pages", type=int, default=2, help="catalogue pages to read (50 each)")
    parser.add_argument("--cards", type=int, default=40, help="how many full cards to open")
    parser.add_argument("--tradeable-first", action="store_true", default=True,
                        help="open cards for tradeable markets before settled ones")
    parser.add_argument("--show", type=int, default=6, help="entries printed per group")
    parser.add_argument("--no-chain", action="store_true",
                        help="skip on-chain lookups; every address-shaped oracle stays unknown")
    return parser.parse_args(argv)


def collect(args):
    listed = panta.markets(limit=50, pages=args.pages)
    rank = {"primary": 0, "secondary": 1, "resolved": 2, "cancelled": 3}
    if args.tradeable_first:
        listed.sort(key=lambda m: rank.get(m.get("phase"), 4))
    cards = []
    for row in listed[:args.cards]:
        card = panta.market(row["marketId"])
        # The list row and the card do not agree on volume: the card reports `primaryVolume`
        # only, while the row carries the settled total. Keep the row's figures so the money in
        # the report is the money the catalogue advertises.
        # Overwrite rather than fill in: the card reports 0 for markets the list row shows
        # volume on, and a present zero would win a setdefault.
        for field in ("totalVolumeUsdc", "volumeUsdc"):
            if float(row.get(field) or 0) > float(card.get(field) or 0):
                card[field] = row[field]
        card.setdefault("phase", row.get("phase"))
        cards.append(card)
    return cards


def settler_facts(verdicts):
    """For every wallet that settles a market here, what it controls and what it calls."""
    facts = {}
    for address in {v.oracle for v in verdicts if v.kind == classify.ONE_KEY}:
        theirs = [v for v in verdicts if v.oracle == address]
        signatures = chain.recent_signatures(address, 25)
        programs = chain.programs_touched(signatures[0]["signature"]) if signatures else set()
        facts[address] = {"markets": len(theirs), "volume": sum(v.volume for v in theirs),
                          "signatures": len(signatures), "programs": programs}
    return facts


def main(argv=None):
    args = parse_args(argv)
    try:
        cards = collect(args)
    except panta.PantaError as error:
        print(f"Could not read the catalogue: {error}", file=sys.stderr)
        return report.EXIT_FAILED

    owner_of = (lambda _address: None) if args.no_chain else chain.account_owner
    verdicts = [classify.judge(card, owner_of, chain.looks_like_address) for card in cards]
    activity = {} if args.no_chain else settler_facts(verdicts)
    print(report.render(verdicts, show=args.show, settler_activity=activity))
    return report.exit_code(verdicts)


if __name__ == "__main__":
    raise SystemExit(main())
