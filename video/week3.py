"""Settlement Check — Colosseum weekly video update, week 3. One minute.

    ~/.venvs/video/bin/python ~/Desktop/KHLab/hack-nation/kit/video/render.py \
        video/week3.py --out video/week3.mp4 --max-seconds 60

Built, learned, next — as Colosseum asks. Every number is in the repository: the re-measurement in
README.md and submission/panta.md, the live settlement in runs/watch.log and `./run.sh --replay`.
"""
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
VOICE = "en-US-AndrewNeural"

SCENES = [
    ("card:built",
     "Settlement Check, week three. The live watcher caught its first settlement as it happened, "
     "on October first, through Solami's Mirage stream. The market's card says it was sent to UMA. "
     "The chain says one key signed the result, and no UMA program is in the transaction. Anyone "
     "can replay it from the signature."),

    ("card:learned",
     "What I learned: Panta moved after the defect report. The listing cursor now advances and "
     "repeated reads agree, so the tool follows it. The thirteen markets with no account left the "
     "listing, but their cards still say tradeable. And the stripped card is not a property of a "
     "market at all: fourteen of thirty markets changed shape across four identical requests."),

    ("card:next",
     "Next: final submission on October sixth, then the Panta and Solami sidetracks, with the "
     "watcher running through the deadline."),
]

CARDS = {
    "built": """<h1>Week 3 · first live settlement</h1>
    <pre style="font-size:21px;line-height:1.5;text-align:left;background:#11151c;color:#e6e6e6;padding:18px 22px;border-radius:10px">18:00:06 UTC  SubmitOracleResultUsdc  8FLq9TjnV8jez7pn…
market   4yiz9ycF3PTwf6tMdTKTzFWNo9Yrph4XsSRHgPMpLpjG
claimed  world-stocks-bloomberg · card carries sentToUma
signed   664h8sZvGwUx4hfqWYrewwvC7wenbKPTCFQTKZx5ghbR
<b style="color:#7fd1a8">→ no UMA program in the transaction</b></pre>
    <p class=sub>caught by --watch --mirage (Solami) · reproducible with ./run.sh --replay &lt;signature&gt;</p>""",

    "learned": """<h1>Re-measured on 1 October</h1>
    <table>
      <tr><td>fixed after the report</td><td>cursor advances · repeated reads agree</td></tr>
      <tr><td>half fixed</td><td>13 no-account markets gone from the listing — cards still say tradeable</td></tr>
      <tr><td>new</td><td><b>14 of 30</b> cards change shape across 4 identical requests</td></tr>
    </table>
    <p class=sub>79 tests · demo/flips.py · demo/ghosts.py</p>""",

    "next": """<h1>Next</h1>
    <table>
      <tr><td>6 Oct</td><td>final Colosseum submission</td></tr>
      <tr><td>then</td><td>Panta and Solami sidetracks on Superteam Earn</td></tr>
      <tr><td>live</td><td>watcher on Mirage through 13 Oct</td></tr>
    </table>""",
}
