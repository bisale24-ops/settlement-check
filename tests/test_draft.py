"""The pre-publish check, tested against drafts written here so the answer is known in advance.

No network: the quote call and the image reachability probe are both injected.
"""
import time

from settlementcheck import draft, panta
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


def test_an_unreachable_image_is_our_finding_and_is_not_blamed_on_panta():
    """This assertion used to claim Panta refuses a 404 image. It does not.

    A draft pointing at a URL that returns 404 was quoted successfully on 2026-09-26, so the
    refusal we saw had nothing to do with the image. A broken picture still leaves a hole in the
    catalogue, so the tool keeps the check — as a warning of its own, without attributing it to
    somebody else's validator.
    """
    text, blocks = draft.report(good(), NOW, reach=lambda _u: (False, "HTTP 404"))
    assert blocks == []
    assert "HTTP 404" in text
    assert "our check, not" in text


def test_a_refusal_naming_no_field_is_not_evidence_about_the_draft():
    """Measured 2026-09-26: 19 of 20 identical quotes for one valid draft came back
    INVALID_MARKET_PARAMS with "check server logs" and no fields, and a repeat quote for the same
    wallet and question failed 4 times out of 4 where the docs promise DUPLICATE_MARKET."""
    assert draft.read_refusal('HTTP 400: {"code":"INVALID_MARKET_PARAMS",'
                              '"message":"unexpected create quote failure — check server logs"}'
                              ) == draft.INCONCLUSIVE
    assert draft.read_refusal('HTTP 400: {"code":"INVALID_MARKET_PARAMS",'
                              '"fields":{"startTime":"too soon"}}') == draft.REFUSED


def test_an_inconclusive_quote_is_retried_and_a_field_refusal_is_not():
    calls = []

    def flaky(_path, _body):
        calls.append(1)
        raise panta.PantaError('HTTP 400: {"code":"INVALID_MARKET_PARAMS",'
                               '"message":"unexpected create quote failure — check server logs"}')

    def refused(_path, _body):
        calls.append(1)
        raise panta.PantaError('HTTP 400: {"code":"INVALID_MARKET_PARAMS","fields":{"category":"?"}}')

    payload, verdict, _detail = draft.quote(good(), post=flaky, attempts=3, sleep=lambda _s: None)
    assert payload is None and verdict == draft.INCONCLUSIVE and len(calls) == 3

    calls.clear()
    payload, verdict, _detail = draft.quote(good(), post=refused, attempts=3, sleep=lambda _s: None)
    assert payload is None and verdict == draft.REFUSED and len(calls) == 1


def test_an_inconclusive_quote_never_tells_the_creator_their_draft_is_wrong():
    text, _blocks = draft.report(good(), NOW, verdict=draft.INCONCLUSIVE,
                                 detail="INVALID_MARKET_PARAMS")
    assert "not evidence about your draft" in text
    assert "refused, naming the fields" not in text


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
