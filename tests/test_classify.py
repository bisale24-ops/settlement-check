"""The rule is tested against cards written here, so the expected verdict is known in advance.

No network: the two on-chain lookups are injected, which is the whole reason they are parameters.
"""
from settlementcheck import classify
from settlementcheck.classify import (EDITORIAL, NAMED_NOTHING, ONE_KEY, UNKNOWN, UNSTATED,
                                      VERIFIABLE)

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


def test_a_market_with_neither_field_filled_is_unstated():
    assert judge(card(description="", title="")).kind == UNSTATED


def test_the_question_is_read_from_the_card_title_not_only_the_description():
    """The regression that nearly shipped.

    Listing rows leave `title` empty on all 100 markets, so measuring `description` alone said 91%
    of this catalogue states no question. Open the card and `title` carries it on 56 of 100. The
    real figure is 34%, and the finding is the split: 0% of settled markets are silent against 85%
    of the ones still on sale.
    """
    verdict = judge(card(description="", title="Will Portugal win their Round of 16 match?"))
    assert verdict.kind != UNSTATED
    assert verdict.question == "Will Portugal win their Round of 16 match?"


def test_a_settlement_source_that_is_only_a_word_names_nothing():
    """`on-chain` is the most common value in the whole oracle field. It is not an address, not a
    program and not a masthead — and if settlement really were on-chain there would be an account
    to name. Calling it a newsroom feed, as this tool first did, is too generous by half."""
    verdict = judge(card(oracle="on-chain"))
    assert verdict.kind == NAMED_NOTHING
    assert "not an address" in verdict.detail


def test_a_two_part_masthead_is_still_a_masthead():
    """`global-ap`, `global-bbc` and `global-reuters` are real outlets with two-part identifiers,
    which is why naming-nothing is a literal list and not a rule about shape."""
    verdict = judge(card(oracle="global-ap,global-bbc"))
    assert verdict.kind == EDITORIAL
    assert "2 newsroom feed(s)" in verdict.detail


def test_a_word_mixed_in_with_real_outlets_is_called_out_separately():
    verdict = judge(card(oracle="world-sports-espn,on-chain"))
    assert verdict.kind == EDITORIAL
    assert "1 newsroom feed(s)" in verdict.detail
    assert "1 naming nothing" in verdict.detail and "on-chain" in verdict.detail


def test_an_unstated_market_settled_by_a_word_says_so():
    verdict = judge(card(title="", description="", oracle="on-chain"))
    assert verdict.kind == UNSTATED
    assert "a word, not a reference" in verdict.detail


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
