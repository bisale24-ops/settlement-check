"""The report: findings first, good news last, and the number that matters at the top.

A report that opens with a score is a report nobody reads to the end, so this opens with the one
comparison that carries the whole finding: of the markets you can still buy, how many say what you
are buying — set against the markets that are already over, where the question is always there.
"""
from . import classify
from .classify import (EDITORIAL, NAMED_NOTHING, ONE_KEY, ORDER, UNKNOWN, UNSTATED, VERIFIABLE)

EXIT_OK = 0
EXIT_FOUND = 1
EXIT_FAILED = 3


def money(value):
    return "volume not reported" if value is None else f"${value:,.0f}"


def known(verdicts):
    return [v.volume for v in verdicts if v.volume is not None]


def total(verdicts):
    values = known(verdicts)
    return sum(values) if values else None


def silent(verdicts):
    return sum(1 for v in verdicts if v.volume is None)


def share(part, whole):
    return f"{round(100 * part / whole)}%" if whole else "—"


def headline(verdicts):
    """Open with the split, because the split is the finding.

    A market that states its question only once it is over has told nobody anything: the people who
    could act on it have already acted. So the two populations are counted apart, and the report
    says plainly when one of them is clean.
    """
    tradeable = [v for v in verdicts if v.tradeable]
    settled = [v for v in verdicts if not v.tradeable]
    mute = lambda group: [v for v in group if v.kind == UNSTATED]  # noqa: E731
    quiet = silent(verdicts)
    lines = [
        f"{len(verdicts)} markets read, {money(total(verdicts))} of reported volume behind them"
        + (f" ({quiet} reported none)." if quiet else "."),
    ]
    if tradeable:
        blind = mute(tradeable)
        lines.append(
            f"Of the {len(tradeable)} you can buy right now, {len(blind)} "
            f"({share(len(blind), len(tradeable))}) do not say what you are buying — "
            f"{money(total(blind))} of {money(total(tradeable))}.")
    if settled:
        blind = mute(settled)
        lines.append(
            f"Of the {len(settled)} already settled, "
            + (f"every one states its question." if not blind
               else f"{len(blind)} ({share(len(blind), len(settled))}) still do not."))
    nothing = [v for v in verdicts if v.kind == NAMED_NOTHING]
    if nothing:
        words = sorted({v.oracle for v in nothing})
        lines.append(
            f"{len(nothing)} market(s) name their settlement source as "
            f"{', '.join(map(repr, words[:2]))} — a word, not a reference; "
            f"{money(total(nothing))} rides on it.")
    keys = {v.oracle for v in verdicts if v.kind == ONE_KEY}
    if keys:
        controlled = [v for v in verdicts if v.kind == ONE_KEY]
        lines.append(
            f"{len(controlled)} market(s) are settled by {len(keys)} wallet(s); "
            f"{money(total(controlled))} rides on those signatures.")
    return lines


def render(verdicts, show=6, settler_activity=None):
    grouped = classify.group(verdicts)
    out = headline(verdicts) + [""]
    for kind in ORDER:
        entries = sorted(grouped[kind], key=lambda v: -(v.volume or 0))
        if not entries:
            if kind == VERIFIABLE:
                out += [f"{classify.HEADINGS[kind]}  (0)",
                        "  Nothing in this catalogue settles from a source a reader can audit.", ""]
            continue
        volume = total(entries)
        out.append(f"{classify.HEADINGS[kind]}  ({len(entries)}, {money(volume)})")
        for verdict in entries[:show]:
            label = verdict.question[:96] or "(no question stated)"
            out.append(f"  {label}")
            out.append(f"      {verdict.short}  {verdict.phase}  {money(verdict.volume)}"
                       f"{'  tradeable' if verdict.tradeable else ''}")
            out.append(f"      {verdict.detail}")
        if len(entries) > show:
            out.append(f"  … and {len(entries) - show} more")
        out.append("")
    if settler_activity:
        out.append("THE WALLET THAT SETTLES THEM")
        for address, facts in settler_activity.items():
            out.append(f"  {address}")
            out.append(f"      {facts['markets']} market(s) in this sample, "
                       f"{money(facts['volume'])} of volume")
            out.append(f"      {facts['signatures']} recent signature(s); "
                       f"calls {', '.join(sorted(facts['programs'])[:3])}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def exit_code(verdicts):
    found = (UNSTATED, NAMED_NOTHING, ONE_KEY)
    return EXIT_FOUND if any(v.kind in found for v in verdicts) else EXIT_OK
