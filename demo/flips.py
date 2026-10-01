"""The same market card, asked for several times in a row, comes back in different shapes.

    .venv/bin/python demo/flips.py [markets] [calls]

For each market it requests GET /markets/{id}/ `calls` times and records whether the response is
the complete card (it carries `question`) or the stripped one (it does not). F = complete,
s = stripped. A market whose row mixes F and s answered identical requests differently.
"""
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
from settlementcheck import panta  # noqa: E402


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    calls = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    rows = panta.markets()[:n]
    mixed = 0
    for row in rows:
        shapes = []
        for _ in range(calls):
            shapes.append("F" if "question" in panta.market(row["marketId"]) else "s")
            time.sleep(0.15)
        mixed += len(set(shapes)) > 1
        print(f"{row['marketId']:46} {''.join(shapes)}")
    print(f"\n{mixed} of {len(rows)} markets changed shape between {calls} identical requests.")


if __name__ == "__main__":
    main()
