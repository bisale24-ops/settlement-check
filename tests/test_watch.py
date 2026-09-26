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


def test_polling_reports_the_same_line_a_subscription_would():
    """The live view must not depend on a plan. Solami refuses a WebSocket upgrade without one
    that includes it, and the public node closes the subscription it just acknowledged."""
    calls = {"n": 0}

    def signatures():
        calls["n"] += 1
        if calls["n"] == 1:
            return [{"signature": "old1", "blockTime": 1}]          # backlog
        return [{"signature": "new1", "blockTime": 2}, {"signature": "old1", "blockTime": 1}]

    events = []
    found = watch.poll(signatures=signatures, on_event=events.append, limit=1,
                       look_up=lambda _s: transaction(RESOLVER, MARKET),
                       catalogue=lambda a: {"oracle": "on-chain", "sentToUma": True}
                       if a == MARKET else None,
                       sleep=lambda _s: None)
    assert found == 1 and len(events) == 1
    assert MARKET in events[0] and RESOLVER in events[0]
    assert "no UMA assertion in the transaction" in events[0]


def test_the_backlog_on_the_first_pass_is_history_not_news():
    """Starting up must not announce every settlement that already happened as if it just did."""
    events = []
    watch.poll(signatures=lambda: [{"signature": "already", "blockTime": 1}],
               on_event=events.append, seconds=0,
               look_up=lambda _s: transaction(RESOLVER, MARKET), sleep=lambda _s: None)
    assert events == []


def test_a_failed_transaction_is_not_polled_into_a_settlement():
    calls = {"n": 0}

    def signatures():
        calls["n"] += 1
        return [] if calls["n"] == 1 else [{"signature": "bad", "blockTime": 2, "err": {"x": 1}}]

    events = []
    found = watch.poll(signatures=signatures, on_event=events.append, seconds=0,
                       look_up=lambda _s: transaction(RESOLVER, MARKET), sleep=lambda _s: None)
    assert found == 0 and events == []


def test_no_command_ever_prints_the_key(capsys, monkeypatch, tmp_path):
    """A credential printed to the terminal is a credential in the next screen recording.

    This is not hypothetical: the first live run of --watch --poll printed the Solami key in full
    on its second line, because the endpoint was interpolated without chain.safe().
    """
    from settlementcheck import chain, cli
    secret = "sk_thisIsTheKeyAndItMustNotAppear"
    key_file = tmp_path / "solami.key"
    key_file.write_text(secret)
    monkeypatch.setenv("SOLAMI_KEY_FILE", str(key_file))
    monkeypatch.delenv("SOLANA_RPC", raising=False)
    monkeypatch.delenv("SOLANA_WS", raising=False)

    import importlib
    importlib.reload(chain)
    assert secret in chain.RPC                       # the key really is in the endpoint
    assert secret not in chain.safe(chain.RPC)
    assert secret not in chain.safe(chain.websocket_endpoint())

    monkeypatch.setattr(cli.watcher, "poll", lambda **_kw: 0)
    cli.live(cli.parse_args(["--watch", "0", "--poll"]))
    printed = capsys.readouterr().out
    assert secret not in printed
    assert "<key>" in printed


def test_both_instruction_name_families_count_as_a_settlement():
    """Markets that carry a MigrateEventV2 settle under the unsuffixed names.

    Measured 2026-09-26 on 3H2GD9PzAfxQpxqJkFLWR9BZxSe8PGbAN1NWV3goYBzg: ResolveEvent and
    SubmitOracleResult, signed by the same keypair that signs the suffixed pair everywhere else.
    Matching only the suffixed names reported that market as one nothing had settled.
    """
    assert watch.is_settlement({"ResolveEventUsdc"})
    assert watch.is_settlement({"ResolveEvent"})
    assert watch.is_settlement({"SubmitOracleResult"})
    assert not watch.is_settlement({"PrimaryOrder", "ClaimWinnings", "MigrateEventV2"})
    assert chain.base_instruction("ResolveEventUsdc") == "ResolveEvent"
    assert chain.base_instruction("ResolveEvent") == "ResolveEvent"


def test_a_settlement_under_the_older_names_is_described_like_any_other():
    events = []
    watch.watch(source=[notification("sigV1", ["ResolveEvent"])], on_event=events.append,
                look_up=lambda _s: {"transaction": {"message": {"accountKeys": [
                    {"pubkey": RESOLVER, "signer": True, "writable": True},
                    {"pubkey": MARKET, "signer": False, "writable": True}]}},
                    "meta": {"logMessages": ["Program log: Instruction: ResolveEvent"]}},
                catalogue=lambda a: {"oracle": "on-chain", "sentToUma": True} if a == MARKET else None)
    assert len(events) == 1
    assert "ResolveEvent" in events[0] and RESOLVER in events[0]


def test_a_history_that_hits_the_limit_is_not_a_complete_history():
    """The methodological trap that nearly produced a false finding.

    getSignaturesForAddress returns the most recent n. A market showing no orders in its last 25
    transactions had eight in its last 40, so "never traded" can only be said when the whole
    history fits under the limit — otherwise the answer is None, never False.
    """
    from settlementcheck import chain as c
    calls = []

    def fake(address, limit=10):
        calls.append(limit)
        return [{"signature": f"s{i}"} for i in range(limit)]     # always fills the limit

    original = c.recent_signatures
    c.recent_signatures = fake
    try:
        assert c.traded_on_chain("M" * 44, limit=25) is None
    finally:
        c.recent_signatures = original


def test_a_short_history_with_only_a_migration_means_it_never_traded_here():
    from settlementcheck import chain as c
    original_sigs, original_tx = c.recent_signatures, c.transaction
    c.recent_signatures = lambda _a, limit=10: [{"signature": "m1"}, {"signature": "m2"}]
    c.transaction = lambda _s: {"transaction": {"message": {"accountKeys": []}},
                                "meta": {"logMessages": ["Program log: Instruction: MigrateEventV2"]}}
    try:
        assert c.traded_on_chain("M" * 44, limit=1000) is False
    finally:
        c.recent_signatures, c.transaction = original_sigs, original_tx
