#!/usr/bin/env bash
# Every gate this project has, on every Python it claims to support.
# Green on one version proves nothing about the other, which is how the 3.9 break got in.
set -uo pipefail
cd "$(dirname "$0")"
fail=0
for python in "${@:-$HOME/.venvs/py39/bin/python $HOME/.venvs/py313/bin/python}"; do
  for candidate in $python; do
    [ -x "$candidate" ] || { echo "skip: no $candidate"; continue; }
    echo "== $("$candidate" -V 2>&1)"
    PYTHONPATH=src "$candidate" -c "from settlementcheck import chain, classify, cli, draft, panta, report, watch, ws" \
      || { echo "   import FAILED"; fail=1; continue; }
    "$candidate" -m pytest tests -q || fail=1
    PYTHONPATH=src "$candidate" -m settlementcheck.cli --check-draft fixtures/draft-like-the-catalogue.json --offline >/dev/null
    [ $? -eq 1 ] || { echo "   the failing fixture should exit 1"; fail=1; }
  done
done
[ $fail -eq 0 ] && echo "all green" || echo "SOMETHING FAILED"
exit $fail
