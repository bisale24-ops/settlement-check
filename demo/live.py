"""Refresh docs/live.json: what landed on the market program since the last look.

    python3 demo/live.py            # reads the chain (Solami if a key is set), updates docs/live.json

Run every hour by .github/workflows/live.yml, so the published page carries a feed that a
machine kept current rather than a snapshot someone once took. Each run lists the program's
recent signatures, opens only the ones it has not seen, and keeps every settlement it finds
with the account that signed it and, when the Panta key is present, what the market's card
claims. A failed read keeps the last good feed and says when and why it failed.
"""
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from settlementcheck import chain, panta, watch  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "live.json"
LOOK_BACK = 200      # signatures listed per run; the program is quiet, an hour never fills this
KEEP_SEEN = 600      # signatures remembered, so a quiet hour does not reopen old ones
KEEP_EVENTS = 40     # settlements shown on the page


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def card_if_market(address):
    try:
        return panta.market(address)
    except Exception:  # no key, or the card is not a market: the line says what it does not know
        return None


def has_panta_key():
    try:
        return bool(panta.api_key())
    except panta.PantaError:  # no key: settlements are still read, cards are not
        return False


def load():
    try:
        return json.loads(OUT.read_text())
    except (OSError, ValueError):
        return {"settlements": [], "seen": [], "runs": 0, "transactions_read": 0}


def endpoint_name():
    return "Solami RPC" if "solami" in chain.RPC else "public Solana node"


def refresh(state, list_signatures=None, open_transaction=None, card=None):
    """One pass. Pure apart from the three injected readers, which the tests replace."""
    list_signatures = list_signatures or (lambda: chain.recent_signatures(chain.MARKET_PROGRAM, LOOK_BACK))
    open_transaction = open_transaction or chain.transaction
    card = card or (card_if_market if has_panta_key() else None)

    state = dict(state)
    state["runs"] = state.get("runs", 0) + 1
    state["checked_at"] = now_iso()
    state["endpoint"] = endpoint_name()
    try:
        entries = list_signatures()
    except Exception as error:  # keep the last good feed and say why this one is missing
        state["last_error"] = {"at": state["checked_at"], "what": f"could not list signatures: {type(error).__name__}"}
        return state

    seen = set(state.get("seen", []))
    fresh = [e for e in reversed(entries) if e.get("signature") not in seen and not e.get("err")]
    found = []
    for entry in fresh:
        signature = entry["signature"]
        try:
            result = open_transaction(signature)
        except Exception:
            continue  # not marked seen: the next run tries it again
        seen.add(signature)
        if not result:
            continue
        names, _signer = chain.instructions_and_signer(result)
        settling = chain.settlement_instructions_in(names)
        if not settling:
            continue
        event = watch.describe(signature, settling, look_up=lambda _s, r=result: r, catalogue=card)
        event["block_time"] = entry.get("blockTime")
        event["signer_is_the_known_key"] = event["signer"] == KNOWN_SETTLER
        found.append(event)

    state["transactions_read"] = state.get("transactions_read", 0) + len(fresh)
    state["new_this_run"] = {"transactions": len(fresh), "settlements": len(found)}
    # newest first by block time: a retried transaction can land in a later run than a newer one
    merged = {e["signature"]: e for e in state.get("settlements", []) + found}
    state["settlements"] = sorted(merged.values(), key=lambda e: e.get("block_time") or 0, reverse=True)[:KEEP_EVENTS]
    state["seen"] = [e["signature"] for e in entries if e.get("signature") in seen][:KEEP_SEEN]
    state.pop("last_error", None)
    return state


# The keypair that signed every settlement inspected so far (README, "What settles a market").
KNOWN_SETTLER = "664h8sZvGwUx4hfqWYrewwvC7wenbKPTCFQTKZx5ghbR"


def main():
    state = refresh(load())
    OUT.write_text(json.dumps(state, indent=1) + "\n")
    new = state.get("new_this_run", {})
    print(f"{state['checked_at']}  via {state['endpoint']}: {new.get('transactions', 0)} new transactions, "
          f"{new.get('settlements', 0)} settlements; {len(state['settlements'])} in the feed"
          + (f"  ! {state['last_error']['what']}" if "last_error" in state else ""))


if __name__ == "__main__":
    main()
