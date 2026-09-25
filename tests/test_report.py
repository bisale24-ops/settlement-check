"""What the report must say, and what it must never quietly stop saying."""
from settlementcheck import report
from settlementcheck.classify import EDITORIAL, ONE_KEY, UNSTATED, VERIFIABLE, Verdict


def verdict(kind, volume=0.0, tradeable=False, question="Will X?", oracle="global-ap"):
    return Verdict(market_id="M" * 44, kind=kind, question=question, oracle=oracle,
                   detail="detail", phase="primary" if tradeable else "resolved",
                   volume=volume, tradeable=tradeable)


def test_an_unreported_volume_is_said_in_words_not_printed_as_zero():
    text = report.render([verdict(UNSTATED, None, True, question="")])
    assert "volume not reported" in text
    assert "$0" not in text


def test_the_headline_counts_how_many_markets_reported_nothing():
    text = report.render([verdict(UNSTATED, None, question=""), verdict(EDITORIAL, 10.0)])
    assert "(1 reported none)" in text


def test_the_headline_splits_what_is_on_sale_from_what_is_over():
    """The finding is the split, so the headline has to carry both halves.

    Counting the two populations together hides it: 34% of this catalogue states no question,
    which sounds like sloppy listings. Counted apart it is 85% of what you can still buy against
    0% of what is already settled — the question appears once it is too late to use it.
    """
    text = report.render([verdict(UNSTATED, 4225.49, True, question=""),
                          verdict(EDITORIAL, 10.0)])
    first = text.splitlines()[0]
    assert "2 markets read" in first and "$4,235" in first
    assert "Of the 1 you can buy right now, 1 (100%) do not say what you are buying" in text
    assert "$4,225" in text
    assert "Of the 1 already settled, every one states its question." in text


def test_findings_come_before_the_good_news():
    text = report.render([verdict(EDITORIAL, 5.0), verdict(UNSTATED, 1.0, question="")])
    assert text.index("UNSTATED") < text.index("EDITORIAL")


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
