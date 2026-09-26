"""Five verdicts about how a market will be settled.

The question is never "will this resolve YES or NO". It is "when it resolves, what decided it, and
could anybody else have checked that decision". The answer comes from two facts that are already
public: whether the market states its question at all, and what kind of thing its `oracle` is.
"""
from __future__ import annotations

import dataclasses

UNSTATED = "unstated"
NAMED_NOTHING = "named-nothing"
EDITORIAL = "editorial"
ONE_KEY = "one-key"
VERIFIABLE = "verifiable"
UNKNOWN = "unknown"

ORDER = [UNSTATED, NAMED_NOTHING, ONE_KEY, EDITORIAL, UNKNOWN, VERIFIABLE]

# Returned by a settlement lookup that never ran — the budget was spent, or the endpoint refused.
# It is a separate value from None, which means "looked, and this market has not settled yet".
# Collapsing the two is how a tool comes to print "nobody settled this" about a market it never
# opened, which is the same false clean bill this project exists to refuse.
NOT_LOOKED = object()

HEADINGS = {
    UNSTATED: ("UNSTATED  the market carries no question — whatever settles it, nobody buying "
               "can know what they bought"),
    NAMED_NOTHING: ("NAMED NOTHING  the settlement source is a word, not a reference: no address "
                    "to look up, no program to read, no outlet to ask"),
    ONE_KEY: ("ONE KEY  the question is stated and one wallet decides it. No program, no feed, "
              "no second signature"),
    EDITORIAL: ("EDITORIAL  the question is stated and named newsrooms decide it. Nobody can "
                "reproduce the call from the chain"),
    UNKNOWN: "NOT CHECKED  the settlement source could not be read",
    VERIFIABLE: ("VERIFIABLE  settlement rests on an on-chain account holding program state, "
                 "which anyone can read for themselves"),
}


@dataclasses.dataclass
class Verdict:
    market_id: str
    kind: str
    question: str          # the stated question, or "" when there is none
    oracle: str            # what the catalogue CLAIMS decides it
    detail: str            # what was found out about the oracle
    phase: str
    volume: float | None
    tradeable: bool
    claims_uma: bool = False       # the catalogue's `sentToUma`
    settled_by: tuple = ()         # who signed the settlement on chain, read from the market
    settlement_seen: tuple = ()    # which settlement instructions were found

    @property
    def short(self):
        return self.market_id[:8] + "…"

    @property
    def claim_versus_chain(self):
        """The one line a buyer needs: what was promised, and what the chain shows.

        Returns None when there is nothing to compare — the market has not settled yet, or the
        lookup was skipped.
        """
        if not self.settled_by:
            return None
        who = ", ".join(sorted(self.settled_by))
        if self.claims_uma:
            # `sentToUma` is a flag in the API, not a promise the venue makes to its users: its
            # own page says agent resolution, with a confidence score and a dispute window. So
            # this reports the flag and the signature side by side and draws no conclusion the
            # reader cannot check.
            return (f"the card carries sentToUma; on chain the result was submitted and the event "
                    f"resolved by {who}, and no UMA program appears in that transaction")
        if self.oracle and self.oracle not in self.settled_by:
            return f"the catalogue names {self.oracle} as the oracle; on chain it was {who}"
        return f"settled on chain by {who}"


def stated_question(card):
    """The question, from wherever this card happens to carry it.

    Three drafts of this function were wrong, each in the same way: a field was read, a sample was
    taken, and a claim about the venue was made from it.

    What is actually there. A complete card carries `question` and `resolutionRule` outright. A
    stripped card carries neither, and also loses `sources`, `totalTrades`, `totalVolume`,
    `isResolved` and a field named `onChain`. Measured 26 September 2026 over the hundred markets
    the API will hand over: 69 complete, 31 stripped — and 13 of the stripped ones have no Solana
    account at all, which Panta's own site renders as "Market not found on-chain".

    So the question is read from `question` first, and a market without one is a market whose card
    was stripped, not a market whose author wrote nothing.
    """
    for field in ("question", "title", "description"):
        text = (card.get(field) or "").strip()
        if text:
            return text
    return ""


def stated_rule(card):
    """The resolution criteria, when this card carries them at all."""
    return (card.get("resolutionRule") or "").strip()


def is_stripped(card):
    """A card with none of the fields that say what the market is or how it settles."""
    return not (stated_question(card) or stated_rule(card) or card.get("sources"))


# Tokens that assert a mechanism instead of naming a publisher. `on-chain` is the single most
# common value in the whole `oracle` field — more common than any newsroom or any wallet — and it
# is the one claim in this catalogue that can be checked on its own terms: if a settlement really
# is on-chain, there is an account, and the identifier has to carry the address so a reader can
# open it. These carry none.
#
# Deliberately a short, literal list rather than a shape rule. A shape rule — "an outlet id has at
# least three dash-separated parts" — was tried first and was wrong: `global-ap`, `global-bbc` and
# `global-reuters` are real mastheads with two. Everything not named here is treated as an outlet.
MECHANISM_ONLY = frozenset({"on-chain", "onchain", "on_chain", "chain"})


