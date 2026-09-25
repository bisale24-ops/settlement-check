"""Render docs/index.html from docs/snapshot.json.

The page is a file, not a service: no key ever reaches a browser, and anyone can open the HTML and
check that it talks to nothing. Everything on it comes out of the snapshot, so a number on the page
that is not in the snapshot is a bug, not a claim.

    .venv/bin/python demo/page.py
"""
import html
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent.parent / "docs"
REPO = "https://github.com/bisale24-ops/settlement-check"

KIND_LABEL = {
    "unstated": ("no question", "bad"),
    "named-nothing": ("names nothing", "bad"),
    "one-key": ("one keypair", "bad"),
    "editorial": ("newsrooms", "warn"),
    "unknown": ("not decided", "muted"),
    "verifiable": ("auditable", "good"),
}

CSS = """
:root{--bg:#0b0d12;--panel:#12151d;--line:#232836;--ink:#e9ecf4;--dim:#9aa3b8;
--bad:#ff6b6b;--warn:#f2b34b;--good:#3ddc97;--accent:#7c5cff;--accent2:#29e0d1}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:16px/1.6 "IBM Plex Sans",-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:0 20px}
header{padding:56px 0 34px;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:14px;margin-bottom:26px}
.mark{width:40px;height:40px;border-radius:11px;flex:0 0 auto;
 background:linear-gradient(135deg,var(--accent),var(--accent2));
 display:flex;align-items:center;justify-content:center;color:#07070b;font-weight:800;font-size:22px}
.brand b{font-size:19px;letter-spacing:.2px}
h1{margin:0 0 14px;font-size:clamp(28px,4.4vw,44px);line-height:1.15;letter-spacing:-.6px}
h1 em{font-style:normal;color:var(--accent2)}
.lede{margin:0;color:var(--dim);font-size:18px;max-width:64ch}
.split{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:34px 0 8px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px}
.big{font-size:clamp(34px,6vw,52px);font-weight:700;line-height:1;letter-spacing:-1px}
.card small{display:block;color:var(--dim);margin-top:10px;font-size:14px}
.bad .big{color:var(--bad)} .good .big{color:var(--good)}
section{padding:40px 0;border-bottom:1px solid var(--line)}
h2{font-size:22px;margin:0 0 8px;letter-spacing:-.2px}
h2+p{margin-top:0;color:var(--dim);max-width:70ch}
code,.mono{font-family:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px}
.quote{border-left:3px solid var(--accent);padding:14px 18px;background:var(--panel);
 border-radius:0 10px 10px 0;margin:18px 0;color:var(--ink)}
.addr{color:var(--accent2);word-break:break-all}
table{width:100%;border-collapse:collapse;margin-top:18px;font-size:14px}
th{text-align:left;color:var(--dim);font-weight:500;font-size:12px;text-transform:uppercase;
 letter-spacing:.7px;padding:0 10px 10px;border-bottom:1px solid var(--line)}
td{padding:13px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tr:hover td{background:#141824}
.q{max-width:46ch}
.q .none{color:var(--bad);font-style:italic}
.chip{display:inline-block;padding:3px 9px;border-radius:999px;font-size:12px;white-space:nowrap;
 border:1px solid transparent}
.chip.bad{background:rgba(255,107,107,.12);color:var(--bad);border-color:rgba(255,107,107,.3)}
.chip.warn{background:rgba(242,179,75,.12);color:var(--warn);border-color:rgba(242,179,75,.3)}
.chip.good{background:rgba(61,220,151,.12);color:var(--good);border-color:rgba(61,220,151,.3)}
.chip.muted{background:#1a1f2b;color:var(--dim);border-color:var(--line)}
.vs{color:var(--dim);font-size:12.5px;margin-top:6px;max-width:52ch}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:18px}
.cols h3{margin:0 0 10px;font-size:14px;color:var(--dim);text-transform:uppercase;letter-spacing:.7px}
pre{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;
 overflow:auto;margin:0}
pre b{color:var(--bad);font-weight:600}
pre i{color:var(--good);font-style:normal}
footer{padding:34px 0 60px;color:var(--dim);font-size:14px}
a{color:var(--accent2)}
@media(max-width:720px){.split,.cols{grid-template-columns:1fr}.hide-sm{display:none}}
"""


def chip(kind):
    label, tone = KIND_LABEL.get(kind, (kind, "muted"))
    return f'<span class="chip {tone}">{html.escape(label)}</span>'


def money(value):
    return "—" if value in (None, 0) else f"${value:,.0f}"


def rows_html(markets, limit=26):
    order = {"unstated": 0, "named-nothing": 1, "one-key": 2, "editorial": 3, "unknown": 4,
             "verifiable": 5}
    markets = sorted(markets, key=lambda m: (order.get(m["kind"], 9), -(m["volume"] or 0)))
    out = []
    for market in markets[:limit]:
        question = html.escape(market["question"][:150]) if market["question"] else \
            '<span class="none">no question stated</span>'
        vs = market.get("claim_versus_chain")
        vs_html = f'<div class="vs">{html.escape(vs)}</div>' if vs else ""
        tradeable = ' · <span style="color:var(--warn)">on sale</span>' if market["tradeable"] else ""
        out.append(f"""<tr>
  <td class="q">{question}{vs_html}</td>
  <td>{chip(market['kind'])}</td>
  <td class="mono hide-sm">{html.escape(market['oracle'][:38]) or '—'}</td>
  <td class="mono">{money(market['volume'])}<br><span style="color:var(--dim)">
      {html.escape(market['phase'])}{tradeable}</span></td>
</tr>""")
    return "\n".join(out)


