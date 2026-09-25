"""The live watcher, tested without a socket.

Every interesting case is a payload string, so the parsing is exercised end to end while the
transport is replaced by a list. The one thing this cannot prove is that the endpoint speaks
WebSocket, which is what the live run against mainnet is for.
"""
import json

from settlementcheck import chain, watch

RESOLVER = "664h8sZvGwUx4hfqWYrewwvC7wenbKPTCFQTKZx5ghbR"
MARKET = "FFFcvy12DfhFMQTPieuGFHgzdXwkk24oXTRpbpXJPF9"


def notification(signature, instructions, err=None):
    logs = [f"Program {chain.MARKET_PROGRAM} invoke [1]"]
    logs += [f"Program log: Instruction: {name}" for name in instructions]
    return json.dumps({"jsonrpc": "2.0", "method": "logsNotification",
                       "params": {"result": {"value": {"signature": signature, "logs": logs,
                                                       "err": err}}}})


def transaction(signer, market):
    return {"transaction": {"message": {"accountKeys": [
        {"pubkey": signer, "signer": True, "writable": True},
        {"pubkey": market, "signer": False, "writable": True},
    ]}}, "meta": {"logMessages": ["Program log: Instruction: ResolveEventUsdc"]}}


def test_the_subscription_asks_for_the_market_program_and_nothing_else():
    assert watch.SUBSCRIBE["method"] == "logsSubscribe"
    assert watch.SUBSCRIBE["params"][0] == {"mentions": [chain.MARKET_PROGRAM]}


def test_a_trade_is_not_a_settlement():
    parsed = watch.read_notification(notification("sig1", ["PrimaryOrderUsdc"]))
    assert parsed is not None
    assert not watch.is_settlement(parsed[1])


def test_a_settlement_is_recognised():
    _sig, instructions, failed = watch.read_notification(
        notification("sig2", ["SubmitOracleResultUsdc"]))
    assert watch.is_settlement(instructions) and not failed


def test_a_failed_transaction_is_not_reported_as_a_settlement():
    events = []
    watch.watch(source=[notification("sig3", ["ResolveEventUsdc"], err={"InstructionError": []})],
                on_event=events.append)
    assert events == []


def test_the_subscription_acknowledgement_is_ignored():
    assert watch.read_notification(json.dumps({"jsonrpc": "2.0", "result": 42, "id": 1})) is None


def test_rubbish_on_the_socket_does_not_stop_the_watch():
    events = []
    seen = watch.watch(source=["not json", "", notification("sig4", ["ResolveEventUsdc"])],
                       on_event=events.append)
    assert seen == 1 and len(events) == 1


def test_an_event_names_the_market_the_claim_and_the_signature():
    events = []
    watch.watch(source=[notification("sig5", ["ResolveEventUsdc"])], on_event=events.append,
                look_up=lambda _s: transaction(RESOLVER, MARKET),
                catalogue=lambda address: {"oracle": "on-chain", "sentToUma": True}
                if address == MARKET else None)
    text = events[0]
    assert MARKET in text and RESOLVER in text
    assert "on-chain" in text and "went to UMA" in text
    assert "no UMA assertion in the transaction" in text


def test_without_a_lookup_the_line_says_what_it_does_not_know():
    """A watcher that cannot reach an RPC must not invent a signer."""
    events = []
    watch.watch(source=[notification("sig6", ["SubmitOracleResultUsdc"])], on_event=events.append)
    assert "SubmitOracleResultUsdc" in events[0]
    assert "signed" not in events[0] and "market" not in events[0]


def test_the_endpoint_is_a_setting(monkeypatch):
    monkeypatch.setenv("SOLANA_WS", "wss://mainnet.solami.dev/?api-key=x")
    assert chain.websocket_endpoint() == "wss://mainnet.solami.dev/?api-key=x"
    monkeypatch.delenv("SOLANA_WS")
    assert chain.websocket_endpoint().startswith("wss://")


def test_a_dropped_subscription_reconnects_and_then_says_so():
    """The public node acknowledges a logsSubscribe and then closes it. Measured 2026-09-26.

    A watcher that died there would leave the impression that the venue never settles anything,
    which is the wrong conclusion drawn from somebody else's rate limit.
    """
    from settlementcheck import ws as wsmod
    notices, attempts = [], []

    class Dropping:
        def messages(self):
            attempts.append(1)
            raise wsmod.WebSocketError("connection closed")

        def close(self):
            pass

    seen = watch.watch(connect=Dropping, on_notice=notices.append, reconnects=2,
                       sleep=lambda _s: None)
    assert seen == 0
    assert len(attempts) == 3
    assert "reconnecting, attempt 1 of 2" in notices[0]
    assert "will not hold a logs subscription" in notices[-1]


def test_reconnecting_keeps_the_events_already_counted():
    from settlementcheck import ws as wsmod
    payloads = [notification("sigA", ["ResolveEventUsdc"])]

    class Once:
        used = []

        def messages(self):
            Once.used.append(1)
            if len(Once.used) == 1:
                yield from payloads
                raise wsmod.WebSocketError("closed after one")
            raise wsmod.WebSocketError("closed again")

        def close(self):
            pass

    events = []
    seen = watch.watch(connect=Once, on_event=events.append, on_notice=lambda _t: None,
                       reconnects=1, sleep=lambda _s: None)
    assert seen == 1 and len(events) == 1
