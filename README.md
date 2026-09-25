# Settlement Check

A prediction market is a claim about the future. This asks the question the market page never
answers: **what decides it, and could anyone else have checked that decision?**

```bash
./run.sh --cards 40
```

Five verdicts, printed every time:

- **unstated** — the market carries no question at all. Whatever settles it, nobody buying can
  know what they bought.
- **named nothing** — the settlement source is a word rather than a reference. No address to look
  up, no program to read, no outlet to ask.
- **one key** — the question is stated and a single wallet decides it: no program, no feed, no
  second signature.
- **editorial** — the question is stated and named newsrooms decide it. Nobody can reproduce the
  call from the chain.
- **verifiable** — settlement rests on an on-chain account holding program state, which anyone can
  read for themselves.

The command exits non-zero when it finds any of the first three.

## What the live catalogue actually shows

Every number below comes out of `demo/census.py`, so none of them is typed by hand:

```bash
.venv/bin/python demo/census.py
```

Three passes on 26 September 2026. Each pass reads the 100 markets the API will hand over, opens
each market's own card, and counts the two populations apart — because counting them together is
what hides the finding.

| Pass | On sale | of those, no question | Settled | of those, no question |
|---|---:|---:|---:|---:|
| 1 | 40 | 34 (85%) | 60 | **0 (0%)** |
| 2 | 50 | 42 (84%) | 50 | **0 (0%)** |
| 3 | 17 | 13 (76%) | 83 | **0 (0%)** |

**Every one of the 193 settled markets states its question. Between three and four out of five of
the markets still on sale state none.** The question is written down once the outcome is known —
which is to say, once nobody can act on it. That is not a listing that needs tidying up; it is the
one fact a buyer needs, withheld for exactly as long as it is worth something.

### The most common settlement source in this catalogue is the word "on-chain"

34 of 100 markets, every pass — more than any newsroom and more than any wallet. It is not an
address, not a program id and not a masthead. And it is the one claim here that can be checked on
its own terms: if a settlement really is on-chain, there is an account, and the identifier has to
carry it so a reader can open it. None of them does.

This tool used to file these as `editorial`, printing "1 newsroom feed(s): on-chain", which is too
generous by half. They now get their own verdict, and it is the largest group by volume in the
catalogue.

Where a question *is* stated and an address given, resolution rests on a wallet:
`4VGFQKGanc5oaLf51mee9m45HmiXRhKruh5mdRaMjipS`, an account owned by the System Program with no
data — a keypair, not an oracle. It signs regularly and calls the market program
`6gM5afTQBq5VZCfgpGqcsqzfWd5maLSCKWtGjbEobZMp` together with the SPL Token program, so the same key
both decides the outcome and moves the money.

The `verifiable` group is empty, and the report says so in as many words. A report that cannot say
"this one is fine" is not measuring anything.

### A number this project got wrong

An earlier draft of this file said **91 of 100 markets state no question**. That was wrong, and it
was wrong in the way this whole tool exists to catch: the measurement read one field, `description`,
because every listing row leaves `title` empty. Open the market's own card and `title` carries the
question on 52–87 of 100, depending on the slice the API returns. Anyone who clicked a single
market would have seen it.

The corrected figure is smaller and the finding is stronger. It is left in the README on purpose:
a tool that demands receipts has to show its own.

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
5. **The listing and the card disagree about the question.** For the same `marketId` the listing
   row returns `title: ""` while the card returns the full question. The listing is what a client
   renders first.
6. **Each read returns a different slice.** Three passes minutes apart returned 40, 50 and 17
   tradeable markets out of 100. This is why the volume riding on silent markets is *not* quoted
   here: it came out at $81,660 on one pass and $0 on the next two. The count split reproduces;
   that figure does not, so it stays out.

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
.venv/bin/python -m pytest tests -q      # 24 tests, no network
```

The verdicts are tested against cards written by the tests themselves, with the two on-chain
lookups injected — which is why they are parameters.

MIT licensed.
