"""Four verdicts about how a market will be settled.

The question is never "will this resolve YES or NO". It is "when it resolves, what decided it, and
could anybody else have checked that decision". The answer comes from two facts that are already
public: whether the market states its question at all, and what kind of thing its `oracle` is.
"""
import dataclasses

UNSTATED = "unstated"
EDITORIAL = "editorial"
ONE_KEY = "one-key"
VERIFIABLE = "verifiable"
UNKNOWN = "unknown"

ORDER = [UNSTATED, ONE_KEY, EDITORIAL, UNKNOWN, VERIFIABLE]

HEADINGS = {
    UNSTATED: ("UNSTATED  the market carries no question — whatever settles it, nobody buying "
               "can know what they bought"),
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
    """Panta leaves `title` empty on every market in the catalogue; the question lives in
    `description`, when it is there at all."""
    for field in ("description", "title"):
        text = (card.get(field) or "").strip()
        if text:
            return text
    return ""


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
        detail = f"settled by {oracle}" if oracle else "no settlement source named either"
        return Verdict(kind=UNSTATED, detail=detail, **common)

    if not oracle:
        return Verdict(kind=UNKNOWN, detail="the market names no settlement source", **common)

    if not is_address(oracle):
        feeds = [f.strip() for f in oracle.split(",") if f.strip()]
        listed = ", ".join(feeds[:4]) + (f" and {len(feeds) - 4} more" if len(feeds) > 4 else "")
        return Verdict(kind=EDITORIAL, detail=f"{len(feeds)} newsroom feed(s): {listed}", **common)

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
