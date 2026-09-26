"""Check a market before it is published, and show the creator what a buyer will actually see.

Panta's create API demands three things from whoever opens a market: a `question`, a
`resolutionRule` of up to 2048 characters, and a non-empty `sourcesOfTruth`. The read API returns
none of them under those names. `title` defaults to the question and appears on the market's card
but never in the listing. `oracle` is `sourcesOfTruth` joined by commas — which is why the single
most common settlement source in the live catalogue is the word `on-chain`: somebody typed it into
that list. And `resolutionRule`, the only field that states the actual criteria, is not in the read
response at all.

So this does two things a creator cannot do for themselves:

1. Refuses a draft whose sources are not references, whose times are impossible, or whose question
   nobody could act on — before the 50 USDC creation fee is paid.
2. Prints what survives into the catalogue, so the gap between what was written and what will be
   readable is visible while it can still be closed.

Nothing here signs or submits anything. The quote endpoint validates and returns the fee; the
transaction is built, signed and broadcast by the market's creator, not by this tool.
"""
import dataclasses
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from . import panta
from .classify import names_a_source

CATEGORIES = ("sports", "crypto", "politics", "entertainment", "finance", "science", "world",
              "other")

# The chain's own `minimumStartDelay`, which the docs give as typically 3600 seconds. Read from the
# quote response when the endpoint is reachable; this is the fallback for an offline check.
MINIMUM_START_DELAY = 3600

MAX_QUESTION = 512
MAX_RULE = 2048
MAX_SOURCES = 20
MAX_IMAGE_URL = 2048

BLOCK, WARN = "BLOCK", "WARN"


@dataclasses.dataclass
class Finding:
    level: str
    field: str
    message: str
    fix: str = ""


def _url(value):
    try:
        parsed = urllib.parse.urlparse(value)
    except ValueError:
        return None
    return parsed if parsed.scheme in ("http", "https") and parsed.netloc else None


PRIVATE_HOST = re.compile(
    r"^(localhost|127\.|0\.0\.0\.0|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.|\[?::1)",
    re.I)


def check_sources(sources):
    """Every entry has to be something a reader can open or a masthead they can name.

    This is the rule that would have kept `on-chain` out of the catalogue. A settlement source
    that asserts a mechanism instead of naming a publisher tells a buyer nothing: if the outcome
    really comes from the chain, the account has to be named, and it never is.
    """
    out = []
    if not isinstance(sources, list) or not sources:
        return [Finding(BLOCK, "sourcesOfTruth", "no source of truth given",
                        "name at least one URL or outlet a reader can check")]
    if len(sources) > MAX_SOURCES:
        out.append(Finding(BLOCK, "sourcesOfTruth",
                           f"{len(sources)} sources, the API accepts {MAX_SOURCES}",
                           f"drop {len(sources) - MAX_SOURCES}"))
    for source in sources:
        text = str(source).strip()
        if not text:
            out.append(Finding(BLOCK, "sourcesOfTruth", "an empty source in the list",
                               "remove it or name the outlet"))
            continue
        if _url(text):
            continue
        if not names_a_source(text):
            out.append(Finding(
                BLOCK, "sourcesOfTruth", f"{text!r} is a word, not a reference",
                "name the account, the program or the outlet. A buyer sees this string and "
                "nothing else — it becomes the market's `oracle` field verbatim"))
    return out


def check_times(draft, now, minimum_delay=MINIMUM_START_DELAY):
    start, end, resolution = (draft.get("startTime"), draft.get("endTime"),
                              draft.get("resolutionTime"))
    out = []
    for name, value in (("startTime", start), ("endTime", end), ("resolutionTime", resolution)):
        if not isinstance(value, int):
            out.append(Finding(BLOCK, name, "missing or not unix seconds",
                               "give an integer number of seconds since the epoch"))
    if out:
        return out
    if not start < end:
        out.append(Finding(BLOCK, "endTime", "trading would close before it opens",
                           "startTime must be earlier than endTime"))
    if end > resolution:
        out.append(Finding(BLOCK, "resolutionTime", "the market resolves before trading ends",
                           "resolutionTime must be at or after endTime"))
    breaking = draft.get("marketType") == "breaking" and draft.get("eventInProgress")
    if not breaking and start - now < minimum_delay:
        out.append(Finding(
            BLOCK, "startTime",
            f"starts in {max(start - now, 0)}s; the chain requires {minimum_delay}s",
            "move startTime further out, or declare it a breaking market in progress"))
    if breaking and end <= now:
        out.append(Finding(BLOCK, "endTime", "a breaking market must still end in the future", ""))
    return out


