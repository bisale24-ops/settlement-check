"""What the report must say, and what it must never quietly stop saying."""
from settlementcheck import report
from settlementcheck.classify import EDITORIAL, ONE_KEY, UNSTATED, VERIFIABLE, Verdict


def verdict(kind, volume=0.0, tradeable=False, question="Will X?", oracle="global-ap",
            stripped=False):
    return Verdict(market_id="M" * 44, kind=kind, question=question, oracle=oracle,
                   detail="detail", phase="primary" if tradeable else "resolved",
                   volume=volume, tradeable=tradeable, stripped=stripped)


def test_an_unreported_volume_is_said_in_words_not_printed_as_zero():
    text = report.render([verdict(UNSTATED, None, True, question="")])
    assert "volume not reported" in text
    assert "$0" not in text


def test_the_headline_counts_how_many_markets_reported_nothing():
    text = report.render([verdict(UNSTATED, None, question=""), verdict(EDITORIAL, 10.0)])
    assert "(1 reported none)" in text


def test_the_headline_says_the_card_was_stripped_not_that_nobody_wrote_a_question():
    """The claim this replaces was disproved by opening a market page.

    Panta shows the question, the RESOLUTION CRITERIA and the sources to buyers. What a client
    building on the API actually faces is a card that arrives complete or stripped, with nothing
    in the response saying which — so that is what the first line says now.
    """
    text = report.render([verdict(UNSTATED, 4225.49, True, question="", stripped=True),
                          verdict(EDITORIAL, 10.0)])
    assert "1 of 2 cards came back stripped" in text
    assert "nothing in the response saying so" in text
    assert "do not say what you are buying" not in text

def test_findings_come_before_the_good_news():
    text = report.render([verdict(EDITORIAL, 5.0), verdict(UNSTATED, 1.0, question="")])
    assert text.index("STRIPPED") < text.index("EDITORIAL")


def test_an_empty_verifiable_group_is_still_printed():
    """A report that cannot say 'this one is fine' is not measuring anything — so when nothing
    is verifiable, it says so in as many words rather than omitting the heading."""
    text = report.render([verdict(ONE_KEY, 1.0)])
    assert "VERIFIABLE" in text
    assert "Nothing in this catalogue settles from a source a reader can audit." in text


def test_a_verifiable_market_replaces_that_sentence():
    text = report.render([verdict(VERIFIABLE, 1.0)])
    assert "Nothing in this catalogue" not in text


def test_the_wallet_section_names_what_the_key_controls():
    text = report.render([verdict(ONE_KEY, 224.0, oracle="W" * 44)],
                         settler_activity={"W" * 44: {"markets": 8, "volume": 224.0,
                                                      "signatures": 25, "programs": {"prog"}}})
    assert "THE WALLET THAT SETTLES THEM" in text
    assert "8 market(s) in this sample" in text and "25 recent signature(s)" in text


def test_the_exit_code_fires_on_findings_only():
    assert report.exit_code([verdict(EDITORIAL), verdict(VERIFIABLE)]) == report.EXIT_OK
    assert report.exit_code([verdict(UNSTATED, question="")]) == report.EXIT_FOUND
    assert report.exit_code([verdict(ONE_KEY)]) == report.EXIT_FOUND


def test_long_groups_are_trimmed_but_say_how_many_were_hidden():
    text = report.render([verdict(UNSTATED, question="") for _ in range(9)], show=3)
    assert "… and 6 more" in text


def test_the_headline_counts_signers_and_not_claimed_oracles():
    """It counted `oracle` and said "settled by 5 wallets" about seven markets one keypair had
    signed — the report contradicting its own wallet section. Measured on a live run, 2026-09-26."""
    one = "664h8sZvGwUx4hfqWYrewwvC7wenbKPTCFQTKZx5ghbR"
    verdicts = [
        Verdict(market_id="M" * 44, kind=ONE_KEY, question="Will X?", oracle="claimed-a",
                detail="d", phase="resolved", volume=10.0, tradeable=False, settled_by=(one,)),
        Verdict(market_id="N" * 44, kind=ONE_KEY, question="Will Y?", oracle="claimed-b",
                detail="d", phase="resolved", volume=20.0, tradeable=False, settled_by=(one,)),
    ]
    text = report.render(verdicts)
    assert "2 market(s) are settled by 1 wallet;" in text
    assert "2 wallets" not in text
