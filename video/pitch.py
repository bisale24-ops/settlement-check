"""Settlement Check — the pitch video for Colosseum. Up to two minutes.

    ~/.venvs/video/bin/python ~/Desktop/KHLab/hack-nation/kit/video/render.py \
        video/pitch.py --out video/pitch.mp4 --max-seconds 118

Second cut. The first was built on findings that collapsed when the venue's own market page was
opened — the question, the criteria and the sources are shown there. This one carries only what
survived that check, which is about the API rather than the venue.

Colosseum asks the pitch video to introduce the builder, say what is being built, and say why
this is the person to build it. Narrated rather than spoken to camera; everything claimed here is
in the repository or reproducible from it.
"""
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
VOICE = "en-US-AndrewNeural"

SCENES = [
    ("card:who",
     "I'm Aleksandr Khrukalo. I build software on my own, from Bishkek, under the name K H Lab. "
     "Seven Android apps on the Amazon Appstore, Python tools and agents. No team, no funding, "
     "everything public."),

    ("card:why_me",
     "A store once rejected one of my apps for a file I could not see was missing. So I wrote the "
     "tool that reads a build the way the reviewer does, and that habit is all I build: something "
     "makes a claim, and I write the part that asks it for the receipt."),

    ("card:problem",
     "A prediction market is a claim with money behind it. Build on its API — a wallet, an "
     "aggregator, an agent — and you decide what your users can buy. Two questions are worth "
     "asking first: does this market exist, and can I tell what settles it?"),

    ("card:finding",
     "I measured it on a live venue. Thirteen of a hundred catalogue markets are served as "
     "tradeable and have no account on Solana; the venue's own page says market not found. The "
     "card arrives complete or stripped, and nothing says which. And the field that names the "
     "settler names the wallet that creates markets; the chain says one keypair signs every "
     "result."),

    ("card:product",
     "Settlement Check says so, in three places. For a buyer, the catalogue "
     "sorted by whether you can tell what you are buying. For a creator, a check that runs before "
     "the market is published and refuses one nobody could read. And live, each settlement as it "
     "lands, naming what was promised and who signed."),

    ("card:market",
     "Who needs it: anyone building on a prediction market's API, and the venues themselves. "
     "Their product already knows which markets do not exist; their API does not say. The gap is "
     "a filter and a flag away, and it is the same at every venue that follows."),

    ("card:how_i_work",
     "One last thing, about how I work. Five claims in this "
     "project were wrong, and all five are in the readme with their corrections. The largest was "
     "disproved by opening a market page. A tool that demands receipts has to show its own."),
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
    <p class=sub>Build on its API and you decide what your users can buy.</p>
    <table>
      <tr><th>ask the API</th><th>what it answers</th></tr>
      <tr><td>does this market exist?</td><td>it says <code>primary</code> either way</td></tr>
      <tr><td>what settles it?</td><td>a field that names the wrong account</td></tr>
    </table>""",

    "finding": """<h1>Measured, on a live venue</h1>
    <table>
      <tr><td><b>13 of 100</b></td><td>served as tradeable, no account on Solana — the venue's own page: <i>Market not found</i></td></tr>
      <tr><td><b>2 shapes</b></td><td>a card comes back complete or stripped; nothing says which</td></tr>
      <tr><td><b>1 keypair</b></td><td>signs every settlement; the <code>oracle</code> field names the creator</td></tr>
    </table>
    <p class=sub>Every number reproduces from <code>demo/census.py</code>.</p>""",

    "product": """<h1>Three places, one rule</h1>
    <table>
      <tr><td>buyer</td><td>the catalogue, sorted by what you can actually check</td></tr>
      <tr><td>creator</td><td>a draft refused before it is published, and before the fee</td></tr>
      <tr><td>live</td><td>each settlement as it lands: promised vs signed</td></tr>
    </table>""",

    "market": """<h1>Who needs it</h1>
    <p class=sub>Anyone building on a prediction market's API — and the venues, whose product
       already knows what their API does not say.</p>
    <table>
      <tr><th>the product shows</th><th>the API returns</th></tr>
      <tr><td>“Market not found on-chain”</td><td><code>phase: primary</code></td></tr>
      <tr><td>question, criteria, sources</td><td>present on some cards, absent on others, unlabelled</td></tr>
      <tr><td>agent resolution, dispute window</td><td>an <code>oracle</code> field naming the creator</td></tr>
    </table>""",

    "how_i_work": """<h1>How I work</h1>
    <table>
      <tr><th>five claims this project got wrong</th></tr>
      <tr><td>“91 of 100 state no question” — measured on the wrong field</td></tr>
      <tr><td>“one key decides” — read from the wallet that creates markets</td></tr>
      <tr><td>“the rule reaches nobody” — the venue shows it to buyers</td></tr>
      <tr><td>“the catalogue promises UMA” — it is a flag, not a promise</td></tr>
      <tr><td>“the public node can’t subscribe” — only when the stream is idle</td></tr>
    </table>
    <p class=sub>All five corrections are in the README.<br>
       github.com/bisale24-ops/settlement-check</p>""",
}