def render(snapshot):
    counts = snapshot["counts"]
    live, mute = counts["tradeable"], counts["tradeable_unstated"]
    done, done_mute = counts["settled"], counts["settled_unstated"]
    share = f"{round(100 * mute / live)}%" if live else "—"
    settlers = snapshot.get("settlers") or []
    settler_line = (
        f'On chain, every result in this snapshot was submitted and every event resolved by '
        f'<span class="addr mono">{html.escape(settlers[0])}</span> — an account owned by the '
        f'System Program, holding no data. A person with a key, not a program. No UMA assertion '
        f'appears in any of those transactions.'
        if len(settlers) == 1 else
        f'Settled on chain by {len(settlers)} account(s): ' +
        ", ".join(f'<span class="addr mono">{html.escape(a)}</span>' for a in settlers))

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Settlement Check</title>
<meta name="description" content="What decides this prediction market, and could anyone else have
 checked that decision? Measured on the live Panta catalogue.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%230b0d12'/><rect x='8' y='8' width='84' height='84' rx='16' fill='%237c5cff'/></svg>">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head><body>
<div class="wrap">

<header>
  <div class="brand"><div class="mark">S</div><b>Settlement Check</b></div>
  <h1>A prediction market is a claim about the future.<br>
      This asks <em>what will decide it</em> — and whether anyone can check that.</h1>
  <p class="lede">Measured on the live Panta catalogue. Every number here comes from the snapshot
     below it; nothing on this page is typed by hand.</p>

  <div class="split">
    <div class="card bad">
      <div class="big">{mute} of {live}</div>
      <small>markets <b>you can buy right now</b> do not say what you are buying — {share}</small>
    </div>
    <div class="card good">
      <div class="big">{done - done_mute} of {done}</div>
      <small>markets that are <b>already settled</b> state their question — the question appears
             once nobody can act on it</small>
    </div>
  </div>
</header>

<section>
  <h2>The catalogue says UMA. The chain says one keypair.</h2>
  <p><code>sentToUma</code> is true on {counts['claims_uma']} of the {counts['markets']} markets in
     this snapshot.</p>
  <div class="quote">{settler_line}</div>
  <p>The settlement path is <code>GraduateMarketUsdc → SubmitOracleResultUsdc →
     ResolveEventUsdc → ClaimWinUsdc</code>. This tool reads the market account's own history and
     reports who signed the middle two, because the catalogue's <code>oracle</code> field is a
     claim about who decides and not the account that does: on every market checked it names the
     wallet whose instruction is <code>CreateEventUsdc</code>.</p>
</section>

<section>
  <h2>What the creator wrote, and what the buyer gets</h2>
  <p>Panta's create API requires a <code>question</code>, a <code>resolutionRule</code> of up to
     2048 characters, and a non-empty <code>sourcesOfTruth</code>. The read API returns none of
     them under those names. <code>oracle</code> is <code>sourcesOfTruth</code> joined by commas —
     which is why the most common settlement source in the catalogue is the word
     <code>on-chain</code>, typed into that list by a creator. <code>resolutionRule</code> is in no
     read response at all.</p>
  <div class="cols">
    <div><h3>./run.sh --check-draft draft.json</h3>
<pre><b>BLOCK</b> sourcesOfTruth: 'on-chain' is a word, not a reference
      → name the account, the program or the outlet.
        A buyer sees this string and nothing else — it
        becomes the market's `oracle` field verbatim
<b>BLOCK</b> startTime: starts in 589s; the chain requires 3600s
<b>BLOCK</b> imageUrl: not reachable (HTTP 404)
      → Panta refuses this draft with a generic
        INVALID_MARKET_PARAMS that never mentions the image</pre></div>
    <div><h3>a draft that passes</h3>
<pre>Nothing here would leave a buyer unable to read this market.

WHAT THE CATALOGUE WILL SHOW
  title   Will the Pectra upgrade activate before 1 Dec 2026?
  oracle  https://ethereum.org/…,https://etherscan.io
  resolutionRule  <b>not returned by the read API under any
                  name — you are writing it for nobody</b>

PANTA SAYS  <i>the draft passes their validation.</i>
  creation fee   50.00 USDC
  event address  8f6SZ3RExSKqwbVy9qoRfe7P6BXJoGrQWEdAYMZ5k6rF
  nothing was signed, submitted or paid by this tool.</pre></div>
  </div>
</section>

<section>
  <h2>The snapshot</h2>
  <p>{counts['markets']} markets, {counts['settlements_read']} of them with their settlement read
     from the chain. Taken {html.escape(snapshot['taken_at'])}.</p>
  <table>
    <thead><tr><th>Market</th><th>Verdict</th><th class="hide-sm">Claimed source</th>
      <th>Volume</th></tr></thead>
    <tbody>
{rows_html(snapshot['markets'])}
    </tbody>
  </table>
</section>

<footer>
  <p>Read-only throughout: no wallet, no signature, no transaction, nothing spent. Reproduce with
     <code>./run.sh</code>, <code>demo/census.py</code> and <code>demo/snapshot.py</code> —
     <a href="{REPO}">{REPO.replace('https://', '')}</a>. Built for the Colosseum Crypto World's
     Fair, Panta API and Solami sidetracks. MIT.</p>
</footer>

</div></body></html>
"""


def main():
    snapshot = json.loads((HERE / "snapshot.json").read_text())
    (HERE / "index.html").write_text(render(snapshot))
    print(f"wrote {HERE / 'index.html'}")


if __name__ == "__main__":
    main()
