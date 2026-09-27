#!/usr/bin/env bash
# Runs from a fresh clone: the project's own .venv if one exists, otherwise whatever python3 is on
# the path. There is nothing to install either way — the package has no runtime dependencies.
set -euo pipefail
cd "$(dirname "$0")"
if [ -n "${PYTHON:-}" ]; then python="$PYTHON"
elif [ -x .venv/bin/python ]; then python=.venv/bin/python
else python=python3; fi
PYTHONPATH=src "$python" -m settlementcheck.cli "$@"
