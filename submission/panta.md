# Panta API Sidetrack — submission text

Judged on: Panta API integration · technical execution · product and UX · originality ·
impact potential · traction. Submitted on Superteam Earn, and separately to the Colosseum
hackathon, which the sidetrack requires.

---

## What it is

**Settlement Check** asks the one question a prediction market never answers on its own page:
when this resolves, what decided it, and could anybody else have checked that decision?

- **Repository** — https://github.com/bisale24-ops/settlement-check
- **Live report** — https://bisale24-ops.github.io/settlement-check/
- **Demo video** — https://youtu.be/1aEPWAT_960
- **Colosseum submission** — https://colosseum.com/arena/projects/settlement-check

No dependencies; `./run.sh` works from a fresh clone. 66 tests on Python 3.9 and 3.13, no
network. Read-only throughout: it never builds, signs or sends a transaction.

## How the Panta API is used

Four endpoints, each doing work the product could not do without it.

| Endpoint | What it is for here |
|---|---|
| `GET /markets/` | the catalogue, collected across phase slices and de-duplicated |
| `GET /markets/{id}/` | the card: the question, the claimed oracle, phase, prices, `sentToUma` |
| `POST /markets/create/quote/` | **validates and prices a draft market before it exists** |
| `GET /markets/{id}/trades/` | the tape, when checking what a market's own account shows |

The create-quote call is the part worth pausing on. `--check-draft` runs the same rules that
judge a live market against one that has not been published yet, then hands the draft to Panta's
own validator and reports the real creation fee. It stops at the first step of your own model —
quote, build, **the creator's wallet signs**, broadcast, register — so nothing is signed,
submitted or paid.

## What it found, and what it withdrew

Measured 26 September 2026 over the hundred markets the API will hand over, and **checked against
panta.market itself**. Every number reproduces with `demo/census.py`.

### The catalogue offers markets that do not exist

**13 of 100** are served by `GET /markets/` as `primary` or `secondary` — tradeable — and have no
account on Solana at all. `getAccountInfo` on the market id returns null. Your own front end
renders exactly these as **"Market not found on-chain."**

So the product already knows. A developer reading the public API does not, and will list markets
their users cannot trade. The fix is a filter, or exposing the `onChain` flag the complete cards
already carry.

Check one: `EWiohz3LKFPmtWKF33K1wDj1xQUUP3Q3xfkj5Tsq9LTd`.

### The card comes back in two shapes, and nothing says which

A complete card carries `question`, `resolutionRule`, `sources`, `totalTrades`, `totalVolume`,
`isResolved`, `oracleResultSubmitted` and `onChain`. A stripped card carries none of them — the
fields are absent, not empty.

| card | markets |
|---|---:|
| complete, account exists | 82 |
| stripped, account exists | 5 |
| stripped, **no account** | 13 |

A client that reads `question` cannot tell a market with no question from a market whose card was
stripped. They look identical.

### What settles a market, read from the chain

`oracle` reads like the account that decides a market. It is not: on every market checked it names
the wallet whose instruction is `CreateEventUsdc`. The account that resolves is found in the
market's own history — `SubmitOracleResult` and `ResolveEvent` — and on every settled market
inspected both were signed by the same keypair,
`664h8sZvGwUx4hfqWYrewwvC7wenbKPTCFQTKZx5ghbR`, under both instruction naming families.

### What this submission withdrew before sending

An earlier draft of this work claimed that the resolution rule reaches nobody, that most markets
on sale state no question, and that the catalogue tells buyers UMA settles them. Opening a market
page disproved all three: the question, the RESOLUTION CRITERIA, the sources, an agent result with
a confidence score, a written rationale and a dispute window are all displayed. The claims are
gone, and the README lists them with their corrections.

What survived is the part that matters to an API sidetrack: the gap is between your API and your
own product, and it is a gap a developer falls into.

## Seven API defects, reported to the team before this submission

Sent directly rather than published: cursor pagination that does not advance;
`GET /markets/categories/` returning `MARKET_NOT_FOUND`; `status=resolved` and `status=cancelled`
returning zero rows; volume fields that come and go between calls; listing and card disagreeing
about the question; each read returning a different slice; and `POST /markets/create/quote/`
refusing valid drafts intermittently with `INVALID_MARKET_PARAMS` and no `fields`, where the
documented code is `DUPLICATE_MARKET` — 19 of 20 identical quotes for an accepted draft, and 3
of 10 fresh ones.

## What it does not claim

The `verifiable` verdict — settlement resting on an account anyone can read — is **empty**, and
the report says so in as many words. A report that cannot say "this one is fine" is not measuring
anything.

Two numbers this project got wrong are still in the README with their corrections. An earlier
draft said 91 of 100 markets state no question; that was measured on one field when the card
carries it in another. And the `one key` verdict was first read from the `oracle` field, which
names the account that creates markets rather than the one that resolves them. A tool that
demands receipts has to show its own.

## Traction

None. This was built during the hackathon and has no users. The repository, the page and the
measurements are public and reproducible, which is the only claim I will make for it.
