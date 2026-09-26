"""Watch settlements land, and say what each one was promised to be.

The rest of this tool looks backwards: it reads markets that have already been decided. This looks
forward. It subscribes to the market program and, the moment a settlement instruction lands, says
which market closed, what the catalogue claimed would decide it, and who actually signed.

The transport is a setting, not a constant. `SOLANA_WS` points at a public node today, and at a
Solami endpoint — private RPC, Mirage over WebSocket, or the Yellowstone firehose — when one is
available. The parsing below does not change either way, which is the whole reason it lives in a
function that takes a payload rather than a socket.

Why this wants a real endpoint: reading the settlements already in the catalogue costs one
getSignaturesForAddress plus a getTransaction per signature, per market. On the public node that
runs out at a couple of dozen markets — measured, it returns `getTransaction failed after 3
attempts`. Watching costs one subscription and one lookup per event instead, which is what makes
the live view possible at all.
"""
import json
import time

from . import chain, ws

# Every settlement passes through the market program, so one subscription sees all of them.
SUBSCRIBE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "logsSubscribe",
    "params": [{"mentions": [chain.MARKET_PROGRAM]}, {"commitment": "confirmed"}],
}


def instructions_in(logs):
    """The Anchor instruction names a transaction's logs announce."""
    return {line.split("Instruction: ", 1)[1].strip()
            for line in logs or [] if "Instruction: " in line}


def read_notification(payload):
    """Turn one subscription message into `(signature, instructions, failed)` or None.

    Pure on purpose: every interesting case — a settlement, an unrelated trade, a failed
    transaction, the subscription acknowledgement — is a string, so all of it is testable without
    a socket.
    """
    try:
        message = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if message.get("method") != "logsNotification":
        return None
    value = (message.get("params") or {}).get("result", {}).get("value") or {}
    signature = value.get("signature")
    if not signature:
        return None
    return signature, instructions_in(value.get("logs")), value.get("err") is not None


def is_settlement(instructions):
    return bool(chain.settlement_instructions_in(instructions))


def describe(signature, instructions, look_up=None, catalogue=None):
    """What to print for one settlement, with the market and the claim filled in when we can.

    `look_up` and `catalogue` are injected: the first fetches the transaction, the second the
    market card. Both are optional, and when either is missing the line says what it does not
    know rather than guessing.
    """
    found = sorted(instructions)
    line = {"signature": signature, "instructions": found, "market": None,
            "signer": None, "claimed": None, "claims_uma": None}
    if not look_up:
        return line
    result = look_up(signature)
    if not result:
        return line
    names, signer = chain.instructions_and_signer(result)
    line["signer"] = signer
    line["instructions"] = sorted(set(found) | chain.settlement_instructions_in(names))
    keys = result["transaction"]["message"].get("accountKeys", [])
    writable = [k["pubkey"] for k in keys
                if isinstance(k, dict) and k.get("writable") and not k.get("signer")]
    if catalogue:
        for candidate in writable:
            card = catalogue(candidate)
            if card:
                line["market"] = candidate
                line["claimed"] = (card.get("oracle") or "").strip() or None
                line["claims_uma"] = bool(card.get("sentToUma"))
                break
    return line


def format_line(event, now=None):
    stamp = time.strftime("%H:%M:%S", time.gmtime(now if now is not None else time.time()))
    what = " + ".join(event["instructions"]) or "settlement"
    parts = [f"{stamp}  {what}  {event['signature'][:16]}…"]
    if event["market"]:
        parts.append(f"          market   {event['market']}")
    if event["claimed"] is not None:
        parts.append(f"          claimed  {event['claimed']}")
    if event["claims_uma"]:
        parts.append("          the catalogue says this one went to UMA")
    if event["signer"]:
        parts.append(f"          signed   {event['signer']}")
    if event["claims_uma"] and event["signer"]:
        parts.append("          → a claim of UMA, settled by a signature, with no UMA "
                     "assertion in the transaction")
    return "\n".join(parts)


