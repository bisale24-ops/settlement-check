# Solami sidetrack — submission text

Judged on: Solami usage · working demo on live mainnet · build quality · usefulness · creativity.
Their rule: *a submission that does not run live is not judged.*

---

## What it is

**Settlement Check** reads a prediction market and asks what will decide it — then checks that
answer against the chain rather than against the venue's own field.

- **Repository** — https://github.com/bisale24-ops/settlement-check
- **Live report** — https://bisale24-ops.github.io/settlement-check/
- **Demo video** — https://youtu.be/1aEPWAT_960
- **Colosseum submission** — https://colosseum.com/arena/projects/settlement-check

## Why Solana is where the answer is

Panta's catalogue exposes an `oracle` field, which reads like the account that decides a market.
It is not. On every market checked, that address is the wallet whose instruction is
`CreateEventUsdc` — it creates markets; it does not resolve them.

The account that does is found by reading the market's own transaction history and looking for
the two instructions that settle it:

```
GraduateMarket → SubmitOracleResult → ResolveEvent → ClaimWin
```

On every settled market inspected, both were signed by the same keypair —
`664h8sZvGwUx4hfqWYrewwvC7wenbKPTCFQTKZx5ghbR`, owned by the System Program, holding no data,
536 signatures since June. `sentToUma` is true on 85 of 100 markets and no UMA program appears in
any of those transactions — reported as two facts side by side, because the venue's own page says
*agent resolution*, with a confidence score and a dispute window, and never mentions UMA.

Solana also answers a question the API will not: **13 of 100 catalogue markets have no account at
all**, while being served as tradeable. `getAccountInfo` returns null, and Panta's own front end
renders them as "Market not found on-chain".

Those instructions arrive under two names — markets carrying a `MigrateEventV2` settle as
`ResolveEvent` and `SubmitOracleResult`, the rest as `ResolveEventUsdc` and
`SubmitOracleResultUsdc`. Matching only one family, which this tool did at first, reports a
settled market as one nothing has settled. Both are matched now, and the same keypair signs both.

## How Solami is used, and what it measurably buys

Solami is the data path. `SOLANA_RPC` wins if set; otherwise a key at `~/.config/solami.key` is
used; otherwise the public node. The key is read from outside the repository, never committed,
and `chain.safe()` masks it anywhere the endpoint is printed — there is a test that fails if any
command prints it.

Reading who settled a market costs one `getSignaturesForAddress` plus a `getTransaction` per
signature, so a catalogue means doing it a few hundred times, and sequential reads spend the day
on round-trip latency. What matters is how many can be in flight. Fourteen settled markets,
identical code, `--workers 6`:

| endpoint | lookups in flight | read | wall clock |
|---|---:|---:|---:|
| `api.mainnet-beta.solana.com` | 6 | **0 of 14** | refused everything under concurrency |
| Solami, free tier | 6 | 14 of 14 | 101s |
| Solami, Pro | 6 | 14 of 14 | 41s |
| **Solami, Pro** | **24** | **14 of 14** | **9s** |

Same code, same fourteen markets; 206s for the same reads one at a time. `--workers` is the knob,
and the endpoint decides how far it can go.

The public node also drops a quiet subscription. With the market program filter over 70 seconds it
delivered 2 frames and closed once; through Solami, 1 frame and no close. On a busy filter it does
not drop at all — 25 seconds on SPL Token, 15,551 frames — so what breaks is an idle connection,
which is exactly what watching settlements is.

## Running live

```bash
./run.sh --replay <signature>     # one settlement that already landed, decoded
./run.sh --watch 300              # subscribe to the market program, report as they land
./run.sh --watch 300 --poll       # follow the signature list instead — works on any plan
```

Output, from a real transaction:

```
20:04:15  ResolveEventUsdc  5u15kVt2wz1cnLMU…
          market   FFFcvy12DfhFMQTPieuGFHgzdXwkk24oXTRpbpXJPF9
          claimed  4VGFQKGanc5oaLf51mee9m45HmiXRhKruh5mdRaMjipS
          the card carries sentToUma
          signed   664h8sZvGwUx4hfqWYrewwvC7wenbKPTCFQTKZx5ghbR
          → the flag is in the API; the signature is on the chain, and no UMA program is in it
```

`--poll` exists because the account this was built on sits on Free, and a WebSocket upgrade to
`wss://ws.solami.dev/ws/sol` returns *"WebSocket access requires a plan that includes WebSocket
access"*. Rather than have no live view, polling follows the market program's signature list
through RPC alone — a few seconds behind a stream, same `describe()`, same output line. With a
plan that includes WebSockets, `--watch` holds the subscription instead; nothing else changes.

## Build quality

- No runtime dependencies, including a small RFC 6455 WebSocket client written for this project,
  so `./run.sh` works from a fresh clone with nothing installed.
- 66 tests, no network, green on Python 3.9 and 3.13 in CI and in `./check.sh`.
- Read-only: it never builds, signs or sends a transaction.
- A settlement that was not looked at is `NOT_LOOKED`, never `None` — the first live run said
  "nothing has settled this market" about markets whose history it had never opened, and there is
  a test that fails without the fix.
