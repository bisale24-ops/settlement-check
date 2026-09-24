# Settlement Check — Crypto World's Fair sidetracks

A prediction market is a claim about the future. This asks the question the market page never
answers: **what evidence will settle it, and can anyone see that evidence?**

## Why this shape

Same spine as the three projects before it — an artifact makes a claim, the tool demands the
receipt — moved to a domain where the gap is expensive. A market resolves to YES or NO and money
changes hands; whether anyone can check that outcome is decided *after* people have bought in.

**Measured on the live catalog, 24.09.2026** (300 markets via the Panta API, 60 cards read):

- **252 of 300 markets carry no question at all** — `title` is empty on every single one and
  `description` is empty on 252. Of the 60 cards read in full, 55 state nothing; 12 of those are in
  `primary` phase, tradeable right now. **$81,131 of $91,938 total volume sits on markets whose
  question is not written down anywhere in the API.**
- Where a question *is* stated, resolution rests on a wallet: all five such markets name the same
  `oracle`, `4VGFQKGanc5oaLf51mee9m45HmiXRhKruh5mdRaMjipS`. That account is owned by the System
  Program with zero data — a plain key, not an oracle program. It signs regularly and calls one
  program, `6gM5afTQBq5VZCfgpGqcsqzfWd5maLSCKWtGjbEobZMp`.
- Where no question is stated, `oracle` is a list of newsroom identifiers instead —
  `world-politics-reuters,world-politics-ap,global-reuters,global-ap,global-bbc`.

So the original guess — that some markets settle against verifiable on-chain data — did not survive
contact with the catalog. Nothing here settles from a feed anyone can audit. That is the finding,
and it is a better one: **your bet is settled by a key, not by a fact.**

## The three verdicts

- **unstated** — the market carries no question. Whatever settles it, nobody buying can know what
  they bought. The volume riding on this is the headline number.
- **editorial** — the question is stated and resolution rests on named newsrooms. Say which ones
  must be trusted, and that no one can reproduce the call.
- **one key** — the question is stated and one wallet decides. Name the key, show how many markets
  it controls and how much volume they carry, and stream its settlements as they land.

A fourth verdict, **verifiable**, exists in the report and is currently empty. It stays in, because
a report that cannot say "this one is fine" is not measuring anything.

## How it uses each sponsor's product, honestly

- **Panta API** (`live-api.panta.market/api/v1/`): market catalog, single market with spot prices,
  trade tape, categories, wallet trades. Read-only — we never build, sign or submit a transaction,
  so no wallet and no money is involved. Auth is `X-Api-Key`; the catalog is closed without one.
- **Solami**: the live path. The resolver key signs settlements on mainnet; the tool watches it
  through Yellowstone gRPC (or Mirage over WebSocket), decodes each transaction against the market
  program, and reports the settlement the moment it lands: which market, which outcome, how much
  volume was riding on it, and whether that market ever stated a question. Blur adds the traded
  side; the Data API fills in history on start-up. This is continuous work on a stream rather than
  one token call — which is what the track asks for.

Open question to settle during the build: `hermesResponse` is `True` on 42 of the 60 cards read and
`False` on 18. If that flags a Pyth price used at resolution, price markets may have a verifiable
path after all, and the fourth verdict stops being empty. To be checked, not assumed.

## Deliverables

1. Public repo, MIT, README anyone can run: setup, env vars, how to point it at their own keys.
2. CLI that prints the three groups for the live catalog, with the evidence under each line.
3. A small live page: a market, its criterion, its verdict, and the on-chain evidence ticking.
4. Demo video 2–3 minutes against **live mainnet** (mandatory for Solami: "a submission that does
   not run live is not judged"). Synthesised narration, screen capture, no presenter.
5. Colosseum submission: description, GitHub, presentation video 2–3 min, demo video ≤3 min, GTM.

## Tracks and prizes

| Track | Pool | Places | Submissions when found |
|---|---|---|---|
| Panta API Sidetrack | 5,000 USDG | 2000 / 1000 / 1000 / 1000 | 5 |
| Solami — build on Solana data | 3,000 USDG | 1200 / 1000 / 500 / 300 | 7 |

Both require the project to be submitted to the **main Colosseum hackathon** as well; the sidetrack
submission does not replace it. Submitting to a sidetrack costs no Earn credit.

Rejected after reading the terms: **RPC Fast** (~$10.5k) pays only in subscriptions — "prizes are
not paid or transferred as cash, cryptocurrency, or other monetary funds" — and demands 2–3
promotional posts a month for two months. **CertiK** and **Adevar** pay in audit credits.

## Dates

- Colosseum hackathon: 14.09 – **12.10.2026**. Registration open, solo allowed, global.
- Sidetracks close **13.10.2026, 06:59 UTC**. Winners: Panta 28.10, Solami 28.10.
- Our build window: **28.09 – 10.10** (IBM Bob runs 25–27.09; AMD ACT III 12–18.10 and Open Agent
  15–20.10 come after, so the submission must be finished before the 12th, not on it).

## His steps (blocking, nothing starts without them)

1. Account at **colosseum.com** and registration in Crypto World's Fair.
2. Account at **panta.market** → API key (`pk_test_…` / `pk_live_…`), saved to `~/.config/panta.key`.
   Everything including the market catalog returns 401 without it.
3. Sign-up at **solami.dev** via the track's referral link (Pro free for 7 days) → key to
   `~/.config/solami.key`. Note: Pro is 7 days and the track runs 19 — start the key when the build
   is ready to run live, not before.
4. **Solana wallet connected to the Earn profile** — required for any payout, Mermail included.

## Mine

Everything else: design, code, tests, both videos, the repo, the Colosseum submission text and the
two sidetrack submissions on Earn.

## Ground rules kept

Read-only throughout: no wallet keys, no signing, no gas, no deposits, no mainnet trades. If a
track feature would require spending his money, it is out of scope rather than funded.
