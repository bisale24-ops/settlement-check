# Settlement Check

A prediction market is a claim about the future. This asks the question the market page never
answers: **what will decide it, and could anyone else have checked that decision?**

```bash
git clone https://github.com/bisale24-ops/settlement-check && cd settlement-check
./run.sh --cards 24 --settlements 8          # the live catalogue, judged
./run.sh --check-draft fixtures/draft-like-the-catalogue.json   # a market, before it is published
./run.sh --replay <settlement-signature>     # one settlement, read from the chain
./run.sh --watch 300                         # settlements as they land
./check.sh                                    # 59 tests on Python 3.9 and 3.13, no network
```

No dependencies. `run.sh` works from a fresh clone. Read-only throughout: this tool never quotes a
trade, never builds a transaction it signs, never broadcasts, and never spends anything.

---

## What it found

Measured 26 September 2026 over the hundred markets the API will hand over. Every number
reproduces with `demo/census.py`.

### The catalogue offers markets that do not exist

**13 of 100** markets are served by `GET /markets/` as `primary` or `secondary` — tradeable — and
have **no account on Solana at all**. `getAccountInfo` on the market id returns null. Panta's own
front end renders exactly these as:

> **Market not found on-chain.**

So the venue already knows. Anyone building on the public API does not, and will list markets
their users cannot trade. The fix is a filter, or the `onChain` flag the complete cards already
carry.

Check one yourself: take `EWiohz3LKFPmtWKF33K1wDj1xQUUP3Q3xfkj5Tsq9LTd` from the catalogue, ask
any RPC for its account, then open `panta.market/market/<id>` and compare.

### The card comes back in two different shapes

A complete card carries `question`, `resolutionRule`, `sources`, `totalTrades`, `totalVolume`,
`isResolved`, `oracleResultSubmitted` and `onChain`. A stripped card carries none of them — not
an empty string, the field is simply absent.

| card | markets |
|---|---:|
| complete | 83 |
| stripped, account exists | 4 |
| stripped, **no account** | 13 |

The catalogue hands back a different slice on every read, so these move by a few between passes —
the published snapshot in `docs/snapshot.json` is the one the page renders, and the count of
markets with no account has been 13 on every pass so far.

Nothing in the response says which shape you are holding. A client that reads `question` gets a
question for most markets and silence for the rest, with no way to tell a market with no question
from a market whose card was stripped. Both look identical.

### What settles a market, read from the chain rather than from a field

The `oracle` field reads like the account that decides a market. It is not: on every market
checked it names the wallet whose instruction is `CreateEventUsdc`, which creates markets and
does not resolve them.

The account that does is found in the market's own history:

```
GraduateMarket → SubmitOracleResult → ResolveEvent → ClaimWin
```

On every settled market inspected, both settlement instructions were signed by the same account —
`664h8sZvGwUx4hfqWYrewwvC7wenbKPTCFQTKZx5ghbR`, owned by the System Program, holding no data, 536
signatures since June — under **both** instruction naming families. Markets carrying a
`MigrateEventV2` settle as `ResolveEvent` and `SubmitOracleResult`; the rest add a `Usdc` suffix.
Matching one family and not the other, which this tool did at first, reports a settled market as
one that nothing has settled.

What this is not: the venue does not tell users an external oracle decides their market. Its page
says *agent resolution*, shows the result with a confidence score and a written rationale, and
names a dispute window. The finding is narrower than it first looked, and it is about what a
developer can verify: the settlement is one signature, and the API's `oracle` field points
somewhere else.

## The five verdicts

- **stripped** — the card carries no question and no resolution rule. A client reading the
  API cannot show one, and the response does not say why.
- **named nothing** — the settlement source is a word rather than a reference. Nothing to open.
- **one key** — read from the market's own history: one keypair signed the result and the
  resolution.
- **editorial** — named newsrooms decide it; nobody can reproduce the call from the chain.
- **verifiable** — settlement rests on an account holding program state, which anyone can read.

`verifiable` is empty, and the report says so in as many words. A report that cannot say "this one
is fine" is not measuring anything.

The command exits non-zero on the first three.

---

## Before you publish: `--check-draft`

The same rules, applied to a market that does not exist yet, so the 50 USDC creation fee buys
something a buyer can read.

```
6 thing(s) would leave a buyer unable to read this market
  BLOCK sourcesOfTruth: 'on-chain' is a word, not a reference
        → name the account, the program or the outlet. A buyer sees this string and
          nothing else — it becomes the market's `oracle` field verbatim
  BLOCK startTime: starts in 589s; the chain requires 3600s

WHAT THE CATALOGUE WILL SHOW
  title   …
  oracle  on-chain
  resolutionRule  returned on a complete card — but 31 of 100 cards come back stripped of it,
                  with no field saying which shape you are holding
```

It ends by asking Panta's own `POST /markets/create/quote/` to validate and price the draft. That
call reserves a create session and returns the fee from on-chain config; **nothing is signed,
submitted or paid.** Panta's model is quote → build → *the creator's wallet signs* → broadcast →
register, and this tool stops at the first step.

---

## Live: `--watch`

Subscribes to the market program and reports each settlement the moment it lands — which market,
what was claimed, who signed:

