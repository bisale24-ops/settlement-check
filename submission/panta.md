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

## What it found on the live catalogue

Every number reproduces with `demo/census.py`. Measured 26 September 2026.

**The question appears once nobody can act on it.** Three passes, every card opened:

| Pass | On sale | no question | Settled | no question |
|---|---:|---:|---:|---:|
| 1 | 40 | 34 (85%) | 60 | **0** |
| 2 | 50 | 42 (84%) | 50 | **0** |
| 3 | 17 | 13 (76%) | 83 | **0** |

193 settled markets, every one states its question. Three to four out of five still on sale
state none.

**The create API demands what the read API drops.** Creating a market requires `question`, a
`resolutionRule` of up to 2048 characters and a non-empty `sourcesOfTruth`. The read API returns
none of them under those names: `title` carries the question but only on the card, never in a
listing row; `oracle` is `sourcesOfTruth` joined by commas; `resolutionRule` appears in no read
response at all. Which is why the most common settlement source in the whole catalogue is the
literal word `on-chain` — 34 of 100 markets, more than any newsroom and more than any wallet.

**The catalogue says UMA; the chain says one keypair.** `sentToUma` is true on 85 of 100
markets. On Solana, `SubmitOracleResult` and `ResolveEvent` were signed by the same account —
`664h8sZvGwUx4hfqWYrewwvC7wenbKPTCFQTKZx5ghbR`, System-owned, no data — on every settled market
inspected, under both instruction naming families, with no UMA assertion in any of those
transactions.

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
