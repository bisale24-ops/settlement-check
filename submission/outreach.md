# Outreach — posted by hand from the founder's own accounts

## Discord, Panta HQ → #market-discussion

Ran a census of the public API catalogue this week and one number is worth checking against your
own feed: 13 of 100 markets served as tradeable by `GET /markets/` have no account on Solana at
all — `getAccountInfo` returns null, and panta.market itself renders them as "Market not found
on-chain". Take `EWiohz3LKFPmtWKF33K1wDj1xQUUP3Q3xfkj5Tsq9LTd` from the catalogue and compare.

The tool that found it is open source and read-only (no wallet, no signing):
https://github.com/bisale24-ops/settlement-check — the report is at
https://bisale24-ops.github.io/settlement-check/ and there is a clean catalogue in
`docs/catalogue.json` with those markets filtered out, if anyone is building a client.

Five of my own earlier claims turned out wrong when I opened your market page; they are listed
in the README with the corrections. Happy to hear where the remaining numbers are off too.

## To the Panta team — a correction to the earlier report

Subject: Correction to my API findings — three claims withdrawn

Hi,

A follow-up to the API notes I sent earlier. After checking them against panta.market itself,
three of my claims do not hold and I am withdrawing them:

1. "Most markets on sale state no question." Measured on the wrong field. The card carries
   `question` and `resolutionRule` outright, and your market page shows both, with the criteria
   and sources.
2. "The resolution rule reaches nobody." It does — it is on the page.
3. "The catalogue promises UMA settlement." `sentToUma` is a flag in the API; the page says agent
   resolution, with a confidence score, a rationale and a dispute window. I no longer draw any
   conclusion from that flag.

What stands, and what I would still ask you to look at:

- 13 of 100 catalogue markets are served as `primary`/`secondary` and have no account on Solana;
  your front end already renders them as "Market not found on-chain". Exposing the `onChain` flag
  in the listing, or filtering there, would keep clients from listing them.
- The card comes back in two shapes — complete, or stripped of `question`, `resolutionRule`,
  `sources`, `totalTrades` — with nothing in the response saying which.
- The seven defects from the earlier note (cursor pagination, `/markets/categories/`, the status
  filters, the create-quote error codes) are unchanged.

Everything reproduces from https://github.com/bisale24-ops/settlement-check, and the corrections
are in its README under "Five things this project got wrong".

Aleksandr Khrukalo