def check_locally(draft, now):
    """Everything that can be decided without spending a request."""
    out = []
    question = str(draft.get("question") or "").strip()
    if not question:
        out.append(Finding(BLOCK, "question", "no question",
                           "state what is being bet on, in one sentence"))
    elif len(question) > MAX_QUESTION:
        out.append(Finding(BLOCK, "question", f"{len(question)} characters, the API accepts "
                                              f"{MAX_QUESTION}", "shorten it"))

    rule = str(draft.get("resolutionRule") or "").strip()
    if not rule:
        out.append(Finding(BLOCK, "resolutionRule", "no resolution criteria",
                           "say what measurement decides this, and when it is taken"))
    elif len(rule) > MAX_RULE:
        out.append(Finding(BLOCK, "resolutionRule",
                           f"{len(rule)} characters, the API accepts {MAX_RULE}", "shorten it"))
    elif len(rule) < 40:
        out.append(Finding(
            WARN, "resolutionRule", f"{len(rule)} characters",
            "a rule this short rarely names both the measurement and the moment it is read; "
            "nobody can see this field after publication, so it is the creator's only record"))

    out += check_sources(draft.get("sourcesOfTruth"))
    out += check_times(draft, now)

    category = draft.get("category")
    if category not in CATEGORIES:
        out.append(Finding(BLOCK, "category", f"{category!r} is not one the API accepts",
                           "one of " + ", ".join(CATEGORIES)))

    image = str(draft.get("imageUrl") or "").strip()
    parsed = _url(image)
    if not image:
        out.append(Finding(BLOCK, "imageUrl", "required by the create API", "give an http(s) URL"))
    elif not parsed:
        out.append(Finding(BLOCK, "imageUrl", "not an http or https URL", "give a reachable URL"))
    elif PRIVATE_HOST.match(parsed.netloc):
        out.append(Finding(BLOCK, "imageUrl", "points at a private address",
                           "host it somewhere a reader can reach"))
    elif len(image) > MAX_IMAGE_URL:
        out.append(Finding(BLOCK, "imageUrl", f"{len(image)} characters, the API accepts "
                                              f"{MAX_IMAGE_URL}", "shorten it"))
    return out


def image_reachable(url, timeout=10, opener=None):
    """Is the catalogue image actually there?

    Worth its own request because of how the endpoint fails without it. A draft whose `imageUrl`
    404s is refused with `INVALID_MARKET_PARAMS` and the message "unexpected create quote failure
    — check server logs" — no `fields`, no mention of the image, and a pointer to logs the caller
    cannot read. Measured on 2026-09-26: identical drafts, one with an unreachable image and one
    with a reachable one, produced that error and a clean 50 USDC quote respectively.

    HEAD first, then a one-byte GET, because the first version of this check asked only for HEAD
    and called `https://picsum.photos/1024` unreachable — a host that answers GET perfectly well
    and that Panta itself accepted. A probe that is stricter than the thing it predicts is a
    false finding, which is the one kind this tool is not allowed to produce.

    Returns (ok, detail). A transport failure returns True: an unproven URL must not become a
    finding either.
    """
    send = opener or urllib.request.urlopen
    last = ""
    for method, headers in (("HEAD", {}), ("GET", {"Range": "bytes=0-0"})):
        request = urllib.request.Request(
            url, method=method,
            headers={"User-Agent": "settlement-check/0.1", **headers})
        try:
            with send(request, timeout=timeout) as response:
                code = getattr(response, "status", 200) or 200
                kind = (response.headers.get("Content-Type", "")
                        if hasattr(response, "headers") else "")
            if code >= 400:
                last = f"HTTP {code}"
                continue
            if kind and not kind.startswith("image/"):
                last = f"served as {kind}, not an image"
                continue
            return True, ""
        except urllib.error.HTTPError as error:
            last = f"HTTP {error.code}"
            continue
        except Exception:
            return True, ""
    return False, last or "no response"


def what_a_buyer_will_see(draft):
    """The catalogue's view of this draft, derived from the create API's own defaults.

    `title` defaults to `question`; `oracle` defaults to `sourcesOfTruth` joined by commas; and
    `resolutionRule` has no field in the read response at all.
    """
    sources = draft.get("sourcesOfTruth") or []
    return {
        "title": str(draft.get("title") or draft.get("question") or "").strip(),
        "description": str(draft.get("description") or "").strip(),
        "oracle": ",".join(str(s).strip() for s in sources if str(s).strip()),
        "resolutionRule": None,   # not returned by the read API under any name
    }


PASSED, REFUSED, INCONCLUSIVE = "passed", "refused", "inconclusive"


