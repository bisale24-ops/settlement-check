"""The pre-publish check, tested against drafts written here so the answer is known in advance.

No network: the quote call and the image reachability probe are both injected.
"""
import time

from settlementcheck import draft
from settlementcheck.draft import BLOCK, WARN

NOW = 1790000000
HOUR, DAY = 3600, 86400


def good(**over):
    body = {
        "wallet": "BxTgpq8cNYBjBTDHJfwbnPifmstHqhU16RYohQTu4ZcR",
        "question": "Will the Pectra upgrade activate on mainnet before 1 December 2026?",
        "resolutionRule": ("YES if the fork is active at 2026-12-01T00:00:00Z, read from the fork "
                           "schedule on ethereum.org and confirmed on etherscan.io."),
        "sourcesOfTruth": ["https://ethereum.org/en/roadmap/", "https://etherscan.io"],
        "category": "crypto",
        "startTime": NOW + 2 * HOUR,
        "endTime": NOW + 30 * DAY,
        "resolutionTime": NOW + 31 * DAY,
        "marketType": "standard",
        "imageUrl": "https://example.com/market-1024.png",
    }
    body.update(over)
    return body


def blocks(body, now=NOW):
    return [f for f in draft.check_locally(body, now) if f.level == BLOCK]


def fields(body, now=NOW):
    return {f.field for f in blocks(body, now)}


def test_a_readable_draft_passes():
    assert blocks(good()) == []


def test_a_source_of_truth_that_is_only_a_word_is_refused():
    """The rule that would have kept `on-chain` out of the catalogue.

    34 of 100 live markets name it as their settlement source, and it becomes the `oracle` string
    a buyer sees, verbatim. It is not an address, a program or a masthead.
    """
    found = blocks(good(sourcesOfTruth=["on-chain"]))
    assert [f.field for f in found] == ["sourcesOfTruth"]
    assert "not a reference" in found[0].message


def test_a_url_source_is_accepted_and_a_masthead_is_too():
    assert blocks(good(sourcesOfTruth=["https://www.coingecko.com"])) == []
    assert blocks(good(sourcesOfTruth=["world-sports-espn", "global-ap"])) == []


def test_an_empty_question_is_refused_even_though_the_catalogue_is_full_of_them():
    assert "question" in fields(good(question=""))


def test_times_must_be_orderable_and_far_enough_out():
    assert "endTime" in fields(good(startTime=NOW + 2 * DAY, endTime=NOW + DAY))
    assert "resolutionTime" in fields(good(resolutionTime=NOW + HOUR))
    assert "startTime" in fields(good(startTime=NOW + 60))


def test_a_breaking_market_in_progress_may_start_now():
    body = good(marketType="breaking", eventInProgress=True, startTime=NOW + 60)
    assert "startTime" not in fields(body)


def test_a_private_image_host_is_refused():
    assert "imageUrl" in fields(good(imageUrl="http://localhost:8080/m.png"))
    assert "imageUrl" in fields(good(imageUrl="https://192.168.1.4/m.png"))


def test_the_category_must_be_one_the_api_accepts():
    assert "category" in fields(good(category="weather"))


def test_a_very_short_resolution_rule_warns_but_does_not_block():
    found = draft.check_locally(good(resolutionRule="on-chain"), NOW)
    warns = [f for f in found if f.level == WARN and f.field == "resolutionRule"]
    assert warns and not [f for f in found if f.level == BLOCK]


def test_the_creator_is_shown_what_survives_into_the_catalogue():
    """The point of the whole tool: `oracle` is `sourcesOfTruth` joined, `title` defaults to the
    question, and `resolutionRule` is returned by nothing."""
    seen = draft.what_a_buyer_will_see(good(sourcesOfTruth=["a-b-c", "d-e-f"]))
    assert seen["oracle"] == "a-b-c,d-e-f"
    assert seen["title"].startswith("Will the Pectra")
    assert seen["resolutionRule"] is None


def test_an_unreachable_image_is_named_locally_instead_of_becoming_a_server_error():
    """Panta refuses a draft with a 404 image as INVALID_MARKET_PARAMS with no `fields` and a
    message pointing at server logs the caller cannot read. Measured 2026-09-26."""
    text, found = draft.report(good(), NOW, reach=lambda _u: (False, "HTTP 404"))
    assert [f.field for f in found] == ["imageUrl"]
    assert "HTTP 404" in text and "never mentions the image" in text


def test_an_image_probe_that_fails_to_connect_is_not_a_finding():
    _text, found = draft.report(good(), NOW, reach=lambda _u: (True, ""))
    assert found == []


def test_the_report_says_plainly_that_the_resolution_rule_reaches_nobody():
    text, _ = draft.report(good(), NOW)
    assert "not returned by the read API under any name" in text


class _Response:
    def __init__(self, status, content_type="image/png"):
        self.status = status
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_a_host_that_refuses_HEAD_but_serves_GET_is_reachable():
    """The false finding this check produced on its first run.

    `https://picsum.photos/1024` answers HEAD with 404 and GET with an image, and Panta accepted
    a draft pointing at it. A probe stricter than the thing it predicts invents findings.
    """
    calls = []

    def opener(request, timeout=None):
        calls.append(request.get_method())
        if request.get_method() == "HEAD":
            raise draft.urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)
        return _Response(206)

    ok, why = draft.image_reachable("https://example.com/i.png", opener=opener)
    assert ok and why == ""
    assert calls == ["HEAD", "GET"]


def test_a_url_that_fails_both_ways_is_unreachable():
    def opener(request, timeout=None):
        raise draft.urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)

    ok, why = draft.image_reachable("https://example.com/i.png", opener=opener)
    assert not ok and why == "HTTP 404"
