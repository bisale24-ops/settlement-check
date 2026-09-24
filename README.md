# Settlement Check

A prediction market is a claim about the future. This asks the question the market page never
answers: **what decides it, and could anyone else have checked that decision?**

```bash
./run.sh --cards 24
```

Four verdicts, printed every time:

- **unstated** — the market carries no question at all. Whatever settles it, nobody buying can
  know what they bought.
- **one key** — the question is stated and a single wallet decides it: no program, no feed, no
  second signature.
- **editorial** — the question is stated and named newsrooms decide it. Nobody can reproduce the
  call from the chain.
- **verifiable** — settlement rests on an on-chain account holding program state, which anyone can
  read for themselves.

The command exits non-zero when it finds the first two.

## What the live catalogue actually shows

Measured on 24 September 2026 across three slices of the Panta catalogue (unfiltered,
`status=primary`, `status=secondary`), 100 unique markets:

| Slice | Markets | No question stated |
|---|---:|---:|
| unfiltered | 50 | 42 (84%) |
| `status=primary` | 50 | 47 (94%) |
| `status=secondary` | 50 | 44 (88%) |
| **union, de-duplicated** | **100** | **91 (91%)** |

Every market in the catalogue leaves `title` empty; the question, when there is one, lives in
`description`. Where a question *is* stated, resolution rests on a wallet:
`4VGFQKGanc5oaLf51mee9m45HmiXRhKruh5mdRaMjipS`, an account owned by the System Program with no
data — a keypair, not an oracle. It signs regularly and calls the market program
`6gM5afTQBq5VZCfgpGqcsqzfWd5maLSCKWtGjbEobZMp` together with the SPL Token program, so the same key
both decides the outcome and moves the money.

The `verifiable` group is currently empty, and the report says so in as many words. A report that
cannot say "this one is fine" is not measuring anything.

## Defects found in the catalogue API

Reported as found, reproducible with `curl`:

1. **Cursor pagination does not advance.** Passing a page's own `nextCursor` back as `cursor`
   returns the identical rows and the identical cursor, at `limit=5` and at `limit=50`. The
   catalogue therefore cannot be walked; this tool collects phase slices and de-duplicates instead.
2. **`GET /markets/categories/` returns `MARKET_NOT_FOUND`** — the documented route is being parsed
   as a market id.
3. **`status=resolved` and `status=cancelled` return zero rows**, while unfiltered pages contain
   markets in both phases.
4. **Volume fields come and go.** `totalVolumeUsdc` is populated on one call and absent on the next
   for the same market. The tool reports "volume not reported" rather than `$0`, because printing
   a zero for an unknown is the false clean bill this project exists to refuse.

## Where the data comes from

- **Panta API** — the market catalogue, the card, the stated question and the `oracle` field.
  Read-only: this tool never quotes, builds, signs or submits a transaction, so it needs no wallet
  and spends nothing.
- **Solana RPC** — what the settlement source actually is. An account owned by the System Program
  is a person with a keypair; an account owned by a program is something a reader can inspect.
  The endpoint is a setting (`SOLANA_RPC`), so the same code runs against a public node today and
  a Solami endpoint tomorrow.

## Tests

```bash
.venv/bin/python -m pytest tests -q      # 19 tests, no network
```

The verdicts are tested against cards written by the tests themselves, with the two on-chain
lookups injected — which is why they are parameters.

MIT licensed.