def watch(url=None, on_event=print, source=None, limit=None, look_up=None, catalogue=None,
          seconds=None, on_traffic=None, on_notice=None, reconnects=4, sleep=time.sleep,
          connect=None):
    """Subscribe and report settlements as they land. Returns the number of events seen.

    `source` is injected in tests: any iterable of payload strings stands in for the socket.

    Reconnecting is not a nicety here. Solana's public endpoint accepts a `logsSubscribe` with a
    program filter, acknowledges it, and then closes the connection — measured against
    `api.mainnet-beta.solana.com` on 2026-09-26. That is a property of the free node, not of the
    venue being watched, so the watcher says so and comes back rather than dying with a traceback
    and leaving the impression that nothing settles.
    """
    notice = on_notice or (lambda text: None)
    deadline = time.time() + seconds if seconds is not None else None
    opener = connect or (lambda: ws.rpc_subscribe(url or chain.websocket_endpoint(), SUBSCRIBE))
    seen = 0
    drops = 0

    while True:
        connection = None
        try:
            if source is None:
                connection = opener()
                stream = connection.messages()
            else:
                stream = iter(source)

            for payload in stream:
                if payload is None:                     # idle heartbeat
                    if deadline and time.time() > deadline:
                        return seen
                    continue
                parsed = read_notification(payload)
                if not parsed:
                    continue
                signature, instructions, failed = parsed
                if on_traffic:
                    on_traffic(signature, sorted(instructions), failed)
                if failed or not is_settlement(instructions):
                    if deadline and time.time() > deadline:
                        return seen
                    continue
                on_event(format_line(describe(signature, instructions, look_up, catalogue)))
                seen += 1
                if limit and seen >= limit:
                    return seen
                if deadline and time.time() > deadline:
                    return seen
            # The stream ended. With an injected source that is simply the end of the input.
            if source is not None:
                return seen
            raise ws.WebSocketError("the endpoint closed the subscription")
        except (ws.WebSocketError, OSError) as error:
            drops += 1
            if deadline and time.time() > deadline:
                return seen
            if drops > reconnects:
                notice(f"gave up after {drops} drops: {error}. This endpoint will not hold a "
                       f"logs subscription — the public node accepts it, acknowledges it and "
                       f"then closes. Point SOLANA_WS at an endpoint that will.")
                return seen
            notice(f"dropped ({error}); reconnecting, attempt {drops} of {reconnects}")
            sleep(min(2 ** drops, 15))
        finally:
            if connection:
                connection.close()


def poll(seen=None, look_up=None, catalogue=None, on_event=print, on_traffic=None,
         seconds=None, every=6.0, sleep=time.sleep, signatures=None, limit=None,
         on_notice=None):
    """The live view without a subscription, for a plan that does not include one.

    Solami answers a WebSocket upgrade on a Free key with
    `WebSocket access requires a plan that includes WebSocket access`, and the public node accepts
    a logs subscription and then closes it. Neither of those is a reason to have no live view: the
    market program's own signature list, polled, is a few seconds behind a stream and needs nothing
    but RPC — which is exactly where an endpoint with headroom pays for itself, because each new
    signature costs a getTransaction and the public node refuses under any concurrency at all.

    Reports the same lines as `watch`, through the same `describe` and `format_line`.
    """
    notice = on_notice or (lambda _text: None)
    fetch = signatures or (lambda: chain.recent_signatures(chain.MARKET_PROGRAM, 50))
    known = set(seen or ())
    first_pass = not known
    deadline = time.time() + seconds if seconds is not None else None
    found = 0

    while True:
        try:
            entries = fetch()
        except chain.ChainError as error:
            notice(f"could not list signatures: {error}")
            entries = []
        fresh = [entry for entry in entries if entry["signature"] not in known]
        for entry in reversed(fresh):          # oldest first, so the order reads like time
            known.add(entry["signature"])
            if first_pass:
                continue                       # the backlog is history, not news
            result = look_up(entry["signature"]) if look_up else None
            names = chain.instructions_and_signer(result)[0] if result else set()
            if on_traffic:
                on_traffic(entry["signature"], sorted(names), bool(entry.get("err")))
            if entry.get("err") or not is_settlement(names):
                continue
            on_event(format_line(describe(entry["signature"], names, look_up, catalogue),
                                 now=entry.get("blockTime")))
            found += 1
            if limit and found >= limit:
                return found
        first_pass = False
        if deadline and time.time() > deadline:
            return found
        sleep(every)