```
20:04:15  ResolveEventUsdc  5u15kVt2wz1cnLMU…
          market   FFFcvy12DfhFMQTPieuGFHgzdXwkk24oXTRpbpXJPF9
          claimed  4VGFQKGanc5oaLf51mee9m45HmiXRhKruh5mdRaMjipS
          signed   664h8sZvGwUx4hfqWYrewwvC7wenbKPTCFQTKZx5ghbR
          the card carries sentToUma; no UMA program appears in that transaction
```

`--replay <signature>` runs the same code over a settlement that already happened, so it can be
shown without waiting for the next one.

### Why this wants a real endpoint, measured rather than asserted

Reading who settled a market costs one `getSignaturesForAddress` plus a `getTransaction` per
signature. Doing it for a catalogue means doing it a few hundred times, and sequential reads spend
their whole day on round-trip latency — so the number that matters is how many can be in flight at
once. Fourteen settled markets, same code, `--workers 6`:

| endpoint | lookups in flight | read | wall clock |
|---|---:|---:|---:|
| `api.mainnet-beta.solana.com` | 6 | **0 of 14** | refused everything under concurrency |
| Solami, free tier | 6 | 14 of 14 | 101s |
| Solami, Pro | 6 | 14 of 14 | 41s |
| **Solami, Pro** | **24** | **14 of 14** | **9s** |

Same code, same fourteen markets; 206s for the same reads one at a time. `--workers` is the knob,
and the endpoint decides how far it can go.

The public node also drops a **quiet** subscription. Measured with the market program filter over
70 seconds: `api.mainnet-beta.solana.com` delivered 2 frames and closed the connection once;
Solami delivered 1 and closed none. On a busy filter the public node does not drop at all — 25
seconds on the SPL Token program gave 15,551 frames with no break — so what fails is an idle
connection, which is exactly what watching settlements is. The watcher reconnects either way and,
when it gives up, says that is the endpoint's limit and not the venue having nothing to settle.

The endpoint is a setting either way. `SOLANA_RPC` wins if set; otherwise a key at
`~/.config/solami.key` is used; otherwise the public node. The key is read from outside the
repository, never committed and never printed — anything that names the endpoint runs it through
`chain.safe()` first.

---

## Defects found, reproducible with `curl`

1. **Cursor pagination does not advance.** A page's own `nextCursor` returns the identical rows and
   the identical cursor, at `limit=5` and `limit=50`. The catalogue cannot be walked; this tool
   collects phase slices and de-duplicates.
2. **`GET /markets/categories/` returns `MARKET_NOT_FOUND`** — the documented route is parsed as a
   market id.
3. **`status=resolved` and `status=cancelled` return zero rows**, while unfiltered pages contain
   markets in both phases.
4. **Volume fields come and go** for the same market between calls. The tool reports "volume not
   reported" rather than `$0`.
5. **The listing and the card disagree about the question.** Same `marketId`, `title: ""` from the
   listing and the full question from the card. The listing is what a client renders first.
6. **Each read returns a different slice** — three passes minutes apart returned 40, 50 and 17
   tradeable markets out of 100.
7. **`POST /markets/create/quote/` refuses valid drafts intermittently, with the wrong code and no
   fields.** 19 of 20 identical quotes for an accepted draft came back `INVALID_MARKET_PARAMS` with
   `"unexpected create quote failure — check server logs"`; a repeat quote for the same wallet and
   question failed 4 times out of 4, where the documented code is `DUPLICATE_MARKET`; and 3 of 10
   fresh, distinct drafts failed the same way. The documented contract is `code` **plus `fields`**.
   A caller cannot tell "you already quoted this" from "your parameters are wrong", and the message
   points at logs they cannot read.

---

## Four things this project got wrong

Left in on purpose. A tool that demands receipts has to show its own.

**91%.** An earlier README said 91 of 100 markets state no question. That was measured on
`description` alone, because every listing row leaves `title` empty — and the market's own card
carries the question in `title` on 52 to 87 of 100. Anyone who clicked a single market would have
seen it. The corrected figure is smaller and the finding is stronger.

**The wrong wallet.** The verdict "one key decides this market" was read from the catalogue's
`oracle` field. That field names the account whose instruction is `CreateEventUsdc` — it creates
markets, it does not resolve them. The verdict now comes from the market account's own history, so
it names the account that actually signed. Both mistakes were the same mistake: believing a field
instead of reading what happened.

**The wrong field, and then the wrong conclusion.** The question was read from `title` and
`description`, which produced "three to four of five markets on sale state no question". A
complete card carries `question` outright, and Panta's own page shows both the question and the
resolution criteria to buyers. What is true is narrower and is above: 31 of 100 cards come back
stripped, and nothing says which shape you are holding.

**An overclaim about UMA.** `sentToUma` is a field in the API. The venue's page never mentions
UMA — it says agent resolution, with a confidence score, a rationale and a dispute window. The
report now puts the flag and the signature side by side and concludes nothing beyond them.

A fifth was caught before it shipped. When the settlement budget ran out, the report said "nothing
has settled this market on chain yet" about markets whose history it had never opened. A lookup
that did not run is now `NOT_LOOKED`, never `None`, and there is a test that fails without it.

---

## Where the data comes from

- **Panta API** — the catalogue, the card, and the create-quote validator. Read-only, plus the one
  POST that prices a draft without creating anything.
- **Solana** — who actually settled a market, and the live subscription. Endpoint is a setting.

MIT licensed. Every number on the published page comes out of `docs/snapshot.json`; every number in
this file comes out of `demo/census.py` or a command printed beside it.
