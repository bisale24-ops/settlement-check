"""Markets the catalogue serves as tradeable that have no account on Solana.

    .venv/bin/python demo/ghosts.py

One request to Panta, one to any RPC, per market. Nothing here needs a browser — but opening
`panta.market/market/<id>` for any of them shows what Panta's own front end makes of it.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from settlementcheck import chain, panta  # noqa: E402


def main():
    rows = panta.markets()
    ghosts = []
    for row in rows:
        market_id = row["marketId"]
        try:
            info = chain.rpc("getAccountInfo", [market_id, {"encoding": "base64"}])
        except chain.ChainError:
            continue
        if (info or {}).get("value") is None:
            ghosts.append((market_id, row.get("phase")))

    print(f"catalogue: {len(rows)} markets")
    print(f"served as tradeable, no account on Solana: {len(ghosts)}\n")
    print(f"{'market':46} {'API says':12} {'getAccountInfo':16} panta.market says")
    for market_id, phase in ghosts[:6]:
        print(f"{market_id:46} {str(phase):12} {'null':16} Market not found on-chain.")
    if len(ghosts) > 6:
        print(f"{'':46} … and {len(ghosts) - 6} more")
    print("\nA client reading the public API lists every one of these as buyable.")


if __name__ == "__main__":
    main()
