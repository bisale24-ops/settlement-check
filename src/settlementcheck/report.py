"""The report: findings first, good news last, and the number that matters at the top.

A report that opens with a score is a report nobody reads to the end, so this opens with the
money: how much volume sits on markets that never say what they are about.
"""
from . import classify
from .classify import EDITORIAL, ONE_KEY, ORDER, UNKNOWN, UNSTATED, VERIFIABLE

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


def headline(verdicts):
    unstated = [v for v in verdicts if v.kind == UNSTATED]
    live = [v for v in unstated if v.tradeable]
    keys = {v.oracle for v in verdicts if v.kind == ONE_KEY}
    quiet = silent(verdicts)
    lines = [
        f"{len(verdicts)} markets read, {money(total(verdicts))} of reported volume behind them"
        + (f" ({quiet} reported none)." if quiet else "."),
        f"{len(unstated)} of them state no question at all — {money(total(unstated))} of that"
        f" volume, and {len(live)} still tradeable right now.",
    ]
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
    return EXIT_FOUND if any(v.kind in (UNSTATED, ONE_KEY) for v in verdicts) else EXIT_OK