def names_a_source(token):
    """Could a reader go and check this token, or is it only a word?"""
    return token.strip().lower() not in MECHANISM_ONLY


def feeds_of(oracle):
    return [feed.strip() for feed in oracle.split(",") if feed.strip()]


def volume_of(card):
    """Traded volume, or None when the catalogue does not report it.

    The same request returns this field populated on one call and absent on the next, so a
    missing figure is reported as missing. Printing $0 for "not reported" would be the false
    clean bill this tool exists to refuse.
    """
    for field in ("totalVolumeUsdc", "volumeUsdc", "primaryVolume"):
        value = card.get(field)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def judge(card, owner_of, is_address, settlement_of=None):
    """Classify one market.

    `owner_of`, `is_address` and `settlement_of` are injected so the rule can be tested without a
    network, and so the on-chain lookup can come from any RPC — the public endpoint today, Solami
    later.

    `settlement_of(market_id)` returns what the market's own transaction history shows, or None
    when it has not settled yet. **It takes precedence over everything the catalogue says.** The
    `oracle` field is a claim; the signature on `SubmitOracleResultUsdc` is what happened.
    """
    oracle = (card.get("oracle") or "").strip()
    question = stated_question(card)
    phase = (card.get("phase") or "").strip()
    market_id = card.get("marketId", "")
    found = settlement_of(market_id) if settlement_of else NOT_LOOKED
    looked = found is not NOT_LOOKED
    common = dict(market_id=market_id, question=question, oracle=oracle,
                  phase=phase, volume=volume_of(card),
                  tradeable=phase in ("primary", "secondary"),
                  claims_uma=bool(card.get("sentToUma")),
                  settled_by=tuple(sorted(found["signers"])) if looked and found else (),
                  settlement_seen=tuple(sorted(found["instructions"])) if looked and found else ())

    if looked and found and len(found["signers"]) == 1 and question:
        who = next(iter(found["signers"]))
        owner = owner_of(who)
        if owner == "11111111111111111111111111111111":
            return Verdict(kind=ONE_KEY, detail=(
                f"one keypair signed {' and '.join(sorted(found['instructions']))} — "
                f"{who}"), **common)
        if owner is not None:
            return Verdict(kind=VERIFIABLE, detail=(
                f"settled by {who}, an account owned by program {owner}"), **common)

    if not question:
        if not oracle:
            detail = "no settlement source named either"
        elif not is_address(oracle) and not any(map(names_a_source, feeds_of(oracle))):
            detail = f"settled by {oracle!r} — a word, not a reference"
        else:
            detail = f"settled by {oracle}"
        return Verdict(kind=UNSTATED, detail=detail, **common)

    if not oracle:
        return Verdict(kind=UNKNOWN, detail="the market names no settlement source", **common)

    if not is_address(oracle):
        feeds = feeds_of(oracle)
        named = [feed for feed in feeds if names_a_source(feed)]
        if not named:
            return Verdict(kind=NAMED_NOTHING,
                           detail=f"the settlement source is {', '.join(map(repr, feeds))} — "
                                  f"not an address, not a program, not an outlet", **common)
        listed = ", ".join(named[:4]) + (f" and {len(named) - 4} more" if len(named) > 4 else "")
        detail = f"{len(named)} newsroom feed(s): {listed}"
        unnamed = [feed for feed in feeds if feed not in named]
        if unnamed:
            detail += f"; {len(unnamed)} naming nothing: {', '.join(map(repr, unnamed[:3]))}"
        return Verdict(kind=EDITORIAL, detail=detail, **common)

    # An address in `oracle` is a claim about who will decide, and this tool used to take it as the
    # answer. It is not: on every market checked, that address is the wallet whose instruction is
    # `CreateEventUsdc`. Until the market settles and the chain can be read, the honest verdict is
    # that nothing has been decided yet — and the detail says what was claimed and what it is.
    owner = owner_of(oracle)
    if owner is None:
        return Verdict(kind=UNKNOWN,
                       detail=f"the catalogue names {oracle} as the oracle; no such account "
                              f"exists on mainnet", **common)
    kind_of_thing = ("a keypair somebody controls" if owner == "11111111111111111111111111111111"
                     else f"an account owned by program {owner}")
    because = ("nothing has settled this market on chain yet" if looked
               else "its settlement was not read — raise --settlements to check it")
    return Verdict(kind=UNKNOWN,
                   detail=f"the catalogue names {oracle} as the oracle — {kind_of_thing}. "
                          f"The claim is untested: {because}",
                   **common)


def group(verdicts):
    grouped = {kind: [] for kind in ORDER}
    for verdict in verdicts:
        grouped[verdict.kind].append(verdict)
    return grouped
