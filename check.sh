#!/usr/bin/env bash
# Every gate this project has, on every Python it claims to support.
# Green on one version proves nothing about the other, which is how the 3.9 break got in.
set -uo pipefail
cd "$(dirname "$0")"
fail=0
# Pass interpreters as arguments; with none, use the author's 3.9 and 3.13 venvs if they exist and
# otherwise whatever python3 is on the path — a fresh clone must never report green having run nothing.
if [ $# -gt 0 ]; then pythons="$*"
elif [ -x "$HOME/.venvs/py39/bin/python" ] || [ -x "$HOME/.venvs/py313/bin/python" ]; then
  pythons="$HOME/.venvs/py39/bin/python $HOME/.venvs/py313/bin/python"
else pythons="$(command -v python3)"; fi
ran=0
for python in "$pythons"; do
  for candidate in $python; do
    [ -x "$candidate" ] || { echo "skip: no $candidate"; continue; }
    ran=1
    echo "== $("$candidate" -V 2>&1)"
    PYTHONPATH=src "$candidate" -c "from settlementcheck import chain, classify, cli, draft, panta, report, watch, ws" \
      || { echo "   import FAILED"; fail=1; continue; }
    if "$candidate" -c "import pytest" 2>/dev/null; then
      "$candidate" -m pytest tests -q || fail=1
    else
      echo "   pytest is not installed for this interpreter — the 70 tests did not run."
      echo "   It is the only thing the checks need: $candidate -m pip install pytest"
      fail=1
    fi
    PYTHONPATH=src "$candidate" -m settlementcheck.cli --check-draft fixtures/draft-like-the-catalogue.json --offline >/dev/null
    [ $? -eq 1 ] || { echo "   the failing fixture should exit 1"; fail=1; }
  done
done
[ $ran -eq 1 ] || { echo "no interpreter ran — nothing was checked"; fail=1; }
[ $fail -eq 0 ] && echo "all green" || echo "SOMETHING FAILED"
exit $fail
