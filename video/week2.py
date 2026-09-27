"""Settlement Check — Colosseum weekly video update, week 2. One minute.

    ~/.venvs/video/bin/python ~/Desktop/KHLab/hack-nation/kit/video/render.py \
        video/week2.py --out video/week2.mp4 --max-seconds 60

Colosseum asks three things of the weekly update: show what you built, share what you learned,
say what you will work on next. Private to the team, the judges and Colosseum. Narrated, not
spoken to camera; every number here is in the repository.
"""
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
VOICE = "en-US-AndrewNeural"

SCENES = [
    ("card:built",
     "Settlement Check, week two. What got built: a tool that reads a prediction market and asks "
     "what will decide it. Five verdicts on the live catalogue, a check that runs on a draft before "
     "the market exists, and a live watcher that reports each settlement as it lands, with who "
     "signed. Seventy tests, no dependencies, public repository, published report."),

    ("card:learned",
     "What I learned: my first findings were wrong. Five claims about the venue collapsed the "
     "moment I opened its own market page, where the question, the criteria and the sources are "
     "all shown. What survived is about the API. Thirteen of a hundred catalogue markets have no "
     "account on Solana at all, and the card arrives in two shapes with nothing saying which. The "
     "withdrawn claims are in the readme, next to their corrections."),

    ("card:next",
     "Next: re-cut the pitch around what survived, hear back from Panta on the seven API defects "
     "reported to them, and keep the watcher running live on Solami through the deadline."),
]

CARDS = {
    "built": """<h1>Week 2 · what got built</h1>
    <table>
      <tr><td>catalogue</td><td>five verdicts on what settles each market</td></tr>
      <tr><td><code>--check-draft</code></td><td>the same rules, before a market exists</td></tr>
      <tr><td><code>--watch</code></td><td>each settlement as it lands: claimed vs signed</td></tr>
      <tr><td>tests</td><td>70, no network, Python 3.9 and 3.13</td></tr>
    </table>
    <p class=sub>github.com/bisale24-ops/settlement-check · bisale24-ops.github.io/settlement-check</p>""",

    "learned": """<h1>What I learned</h1>
    <table>
      <tr><th>withdrawn after opening the venue's own page</th></tr>
      <tr><td>“most markets on sale state no question” — wrong field</td></tr>
      <tr><td>“the catalogue promises UMA” — a flag, not a promise</td></tr>
    </table>
    <table>
      <tr><th>what survived</th></tr>
      <tr><td><b>13 of 100</b> tradeable markets have no account on Solana</td></tr>
      <tr><td>cards arrive complete or stripped — <b>no label</b> says which</td></tr>
    </table>""",

    "next": """<h1>Next</h1>
    <table>
      <tr><td>pitch</td><td>re-cut around the findings that survived</td></tr>
      <tr><td>Panta</td><td>seven API defects reported; waiting on their reply</td></tr>
      <tr><td>live</td><td>watcher on Solami through the sidetrack deadline</td></tr>
    </table>""",
}
