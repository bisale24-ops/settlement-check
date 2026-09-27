# Colosseum — project form text

Second version, 27 September 2026. The first carried the "three to four of five state no question"
figure and the UMA framing, both withdrawn after checking the venue's own page. Limits are the
form's: brief 500, building 1000, why now 1000, chains 500, judges 500.

## Brief description (public, 500)

If you build on a prediction market's API, you decide what your users can buy. Settlement Check asks that API two questions before you ship: does this market exist, and can anyone tell what settles it? On the live Panta catalogue, 13 of 100 markets served as tradeable have no account on Solana, and cards arrive complete or stripped with nothing saying which. Who settles a market is read from the chain, not from a field. Live on mainnet, read-only, no dependencies.

## What are you building, and who is it for? (1000)

Settlement Check reads a prediction market and answers: when this resolves, what decided it, and could anybody else have checked that decision?

Three users.

A buyer, before trading. It reads the live catalogue and sorts markets by whether you can tell what you are buying and what will settle it. Five verdicts, each naming its evidence: stripped, named nothing, one key, editorial, verifiable. A market with no account on chain is flagged before it is listed.

A creator, before publishing. --check-draft applies the same rules to a draft and refuses one a buyer could not read: no question, a source that is a word rather than a reference, times that close trading before it opens. It then asks Panta's own create-quote endpoint to validate and price it. Nothing is signed or paid.

Anyone watching, live. --watch reports each settlement as it lands: which market closed, what the catalogue claimed would decide it, and which account signed the result.

Public repo, no dependencies, read-only.

## Why did you decide to build this, and why build it now? (1000)

I shipped seven Android apps to a store, and one was rejected for a file I could not see was missing: three days to get back to a published app. So I wrote the preflight that reads a build the way the reviewer does, and the habit stuck — an artifact makes a claim, and something should ask it for the receipt.

Prediction markets are where that gap costs most, because the claim is the product, and anything built on a market's API inherits the claim without the receipt.

Why now: I measured it. On the live Panta catalogue, 13 of 100 markets served as tradeable have no account on Solana. The venue's own page says "Market not found on-chain"; the API says "primary". The card comes back complete or stripped, with nothing saying which. And the oracle field names the wallet that creates markets; on chain, one keypair signs every settlement.

The venue's product already knows all of this. Its API does not say. That is a filter and a flag away, and the same gap at every venue that follows.

## How does your product use these chains? (500)

Solana is where the answer is. The catalogue's oracle field is a claim about who decides a market, not the account that does: it names the wallet whose instruction is CreateEventUsdc. So the verdict is read from the market account's own history — who signed SubmitOracleResult and ResolveEvent, under both instruction naming families — and getAccountInfo decides whether a listed market exists at all. Live mode subscribes to the market program through Solami. Read-only: nothing is signed or sent.

## Is there anything else judges should know? (500)

Five claims this project made were wrong, and all five are in the README with their corrections; the largest was disproved by opening a market page on the venue itself. A tool that demands receipts has to show its own. Every number is reproducible: demo/census.py prints the README table and docs/snapshot.json is what the page renders. Seven API defects were reported to the Panta team directly before this submission.

## Repo context (Media and code)

The whole product is in this repository, written during the hackathon window. No runtime dependencies: ./run.sh works from a fresh clone with nothing installed, and ./check.sh runs 77 tests on Python 3.9 and 3.13 without network. demo/census.py reproduces every number in the README, including the five the project got wrong and corrected. docs/ is the published page, generated from docs/snapshot.json.
