"""The hourly live feed, tested without the chain: the three readers are replaced by lists."""
import importlib.util
import pathlib

SPEC = importlib.util.spec_from_file_location(
    "live", pathlib.Path(__file__).resolve().parent.parent / "demo" / "live.py")
live = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(live)

KEY = live.KNOWN_SETTLER
MARKET = "4yiz9ycF3PTwf6tMdTKTzFWNo9Yrph4XsSRHgPMpLpjG"


def tx(instruction, signer=KEY):
    return {
        "meta": {"logMessages": [f"Program log: Instruction: {instruction}"]},
        "transaction": {"message": {"accountKeys": [
            {"pubkey": signer, "signer": True, "writable": True},
            {"pubkey": MARKET, "signer": False, "writable": True},
        ]}},
    }


CHAIN = {
    "sigTrade": tx("SecondaryMarketOrder", signer="Trader1111111111111111111111111111111111111"),
    "sigResult": tx("SubmitOracleResultUsdc"),
    "sigResolve": tx("ResolveEvent"),  # the other naming family must count too
}
LISTING = [  # newest first, as getSignaturesForAddress returns them
    {"signature": "sigResolve", "blockTime": 300},
    {"signature": "sigResult", "blockTime": 200},
    {"signature": "sigTrade", "blockTime": 100},
]


def run(state, listing=LISTING, opened=None):
    opened = [] if opened is None else opened

    def open_transaction(signature):
        opened.append(signature)
        return CHAIN[signature]

    return live.refresh(state, list_signatures=lambda: listing, open_transaction=open_transaction,
                        card=lambda address: {"oracle": "on-chain", "sentToUma": True} if address == MARKET else None)


def test_settlements_are_found_and_shown_newest_first():
    state = run({})
    assert [e["signature"] for e in state["settlements"]] == ["sigResolve", "sigResult"]
    first = state["settlements"][0]
    assert first["market"] == MARKET and first["claims_uma"] is True
    assert first["signer_is_the_known_key"] is True and first["block_time"] == 300
    assert state["new_this_run"] == {"transactions": 3, "settlements": 2}


def test_a_second_run_opens_nothing_it_has_seen():
    state = run({})
    opened = []
    again = run(state, opened=opened)
    assert opened == []
    assert again["new_this_run"] == {"transactions": 0, "settlements": 0}
    assert len(again["settlements"]) == 2 and again["runs"] == 2


def test_a_failed_listing_keeps_the_last_good_feed():
    state = run({})

    def down():
        raise TimeoutError

    after = live.refresh(state, list_signatures=down, open_transaction=lambda s: None, card=None)
    assert after["settlements"] == state["settlements"]
    assert "could not list signatures" in after["last_error"]["what"]


def test_a_transaction_that_could_not_be_opened_is_tried_again_next_run():
    def flaky(signature):
        if signature == "sigResult":
            raise TimeoutError
        return CHAIN[signature]

    state = live.refresh({}, list_signatures=lambda: LISTING, open_transaction=flaky, card=None)
    assert "sigResult" not in state["seen"]
    opened = []
    again = run(state, opened=opened)
    assert opened == ["sigResult"]
    assert [e["signature"] for e in again["settlements"]] == ["sigResolve", "sigResult"]


def test_a_settlement_signed_by_another_key_is_marked_so():
    listing = [{"signature": "sigOther", "blockTime": 1}]
    CHAIN["sigOther"] = tx("ResolveEventUsdc", signer="Other11111111111111111111111111111111111111")
    state = run({}, listing=listing)
    assert state["settlements"][0]["signer_is_the_known_key"] is False


def test_without_a_panta_key_settlements_are_still_read(monkeypatch):
    monkeypatch.delenv("PANTA_API_KEY", raising=False)
    monkeypatch.setattr(live.panta, "KEY_FILE", pathlib.Path("/nonexistent/panta.key"))
    state = live.refresh({}, list_signatures=lambda: LISTING, open_transaction=lambda s: CHAIN[s])
    assert len(state["settlements"]) == 2
    assert state["settlements"][0]["market"] is None  # unknown, not guessed
