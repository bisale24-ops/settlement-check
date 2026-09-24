"""The rule is tested against cards written here, so the expected verdict is known in advance.

No network: the two on-chain lookups are injected, which is the whole reason they are parameters.
"""
from settlementcheck import classify
from settlementcheck.classify import EDITORIAL, ONE_KEY, UNKNOWN, UNSTATED, VERIFIABLE

SYSTEM = "11111111111111111111111111111111"
WALLET = "4VGFQKGanc5oaLf51mee9m45HmiXRhKruh5mdRaMjipS"
PROGRAM_OWNED = "SysvarC1ock11111111111111111111111111111111"


def card(**over):
    base = {"marketId": "M" * 44, "description": "Will X happen by Friday?",
            "oracle": "global-ap", "phase": "primary", "totalVolumeUsdc": 100}
    base.update(over)
    return base


def judge(c, owner=None):
    owners = {WALLET: SYSTEM, PROGRAM_OWNED: "SomeProgram1111111111111111111111111111111"}
    if owner is not None:
        owners = owner
    return classify.judge(c, lambda a: owners.get(a), classify_is_address)


def classify_is_address(value):
    from settlementcheck import chain
    return chain.looks_like_address(value)


def test_a_market_with_no_question_is_the_finding_whatever_settles_it():
    verdict = judge(card(description="", oracle="global-bbc,global-ap"))
    assert verdict.kind == UNSTATED
    assert "global-bbc" in verdict.detail


def test_an_empty_title_does_not_count_as_a_question():
    """Panta leaves `title` blank on every market; only `description` carries the question."""
    assert judge(card(description="", title="")).kind == UNSTATED


def test_newsroom_feeds_are_editorial_and_are_named():
    verdict = judge(card(oracle="world-gaming-ign,world-gaming-polygon,world-entertainment-variety"))
    assert verdict.kind == EDITORIAL
    assert "3 newsroom feed(s)" in verdict.detail
    assert "world-gaming-ign" in verdict.detail


def test_a_wallet_settling_a_market_is_one_key_not_an_oracle():
    verdict = judge(card(oracle=WALLET))
    assert verdict.kind == ONE_KEY
    assert "keypair" in verdict.detail


def test_an_account_owned_by_a_program_is_the_good_case():
    verdict = judge(card(oracle=PROGRAM_OWNED))
    assert verdict.kind == VERIFIABLE


def test_an_address_that_does_not_exist_is_reported_as_unchecked_not_as_clean():
    verdict = judge(card(oracle=WALLET), owner={})
    assert verdict.kind == UNKNOWN
    assert "does not exist" in verdict.detail


def test_a_market_naming_no_source_at_all_is_unchecked():
    assert judge(card(oracle="")).kind == UNKNOWN


def test_volume_is_read_from_the_field_the_catalogue_actually_fills():
    """The card reports `primaryVolume`, the list row the settled total; prefer the total."""
    assert classify.volume_of({"totalVolumeUsdc": "4225.49", "primaryVolume": 0}) == 4225.49
    assert classify.volume_of({"primaryVolume": 7}) == 7


def test_a_missing_volume_is_not_a_zero():
    """The catalogue returns this field populated on one call and absent on the next. Reporting
    an unknown figure as $0 would be exactly the false clean bill this tool refuses to give."""
    assert classify.volume_of({}) is None
    assert classify.volume_of({"totalVolumeUsdc": None, "volumeUsdc": ""}) is None


def test_phase_decides_whether_money_can_still_be_put_on_it():
    assert judge(card(phase="primary")).tradeable
    assert judge(card(phase="secondary")).tradeable
    assert not judge(card(phase="resolved")).tradeable
    assert not judge(card(phase="cancelled")).tradeable
