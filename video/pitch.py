"""Settlement Check — the pitch video for Colosseum. Up to two minutes.

    ~/.venvs/video/bin/python ~/Desktop/KHLab/hack-nation/kit/video/render.py \
        video/pitch.py --out video/pitch.mp4 --max-seconds 118

Colosseum asks the pitch video to introduce the builder, say what is being built, and say why
this is the person to build it. It is narrated rather than spoken to camera; everything claimed
here is either in the repository or reproducible from it.
"""
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
VOICE = "en-US-AndrewNeural"

SCENES = [
    ("card:who",
     "I'm Aleksandr Khrukalo. I build software on my own, from Bishkek, under the name K H Lab. "
     "Seven Android apps live on the Amazon Appstore, plus Python tools and agents. No team, no "
     "funding, and everything I ship is public."),

    ("card:why_me",
     "A store once rejected one of my apps for a file I could not see was missing. Three days to "
     "get back to a published app. So I wrote the tool that reads a build the way the reviewer "
     "does. That is the only thing I build: something makes a claim, and I write the part that "
     "asks it for the receipt."),

    ("card:problem",
     "A prediction market is a claim with money behind it. It says what it will pay out on, and "
     "who will decide. Both of those are worth checking before you buy, and almost nobody does."),

    ("card:finding",
     "So I measured it on a live venue. Every settled market states its question. Three to four "
     "out of five still on sale state none — the question appears once nobody can act on it. "
     "Eighty five of a hundred are flagged as settled by an optimistic oracle; on chain one "
     "keypair submitted every result, with no assertion from it anywhere."),

    ("card:product",
     "Settlement Check is the tool that says so, in three places. For a buyer, the catalogue "
     "sorted by whether you can tell what you are buying. For a creator, a check that runs before "
     "the market is published and refuses one nobody could read. And live, each settlement as it "
     "lands, naming what was promised and who actually signed."),

    ("card:market",
     "The people who need this are the venues themselves. Every market here was created through "
     "an interface that demanded a question, a resolution rule and sources — and the interface "
     "buyers read returns none of them. The data exists, it is just not shown. That is fixable, "
     "and it is the same at every venue that follows."),

    ("card:how_i_work",
     "One last thing, because it is how I work rather than what I built. Two numbers in this "
     "project were wrong, and both corrections are still in the readme next to them. A tool that "
     "demands receipts has to show its own."),
]

CARDS = {
    "who": """<h1>Aleksandr Khrukalo</h1>
    <p class=sub>Solo builder, Bishkek, Kyrgyzstan · KHLab</p>
    <table>
      <tr><td>shipped</td><td>7 Android apps live on the Amazon Appstore</td></tr>
      <tr><td>also</td><td>Python developer tools and agents, all public</td></tr>
      <tr><td>team</td><td>one</td></tr>
    </table>""",

    "why_me": """<h1>Why me</h1>
    <p class=sub>A store rejected my app for a file I could not see was missing.<br>
       Three days and two uploads to get back to a published app.</p>
    <table>
      <tr><th>the habit that came out of it</th></tr>
      <tr><td>something makes a claim → write the part that asks for the receipt</td></tr>
    </table>""",

    "problem": """<h1>A market is a claim with money behind it</h1>
    <table>
      <tr><th>before you buy, you want to know</th><th>can you find out?</th></tr>
      <tr><td>what am I betting on</td><td>often: no</td></tr>
      <tr><td>what will decide it</td><td>a string — and not the one that signs</td></tr>
    </table>""",

    "finding": """<h1>Measured, on a live venue</h1>
    <table>
      <tr><th></th><th>markets</th><th>state no question</th></tr>
      <tr><td>already settled</td><td>193</td><td><b>0</b></td></tr>
      <tr><td>still on sale</td><td>107</td><td>76–85%</td></tr>
    </table>
    <p class=sub>85 of 100 flagged as settled by an optimistic oracle.
       On chain: one keypair, no assertion, no dispute window.</p>""",

    "product": """<h1>Three places, one rule</h1>
    <table>
      <tr><td>buyer</td><td>the catalogue, sorted by what you can actually check</td></tr>
      <tr><td>creator</td><td>a draft refused before it is published, and before the fee</td></tr>
      <tr><td>live</td><td>each settlement as it lands: promised vs signed</td></tr>
    </table>""",

    "market": """<h1>Who needs it</h1>
    <p class=sub>The venues. The create API demands a question, a resolution rule and sources.
       The read API returns none of them.</p>
    <table>
      <tr><th>creator must write</th><th>buyer can read</th></tr>
      <tr><td>question</td><td>on the card only, never in the listing</td></tr>
      <tr><td>resolution rule, up to 2048 chars</td><td><b>nothing</b></td></tr>
      <tr><td>sources of truth</td><td>joined into one string</td></tr>
    </table>""",

    "how_i_work": """<h1>How I work</h1>
    <table>
      <tr><th>two numbers this project got wrong</th></tr>
      <tr><td>“91 of 100 state no question” — measured on the wrong field</td></tr>
      <tr><td>“one key decides” — read from the wallet that creates markets</td></tr>
    </table>
    <p class=sub>Both corrections are in the README, next to the numbers.<br>
       github.com/bisale24-ops/settlement-check</p>""",
}
