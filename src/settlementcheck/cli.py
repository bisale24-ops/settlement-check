"""settlement-check — what decides this market, and could anyone else have checked it?"""
import argparse
import json
import pathlib
import sys
import time

from . import chain, classify, draft as draftcheck, panta, report, watch as watcher


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="settlement-check", description=__doc__)
    parser.add_argument("--watch", type=int, metavar="SECONDS", nargs="?", const=0,
                        help="watch the market program live and report settlements as they land. "
                             "With no number it runs until interrupted. Traffic is printed too, "
                             "so an idle venue looks idle rather than broken")
    parser.add_argument("--poll", action="store_true",
                        help="with --watch: follow the signature list instead of holding a "
                             "subscription. A few seconds behind a stream, and it works on any "
                             "plan — Solami refuses a WebSocket without one that includes it, and "
                             "the public node closes the subscription it just acknowledged")
    parser.add_argument("--replay", metavar="SIGNATURE",
                        help="run the live path over one settlement that already happened, so the "
                             "same code can be demonstrated without waiting for the next one")
    parser.add_argument("--check-draft", metavar="FILE",
                        help="check a market draft (JSON) before it is published, instead of "
                             "reading the catalogue. Asks Panta to validate and price it; nothing "
                             "is signed, submitted or paid")
    parser.add_argument("--offline", action="store_true",
                        help="with --check-draft: apply the local rules only, ask Panta nothing")
    parser.add_argument("--pages", type=int, default=2, help="catalogue pages to read (50 each)")
    parser.add_argument("--cards", type=int, default=40, help="how many full cards to open")
    parser.add_argument("--tradeable-first", action=argparse.BooleanOptionalAction, default=True,
                        help="open cards for tradeable markets before settled ones")
    parser.add_argument("--show", type=int, default=6, help="entries printed per group")
    parser.add_argument("--settlements", type=int, default=8, metavar="N",
                        help="read the on-chain settlement of this many markets. Each one costs a "
                             "getSignaturesForAddress plus a getTransaction per signature, which "
                             "is why the default is small on a public node and why this is the "
                             "part that wants a real endpoint")
    parser.add_argument("--workers", type=int, default=6, metavar="N",
                        help="settlement lookups in flight at once. The public node starts "
                             "refusing above a couple; an endpoint with headroom does not, which "
                             "is where that headroom becomes wall-clock")
    parser.add_argument("--no-chain", action="store_true",
                        help="skip every on-chain lookup; nothing is claimed about who settled")
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


def read_settlements(cards, args):
    """Read who settled each market, spending a fixed budget on the markets that can answer.

    A market still in `primary` or `secondary` has not settled, so opening its history costs a
    request and learns nothing. The budget therefore goes to settled markets first. Every market
    the budget does not reach is recorded as NOT_LOOKED, never as a market nobody settled.
    """
    if args.no_chain or args.settlements <= 0:
        return None
    order = sorted(cards, key=lambda c: (c.get("phase") in ("primary", "secondary")))
    wanted = [card["marketId"] for card in order[:args.settlements]]
    found = chain.settlements(wanted, workers=args.workers)
    return lambda market_id: found.get(market_id, classify.NOT_LOOKED)


def settler_facts(verdicts):
    """For every key that actually settled a market here, what it controls and what it calls."""
    facts = {}
    settlers = {address for verdict in verdicts for address in verdict.settled_by}
    for address in settlers:
        theirs = [v for v in verdicts if address in v.settled_by]
        signatures = chain.recent_signatures(address, 1000)
        programs = chain.programs_touched(signatures[0]["signature"]) if signatures else set()
        facts[address] = {"markets": len(theirs),
                          "volume": sum(v.volume or 0 for v in theirs),
                          "signatures": len(signatures), "programs": programs}
    return facts


def check_draft(args):
    path = pathlib.Path(args.check_draft)
    try:
        body = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read the draft: {error}", file=sys.stderr)
        return report.EXIT_FAILED
    quoted, verdict, detail = None, None, ""
    if not args.offline:
        quoted, verdict, detail = draftcheck.quote(body)
    # --offline means offline: no quote, and no reachability request either.
    reach = None if args.offline else draftcheck.image_reachable
    text, blocks = draftcheck.report(body, int(time.time()), quoted, verdict, detail, reach=reach)
    print(text)
    return report.EXIT_FOUND if blocks else report.EXIT_OK


def live(args):
    """The live path. Everything it prints is parsed by the same code the tests exercise."""
    endpoint = chain.websocket_endpoint()
    # chain.safe() and nothing else: this line ends up in terminal recordings.
    print(f"watching {chain.MARKET_PROGRAM}\n  through {chain.safe(endpoint)}")
    if "api.mainnet-beta.solana.com" in endpoint:
        print("  (the public node. SOLANA_WS points this at a real endpoint — a Solami key "
              "raises the ceiling this measured at, not the code)")
    print("  settlements are rare; market traffic is printed so an idle venue looks idle\n")

    def traffic(signature, instructions, failed):
        if not watcher.is_settlement(instructions):
            names = " + ".join(instructions) or "(no instruction name in the logs)"
            print(f"  · {names}  {signature[:16]}…{'  failed' if failed else ''}")

    notice = lambda text: print(f"  ! {text}")  # noqa: E731
    if args.poll:
        print("  polling mode: the signature list, every few seconds\n")
        seen = watcher.poll(on_event=print, seconds=args.watch or None, on_traffic=traffic,
                            look_up=chain.transaction, catalogue=_card_if_market,
                            on_notice=notice)
    else:
        seen = watcher.watch(on_event=print, seconds=args.watch or None, on_traffic=traffic,
                             look_up=chain.transaction, catalogue=_card_if_market,
                             on_notice=notice)
    print(f"\n{seen} settlement(s) seen.")
    return report.EXIT_OK


def _card_if_market(address):
    """Is this writable account one of Panta's markets? The catalogue answers, or it does not."""
    try:
        return panta.market(address)
    except panta.PantaError:
        return None


def replay(signature):
    try:
        result = chain.transaction(signature)
    except chain.ChainError as error:
        print(f"could not read {signature}: {error}", file=sys.stderr)
        return report.EXIT_FAILED
    if not result:
        print(f"no transaction {signature} on this endpoint", file=sys.stderr)
        return report.EXIT_FAILED
    names, _signer = chain.instructions_and_signer(result)
    if not watcher.is_settlement(names):
        print(f"{signature} is not a settlement: {sorted(names) or 'no named instruction'}",
              file=sys.stderr)
        return report.EXIT_FAILED
    event = watcher.describe(signature, names, chain.transaction, _card_if_market)
    print(watcher.format_line(event))
    return report.EXIT_OK


def main(argv=None):
    args = parse_args(argv)
    if args.replay:
        return replay(args.replay)
    if args.watch is not None:
        return live(args)
    if args.check_draft:
        return check_draft(args)
    try:
        cards = collect(args)
    except panta.PantaError as error:
        print(f"Could not read the catalogue: {error}", file=sys.stderr)
        return report.EXIT_FAILED

    owner_of = (lambda _address: None) if args.no_chain else chain.account_owner
    settlement_of = read_settlements(cards, args)
    verdicts = [classify.judge(card, owner_of, chain.looks_like_address, settlement_of)
                for card in cards]
    activity = {} if args.no_chain else settler_facts(verdicts)
    print(report.render(verdicts, show=args.show, settler_activity=activity))
    return report.exit_code(verdicts)


if __name__ == "__main__":
    raise SystemExit(main())