def read_refusal(error):
    """Whose problem is a 400 — the draft's, or the endpoint's?

    The documented contract is that field validation returns `code` **plus `fields`**. What the
    live endpoint returns instead, for a draft it accepted seconds earlier, is
    `INVALID_MARKET_PARAMS` with "unexpected create quote failure — check server logs" and no
    fields at all. Measured on 2026-09-26: a second quote for the same wallet and question failed
    4 times out of 4 (the documented code for that is `DUPLICATE_MARKET`), and 3 of 10 quotes for
    fresh, distinct drafts failed the same way.

    So a refusal that names no field is not evidence about the draft, and this tool will not
    present it as one. Telling a creator their market is malformed because somebody else's
    validator was flaky is the same false verdict this project exists to refuse.
    """
    text = str(error)
    if '"fields"' in text or "'fields'" in text:
        return REFUSED
    if "INVALID_MARKET_PARAMS" in text and "check server logs" in text:
        return INCONCLUSIVE
    if "HTTP 400" in text:
        return REFUSED
    return INCONCLUSIVE


def quote(draft, post=None, attempts=3, pause=1.0, sleep=time.sleep):
    """Ask Panta to validate the draft and price it. No signature, no broadcast, no payment.

    Returns `(payload, verdict, detail)` where verdict is PASSED, REFUSED or INCONCLUSIVE. The
    endpoint reserves a create session and returns the fee from on-chain config; nothing is
    charged until a transaction is built, signed by the creator's wallet and broadcast, none of
    which happens here.

    Inconclusive refusals are retried, because they are flaky rather than final. A refusal that
    names fields is final on the first answer and never retried — the draft really is wrong.
    """
    caller = post or panta.post
    detail = ""
    for attempt in range(attempts):
        try:
            return caller("markets/create/quote/", draft), PASSED, ""
        except panta.PantaError as error:
            detail = str(error)
            if read_refusal(error) == REFUSED:
                return None, REFUSED, detail
            if attempt + 1 < attempts:
                sleep(pause * (attempt + 1))
    return None, INCONCLUSIVE, detail


def report(draft, now, quoted=None, verdict=None, detail="", reach=None):
    findings = check_locally(draft, now)
    image = str(draft.get("imageUrl") or "").strip()
    if reach and _url(image) and not any(f.field == "imageUrl" for f in findings):
        ok, why = reach(image)
        if not ok:
            findings.append(Finding(
                WARN, "imageUrl", f"not reachable ({why})",
                "host the image where a reader can fetch it — the catalogue will show a hole "
                "where the market's picture should be. Panta's own validator does not object: a "
                "draft pointing at a 404 was quoted successfully, so this is our check, not "
                "theirs"))
    seen = what_a_buyer_will_see(draft)
    lines = []
    blocks = [f for f in findings if f.level == BLOCK]
    warns = [f for f in findings if f.level == WARN]

    lines.append(f"{len(blocks)} thing(s) would leave a buyer unable to read this market"
                 if blocks else "Nothing here would leave a buyer unable to read this market.")
    for finding in blocks + warns:
        lines.append(f"  {finding.level:5} {finding.field}: {finding.message}")
        if finding.fix:
            lines.append(f"        → {finding.fix}")

    lines.append("")
    lines.append("WHAT THE CATALOGUE WILL SHOW")
    lines.append(f"  title   {seen['title'] or '(empty — and the listing leaves it empty anyway)'}")
    lines.append(f"  oracle  {seen['oracle'] or '(empty)'}")
    lines.append("  resolutionRule  returned on a complete card — but 31 of 100 cards come back "
                 "stripped of it,")
    lines.append("                  with no field saying which shape you are holding")

    if verdict == REFUSED:
        lines += ["", f"PANTA SAYS  the draft was refused, naming the fields: {detail}"]
    elif verdict == INCONCLUSIVE:
        lines += ["", "PANTA SAYS  nothing usable. Their validator refused without naming a "
                      "field, which it also does for drafts it accepts seconds later, so this is "
                      "not evidence about your draft.",
                  f"  what came back   {detail or '(no detail)'}",
                  "  the local checks above still stand on their own."]
    elif quoted:
        fee = quoted.get("paymentUsdc")
        human = f"{int(fee) / 1_000_000:,.2f} USDC" if str(fee).isdigit() else str(fee)
        lines += ["", "PANTA SAYS  the draft passes their validation.",
                  f"  creation fee      {human}",
                  f"  event address     {quoted.get('expectedEventPda', '?')}",
                  f"  session expires   {quoted.get('expiresAt', '?')}",
                  "  nothing was signed, submitted or paid by this tool."]
    return "\n".join(lines), blocks
