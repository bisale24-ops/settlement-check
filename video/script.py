"""Settlement Check — the demo video.

    ~/.venvs/video/bin/python ~/Desktop/KHLab/hack-nation/kit/video/render.py \
        video/script.py --out video/demo.mp4 --max-seconds 178

Second version. The first told a story that opening one market page disproved — that buyers cannot
see what decides a market. They can: the venue shows the question, the criteria and the sources.
What is true is about the API, and this is that story instead.

Every terminal frame under shots/ is real captured output. The one screenshot is panta.market
loaded without an account, so nothing personal is in frame, and no command here prints a key.
"""
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
VOICE = "en-US-AndrewNeural"

SCENES = [
    ("card:open",
     "If you build on a prediction market's API, you are deciding what your users can buy. So "
     "here are two questions worth asking of that API before you ship: does this market exist, "
     "and can I tell what settles it?"),

    ("term:ghosts",
     "On the live Panta catalogue, thirteen markets out of a hundred are served as tradeable and "
     "have no account on Solana at all. One call to any node returns null for every one of them."),

    ("shot:notfound",
     "And here is the same market on Panta's own site. The venue knows. A client reading the "
     "public API does not, and will offer all thirteen to its users."),

    ("term:report",
     "The second question is harder, because the card arrives in two shapes. A complete one "
     "carries the question, the resolution rule, the sources and the trade counts. A stripped one "
     "carries none of them, and nothing in the response says which you are holding."),

    ("card:shapes",
     "So a client that reads the question field gets a question for most markets and silence for "
     "the rest, and cannot tell a market with no question from a card that arrived empty. This "
     "tool reports the difference instead of guessing at it."),

    ("term:replay",
     "For what actually settles a market, it reads the chain rather than a field. The oracle field "
     "names the wallet that creates markets, not the one that resolves them. This is one "
     "settlement, decoded: which market closed, what the card claimed, and who signed."),

    ("card:chain",
     "On every settled market inspected, the result was submitted and the event closed by the "
     "same keypair, under both of the instruction naming families this program uses. Matching one "
     "and not the other reports a settled market as one that nothing has settled — which this "
     "tool did, until it was caught."),

    ("card:endpoint",
     "It runs live, and which endpoint you read from is a setting. Fourteen settled markets, the "
     "same code: the public node returns none of them under concurrency, Solami returns all "
     "fourteen in nine seconds. A quiet subscription is where the free node gives up, and "
     "watching settlements is nothing but a quiet subscription."),

    ("term:draft_bad",
     "The same rules run before a market exists. This draft is shaped like the catalogue and the "
     "check refuses it: a source of truth that is a word rather than a reference, and times that "
     "close trading before it opens."),

    ("term:draft_good",
     "A draft that passes goes to Panta's own validator and comes back priced. Fifty U S D C to "
     "create. Nothing is signed, submitted or paid — their model is quote, build, then the "
     "creator's wallet signs, and this stops at the first step."),

    ("card:wrong",
     "One more thing, because it is the point. Five claims this project made were wrong, and all "
     "five are in the readme with their corrections. The largest was disproved by opening a "
     "market page. A tool that asks for receipts has to show its own."),

    ("card:close",
     "Seventy tests, no network, no dependencies, green on two versions of Python. Everything "
     "here reproduces from a clone."),
]

CARDS = {
    "open": """<h1>Settlement Check</h1>
    <p class=sub>Two questions to ask a prediction market's API before you ship on it.</p>
    <table>
      <tr><th>question</th><th>what the API answers</th></tr>
      <tr><td>does this market exist?</td><td>it says <code>primary</code> either way</td></tr>
      <tr><td>what settles it?</td><td>a field that names the wrong account</td></tr>
    </table>""",

    "shapes": """<h1>Two shapes, no label</h1>
    <table>
      <tr><th>complete card</th><th>stripped card</th></tr>
      <tr><td><code>question</code></td><td>absent</td></tr>
      <tr><td><code>resolutionRule</code></td><td>absent</td></tr>
      <tr><td><code>sources</code></td><td>absent</td></tr>
      <tr><td><code>totalTrades</code>, <code>onChain</code></td><td>absent</td></tr>
    </table>
    <p class=sub>Nothing in the response distinguishes them. 17 of 100 arrive stripped.</p>""",

    "chain": """<h1>Read the chain, not the field</h1>
    <table>
      <tr><td><code>oracle</code> says</td><td>the wallet that runs <code>CreateEventUsdc</code></td></tr>
      <tr><td>the chain says</td><td><code>664h8sZvGwUx4hfq…</code> signed every settlement</td></tr>
      <tr><td>that account is</td><td>System-owned, no data — a key, not a program</td></tr>
    </table>
    <p class=sub>Two naming families: <code>ResolveEvent</code> and
       <code>ResolveEventUsdc</code>. Match one and a settled market looks unsettled.</p>""",

    "endpoint": """<h1>The endpoint is a setting</h1>
    <p class=sub>Fourteen settled markets, identical code.</p>
    <table>
      <tr><th>endpoint</th><th>in flight</th><th>read</th><th>time</th></tr>
      <tr><td>api.mainnet-beta.solana.com</td><td>6</td><td><b>0 of 14</b></td><td>refused</td></tr>
      <tr><td>Solami</td><td>6</td><td>14 of 14</td><td>41s</td></tr>
      <tr><td><b>Solami</b></td><td><b>24</b></td><td><b>14 of 14</b></td><td><b>9s</b></td></tr>
    </table>""",

    "wrong": """<h1>Five things this project got wrong</h1>
    <table>
      <tr><td>“91 of 100 state no question”</td><td>measured on the wrong field</td></tr>
      <tr><td>“one key decides”</td><td>read from the wallet that creates markets</td></tr>
      <tr><td>“the rule reaches nobody”</td><td>the venue shows it to buyers</td></tr>
      <tr><td>“the catalogue promises UMA”</td><td>it is a flag, not a promise</td></tr>
      <tr><td>“the public node can’t subscribe”</td><td>only when the stream is idle</td></tr>
    </table>""",

    "close": """<h1>Check it yourself</h1>
    <table>
      <tr><td>repository</td><td>github.com/bisale24-ops/settlement-check</td></tr>
      <tr><td>page</td><td>bisale24-ops.github.io/settlement-check</td></tr>
      <tr><td>tests</td><td>70, no network, Python 3.9 and 3.13</td></tr>
      <tr><td>dependencies</td><td>none — <code>run.sh</code> works from a clone</td></tr>
    </table>
    <p class=sub>Read-only throughout: nothing is signed, broadcast or paid.</p>""",
}

SHELL = {
    "ghosts": ("$ .venv/bin/python demo/ghosts.py", "ghosts.txt"),
    "report": ("$ ./run.sh --cards 20 --settlements 8 --workers 20", "report.txt", 0, 16),
    "replay": ("$ ./run.sh --replay 5u15kVt2wz1cnLMU…", "replay.txt"),
    "draft_bad": ("$ ./run.sh --check-draft draft.json", "draft-bad.txt", 0, 14),
    "draft_good": ("$ ./run.sh --check-draft draft.json", "draft-good.txt"),
}

IMAGES = {
    "notfound": "shots/panta-notfound.png",
}
