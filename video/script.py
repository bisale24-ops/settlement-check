"""Settlement Check — the demo video.

    ~/.venvs/video/bin/python ~/Desktop/KHLab/hack-nation/kit/video/render.py \
        video/script.py --length-only
    ~/.venvs/video/bin/python ~/Desktop/KHLab/hack-nation/kit/video/render.py \
        video/script.py --out video/demo.mp4 --max-seconds 178

Every terminal frame under shots/ is real captured output, written by running the tool against the
live catalogue and mainnet. Nothing is retyped for the camera, and nothing in these files names a
path, a user or a key — there is a test that fails if a command ever prints the key.
"""
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
VOICE = "en-US-AndrewNeural"

SCENES = [
    ("card:open",
     "A prediction market is a claim about the future. Before you buy into one, there are two "
     "things you would want to know. What question am I betting on, and what will decide it."),

    ("card:split",
     "On the live Panta catalogue, neither is reliably there. Of the markets already settled, "
     "every single one states its question. Of the ones you can still buy, three to four out of "
     "five state none. The question appears once nobody can act on it."),

    ("term:report",
     "This is the tool reading the catalogue. Twenty six markets, the two populations counted "
     "apart, and one line that matters more than the rest. Seven markets settled by a single "
     "wallet."),

    ("term:claim",
     "Here is that line. The catalogue says this market was settled by U M A, the optimistic "
     "oracle. On Solana, the result was submitted and the event closed by one keypair, with no "
     "U M A assertion in the transaction. The claim is in the interface, not on the chain."),

    ("shot:page_uma",
     "That verdict is not read from a field. It comes from the market's own history: who signed "
     "submit oracle result, and who signed resolve event. The oracle field names a different "
     "wallet — the one that creates markets."),

    ("term:replay",
     "Replay runs the same path over one settlement that already happened. Which market closed, "
     "what was promised, who actually signed it."),

    ("card:live",
     "And it runs live. Watch subscribes to the market program and reports each settlement as it "
     "lands. Where a plan has no websocket, poll mode follows the signature list instead — a few "
     "seconds behind a stream, and it works anywhere."),

    ("card:endpoint",
     "The endpoint is a setting, and the difference is measured. Fourteen settled markets, six "
     "lookups in flight: the public node returned none of them, Solami returned all fourteen."),

    ("shot:page_creator",
     "And here is why any of this happens. The create A P I requires a question, a resolution "
     "rule, and a list of sources. The read A P I returns none of them. Oracle is that source "
     "list joined by commas — which is why the commonest settlement source in the catalogue is "
     "the word on chain, typed in by a person."),

    ("term:draft_bad",
     "So the same rules run before a market exists. This draft is shaped like the catalogue, and "
     "the check refuses it: no question, a source that is a word, and times that close trading "
     "before it opens."),

    ("term:draft_good",
     "A draft that passes goes to Panta's own validator and comes back priced: fifty U S D C. "
     "Nothing is signed, submitted or paid — their model is quote, build, then the creator's "
     "wallet signs, and this stops at the first step."),

    ("card:close",
     "Sixty four tests, no network, no dependencies. Two numbers this project got wrong are "
     "still in the readme with their corrections, because a tool that demands receipts has to "
     "show its own."),
]

CARDS = {
    "open": """<h1>Settlement Check</h1>
    <p class=sub>What decides this prediction market — and could anyone else have checked that?</p>
    <table>
      <tr><th>before you buy</th><th>the catalogue tells you</th></tr>
      <tr><td>what am I betting on</td><td>often nothing at all</td></tr>
      <tr><td>what will settle it</td><td>a string, and not the one that signs</td></tr>
    </table>""",

    "split": """<h1>The question appears once it is too late</h1>
    <p class=sub>Three passes over the live catalogue, every card opened.
       Reproduce with <code>demo/census.py</code>.</p>
    <table>
      <tr><th>pass</th><th>on sale</th><th>no question</th><th>settled</th><th>no question</th></tr>
      <tr><td>1</td><td>40</td><td>34 &nbsp;(85%)</td><td>60</td><td><b>0</b></td></tr>
      <tr><td>2</td><td>50</td><td>42 &nbsp;(84%)</td><td>50</td><td><b>0</b></td></tr>
      <tr><td>3</td><td>17</td><td>13 &nbsp;(76%)</td><td>83</td><td><b>0</b></td></tr>
    </table>""",

    "live": """<h1>Live, on either transport</h1>
    <table>
      <tr><th>mode</th><th>how</th><th>needs</th></tr>
      <tr><td><code>--watch</code></td><td>logsSubscribe on the market program</td>
          <td>a plan with websockets</td></tr>
      <tr><td><code>--watch --poll</code></td><td>the signature list, every few seconds</td>
          <td>RPC only — any plan</td></tr>
      <tr><td><code>--replay</code></td><td>one settlement that already landed</td>
          <td>RPC only</td></tr>
    </table>
    <p class=sub>Same <code>describe()</code>, same line, whichever way the event arrives.</p>""",

    "endpoint": """<h1>The endpoint is a setting, and the difference is measured</h1>
    <p class=sub>Fourteen settled markets, <code>--workers 6</code>, identical code.</p>
    <table>
      <tr><th>endpoint</th><th>read</th><th>wall clock</th></tr>
      <tr><td>api.mainnet-beta.solana.com</td><td><b>0 of 14</b></td>
          <td>refused everything under concurrency</td></tr>
      <tr><td>Solami RPC</td><td><b>14 of 14</b></td>
          <td>101s — against 206s one at a time</td></tr>
    </table>""",

    "close": """<h1>Check it yourself</h1>
    <table>
      <tr><td>repository</td><td>github.com/bisale24-ops/settlement-check</td></tr>
      <tr><td>page</td><td>bisale24-ops.github.io/settlement-check</td></tr>
      <tr><td>tests</td><td>64, on Python 3.9 and 3.13, no network</td></tr>
      <tr><td>dependencies</td><td>none — <code>run.sh</code> works from a clone</td></tr>
    </table>
    <p class=sub>Read-only throughout: nothing is signed, broadcast or paid.</p>""",
}

SHELL = {
    "report": ("$ ./run.sh --cards 26 --settlements 10 --workers 6", "report.txt", 0, 16),
    "claim": ("", "report.txt", 17, 26),
    "replay": ("$ ./run.sh --replay 5u15kVt2wz1cnLMU…", "replay.txt"),
    "draft_bad": ("$ ./run.sh --check-draft draft.json", "draft-bad.txt", 0, 14),
    "draft_good": ("$ ./run.sh --check-draft draft.json", "draft-good.txt"),
}

IMAGES = {
    "page_uma": "shots/page-uma.png",
    "page_creator": "shots/page-creator.png",
}
