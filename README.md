# Settlement Check

A prediction market is a claim about the future. This asks the question the market page never
answers: **what will decide it, and could anyone else have checked that decision?**

```bash
git clone https://github.com/bisale24-ops/settlement-check && cd settlement-check
./run.sh --cards 24 --settlements 8          # the live catalogue, judged
./run.sh --check-draft fixtures/draft-like-the-catalogue.json   # a market, before it is published
./run.sh --replay <settlement-signature>     # one settlement, read from the chain
./run.sh --watch 300                         # settlements as they land
.venv/bin/python -m pytest tests -q          # 59 tests, no network
```

No dependencies. `run.sh` works from a fresh clone. Read-only throughout: this tool never quotes a
trade, never builds a transaction it signs, never broadcasts, and never spends anything.

---

## What it found

### The question appears once nobody can act on it

Three passes over the catalogue on 26 September 2026, every card opened, reproducible with
`demo/census.py`:

| Pass | On sale | of those, no question | Settled | of those, no question |
|---|---:|---:|---:|---:|
| 1 | 40 | 34 (85%) | 60 | **0 (0%)** |
| 2 | 50 | 42 (84%) | 50 | **0 (0%)** |
| 3 | 17 | 13 (76%) | 83 | **0 (0%)** |

Every one of the 193 settled markets states its question. Three to four out of five of the markets
still on sale state none. The two populations have to be counted apart, because counted together
this reads as untidy listings rather than as the one fact a buyer needs, withheld for exactly as
long as it is worth something.

### The catalogue says UMA. The chain says one keypair.

`sentToUma` is true on 85 of 100 markets, including markets still trading, and false on every
cancelled one. On chain, the settlement path is:

```
GraduateMarketUsdc → SubmitOracleResultUsdc → ResolveEventUsdc → ClaimWinUsdc
```

On all 12 settled markets inspected, `SubmitOracleResultUsdc` and `ResolveEventUsdc` were signed by
the same account — `664h8sZvGwUx4hfqWYrewwvC7wenbKPTCFQTKZx5ghbR`, owned by the System Program,
holding no data, 536 signatures since June. A person with a key, not a program. **No UMA program
appears in any of those transactions**: no assertion, no dispute window, no second signature. The
claim lives in the API and not on the chain.

### What the creator wrote, and what the buyer gets

Panta's create API **requires** a `question`, a `resolutionRule` of up to 2048 characters, and a
non-empty `sourcesOfTruth`. The read API returns none of them under those names:

| create API demands | read API returns |
|---|---|
| `question` | `title`, on the card only — every listing row leaves it empty |
| `resolutionRule` (≤ 2048 chars) | **nothing, under any name** |
| `sourcesOfTruth` (≤ 20) | `oracle`, the list joined by commas |

Which is why the most common settlement source in the whole catalogue is the word `on-chain` — 34
of 100 markets, more than any newsroom and more than any wallet. Somebody typed it into that list.
It is not an address, not a program and not a masthead, and it is the one claim here that refutes
itself: a settlement that really is on-chain has an account, and the identifier has to carry it.

Every author was made to write down what decides their market. Nobody can read a word of it.

---

## The five verdicts

- **unstated** — no question at all. Whatever settles it, nobody buying can know what they bought.
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
  resolutionRule  not returned by the read API under any name — you are writing it for nobody
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
          the catalogue says this one went to UMA
          signed   664h8sZvGwUx4hfqWYrewwvC7wenbKPTCFQTKZx5ghbR
          → a claim of UMA, settled by a signature, with no UMA assertion in the transaction
```

`--replay <signature>` runs the same code over a settlement that already happened, so it can be
shown without waiting for the next one.

**Why this wants a real endpoint, measured rather than asserted.** Reading the settlements already
in the catalogue costs one `getSignaturesForAddress` plus a `getTransaction` per signature, per
market; on the public node that fails at a couple of dozen markets with `getTransaction failed
after 3 attempts`. And the public node accepts a `logsSubscribe` with a program filter,
acknowledges it, then closes the connection. The watcher reconnects and, when it gives up, says
that is the endpoint's limit and not the venue having nothing to settle. `SOLANA_WS` and
`SOLANA_RPC` point the same code somewhere that will hold it.

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

## Two numbers this project got wrong

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

A third was caught before it shipped. When the settlement budget ran out, the report said "nothing
has settled this market on chain yet" about markets whose history it had never opened. A lookup
that did not run is now `NOT_LOOKED`, never `None`, and there is a test that fails without it.

---

## Where the data comes from

- **Panta API** — the catalogue, the card, and the create-quote validator. Read-only, plus the one
  POST that prices a draft without creating anything.
- **Solana** — who actually settled a market, and the live subscription. Endpoint is a setting.

MIT licensed. Every number on the published page comes out of `docs/snapshot.json`; every number in
this file comes out of `demo/census.py` or a command printed beside it.
