"""The Mirage decoder is tested against frames built here, so the expected answer is known.

Frames are encoded with the same field numbers the decoder reads, plus fields it has never heard
of, because a real SubscribeUpdate carries far more than the three fields this project wants.
"""
from settlementcheck import mirage, watch
from settlementcheck.mirage import encode_field, encode_fixed64

SIGNATURE = bytes(range(64))
RESOLVE_LOGS = ["Program 6gM5afTQBq5VZCfgpGqcsqzfWd5maLSCKWtGjbEobZMp invoke [1]",
                "Program log: Instruction: ResolveEventUsdc",
                "Program 6gM5afTQBq5VZCfgpGqcsqzfWd5maLSCKWtGjbEobZMp success"]


def frame(signature=SIGNATURE, logs=RESOLVE_LOGS, failed=False, vote=False, extra=b""):
    meta = b"".join(encode_field(6, line) for line in logs)
    if failed:
        meta = encode_field(1, encode_field(1, b"\x01")) + meta          # err: any message
    meta += encode_field(2, 5000)                                          # fee, skipped
    meta += encode_field(3, b"\x01\x02")                                   # pre_balances, skipped
    info = (encode_field(1, signature) + encode_field(2, vote) + encode_field(3, b"\x0a\x00")
            + encode_field(4, meta) + encode_field(5, 7))
    transaction = encode_field(1, info) + encode_field(2, 123456789)       # slot
    update = encode_field(1, "settlements") + encode_field(4, transaction) + extra
    update += encode_fixed64(99, 42)                                       # unknown fixed64
    return update


def test_a_settlement_frame_yields_the_signature_the_logs_and_success():
    signature, logs, failed = mirage.read_update(frame())
    assert signature == mirage.base58(SIGNATURE)
    assert "Program log: Instruction: ResolveEventUsdc" in logs
    assert failed is False


def test_a_failed_transaction_is_flagged_by_the_presence_of_err():
    _, _, failed = mirage.read_update(frame(failed=True))
    assert failed is True


def test_votes_pings_and_slot_updates_are_not_events():
    assert mirage.read_update(frame(vote=True)) is None
    ping = encode_field(6, b"")                                            # SubscribeUpdatePing
    assert mirage.read_update(ping) is None
    slot = encode_field(3, encode_field(1, 1) + encode_field(2, 0))
    assert mirage.read_update(slot) is None


def test_a_truncated_frame_is_skipped_rather_than_crashing_the_watcher():
    assert mirage.read_update(frame()[:20]) is None
    assert mirage.read_update(b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff") is None


def test_base58_matches_the_addresses_solana_prints():
    # The System Program is 32 zero bytes, which base58 spells as 32 ones.
    assert mirage.base58(bytes(32)) == "1" * 32
    # Round-trip a known address through the standard decoding.
    address = "664h8sZvGwUx4hfqWYrewwvC7wenbKPTCFQTKZx5ghbR"
    number = 0
    for char in address:
        number = number * 58 + mirage.ALPHABET.index(char.encode())
    assert mirage.base58(number.to_bytes(32, "big")) == address


def test_the_watcher_reads_a_mirage_frame_the_same_way_as_a_logs_notification():
    """Same three answers from either wire, so `watch()` needs no idea which one it is on."""
    from_mirage = watch.read_payload(frame())
    from_rpc = watch.read_payload(
        '{"method":"logsNotification","params":{"result":{"value":{"signature":"%s","logs":%s,'
        '"err":null}}}}' % (mirage.base58(SIGNATURE),
                            str(RESOLVE_LOGS).replace("'", '"')))
    assert from_mirage[0] == from_rpc[0]
    assert from_mirage[1] == from_rpc[1] == {"ResolveEventUsdc"}
    assert from_mirage[2] is from_rpc[2] is False


def test_a_mirage_stream_of_frames_produces_the_same_settlement_line():
    seen = []
    count = watch.watch(source=[frame(), encode_field(6, b""), frame(vote=True)],
                        on_event=seen.append, look_up=lambda _s: None, catalogue=lambda _m: None)
    assert count == 1
    assert "ResolveEventUsdc" in seen[0]
    assert mirage.base58(SIGNATURE)[:16] in seen[0]
