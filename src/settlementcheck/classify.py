"""Five verdicts about how a market will be settled.

The question is never "will this resolve YES or NO". It is "when it resolves, what decided it, and
could anybody else have checked that decision". The answer comes from two facts that are already
public: whether the market states its question at all, and what kind of thing its `oracle` is.
"""
import dataclasses

UNSTATED = "unstated"
NAMED_NOTHING = "named-nothing"
EDITORIAL = "editorial"
ONE_KEY = "one-key"
VERIFIABLE = "verifiable"
UNKNOWN = "unknown"

ORDER = [UNSTATED, NAMED_NOTHING, ONE_KEY, EDITORIAL, UNKNOWN, VERIFIABLE]

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
    oracle: str
    detail: str            # what was found out about the oracle
    phase: str
    volume: float | None
    tradeable: bool

    @property
    def short(self):
        return self.market_id[:8] + "…"


def stated_question(card):
    """The question, from wherever the catalogue happens to be keeping it.

    The listing rows leave `title` empty on every market without exception, which is what made an
    earlier measurement of this catalogue read `description` alone and conclude that almost nothing
    states a question. That was wrong: open the market's own card and the question is in `title` on
    56 of 100 markets. Both fields are read here, and the card is what gets classified.
    """
    for field in ("title", "description"):
        text = (card.get(field) or "").strip()
        if text:
            return text
    return ""


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


def judge(card, owner_of, is_address):
    """Classify one market.

    `owner_of` and `is_address` are injected so the rule can be tested without a network, and so
    the on-chain lookup can come from any RPC — the public endpoint today, Solami later.
    """
    oracle = (card.get("oracle") or "").strip()
    question = stated_question(card)
    phase = (card.get("phase") or "").strip()
    common = dict(market_id=card.get("marketId", ""), question=question, oracle=oracle,
                  phase=phase, volume=volume_of(card),
                  tradeable=phase in ("primary", "secondary"))

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

    owner = owner_of(oracle)
    if owner is None:
        return Verdict(kind=UNKNOWN,
                       detail="the named account does not exist on mainnet", **common)
    if owner == "11111111111111111111111111111111":
        return Verdict(kind=ONE_KEY,
                       detail="a System Program account — a keypair, not an oracle", **common)
    return Verdict(kind=VERIFIABLE, detail=f"account owned by program {owner}", **common)


def group(verdicts):
    grouped = {kind: [] for kind in ORDER}
    for verdict in verdicts:
        grouped[verdict.kind].append(verdict)
    return grouped
