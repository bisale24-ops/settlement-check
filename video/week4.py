"""Settlement Check — Colosseum weekly video update, week 4. One minute.

    ~/.venvs/video/bin/python ~/Desktop/KHLab/hack-nation/kit/video/render.py \
        video/week4.py --out video/week4.mp4 --max-seconds 60

Built, learned, next — as Colosseum asks. Every number comes from docs/live.json as of
2026-10-09 09:12 UTC (34 runs, 295 transactions, 40 settlements, 20 markets, one signer).
"""
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
VOICE = "en-US-AndrewNeural"

SCENES = [
    ("card:built",
     "Settlement Check, week four. The live feed now runs on its own. A scheduled job reads the "
     "market program through Solami every few hours and republishes the page. Thirty-four runs, "
     "two hundred ninety-five transactions read, forty settlements across twenty markets."),

    ("card:learned",
     "What the week confirmed: all forty were signed by the same single key. Every one of those "
     "markets tells traders it resolves through UMA, and none of the forty transactions touches "
     "UMA. Twelve of them landed after my last update, so this is a pattern, not one odd market."),

    ("card:next",
     "Done this week: the final Colosseum submission on October sixth, plus the Panta and Solami "
     "sidetracks. Next: the feed keeps running through judging, and every claim on the page links "
     "to a signature anyone can replay."),
]

CARDS = {
    "built": """<h1>Week 4 · the live feed runs itself</h1>
    <table>
      <tr><td>runs</td><td class=big><b>34</b> · scheduled, Solami RPC</td></tr>
      <tr><td>transactions read</td><td class=big><b>295</b></td></tr>
      <tr><td>settlements caught</td><td class=big><b>40</b> across <b>20</b> markets</td></tr>
    </table>
    <p class=foot>bisale24-ops.github.io/settlement-check · docs/live.json · checked 9 Oct 09:12 UTC</p>""",

    "learned": """<h1>40 of 40 · one signer</h1>
    <pre>signer   664h8sZvGwUx4hfqWYrewwvC7wenbKPTCFQTKZx5ghbR   40 / 40
card     "resolves via UMA"                             40 / 40
chain    UMA program in the transaction                  0 / 40
since 3 Oct   12 new settlements · 6 markets</pre>
    <p class=foot>reproducible: ./run.sh --replay &lt;signature&gt;</p>""",

    "next": """<h1>Done · next</h1>
    <table>
      <tr><td>6 Oct</td><td class=ok>final Colosseum submission</td></tr>
      <tr><td>2 Oct</td><td class=ok>Panta and Solami sidetracks submitted</td></tr>
      <tr><td>next</td><td>feed keeps running through judging · every claim links to a signature</td></tr>
    </table>""",
}
