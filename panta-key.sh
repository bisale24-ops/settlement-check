#!/usr/bin/env bash
# Registers a Panta developer account (or logs in) and mints an API key.
# Password is read hidden and never stored. The key goes straight to ~/.config/panta.key.
# Only HTTP statuses and server error codes are printed — never tokens, keys or the password.
set -uo pipefail
API=https://live-api.panta.market/api/v1
OUT="$HOME/.config/panta.key"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

say_error() {                       # $1 = file with the JSON body
  python3 - "$1" <<'PY' 2>/dev/null || head -c 300 "$1"
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    print("(unparseable response)"); raise SystemExit
print("  code:", d.get("code", "-"))
print("  message:", str(d.get("message", "-"))[:300])
PY
}

printf 'Email: '; read -r EMAIL
printf 'Password for the API account (min 8 chars, you invent it, hidden): '
stty -echo 2>/dev/null; read -r PASS; stty echo 2>/dev/null; printf '\n'

payload=$(EMAIL="$EMAIL" PASS="$PASS" python3 -c '
import json, os
print(json.dumps({"email": os.environ["EMAIL"], "password": os.environ["PASS"], "name": "KHLab"}))')

echo "1/3 register…"
code=$(curl -sS -o "$TMP/reg.json" -w '%{http_code}' -X POST "$API/auth/register/" \
       -H 'Content-Type: application/json' -d "$payload")
echo "    HTTP $code"

if [ "$code" != "200" ] && [ "$code" != "201" ]; then
  say_error "$TMP/reg.json"
  echo "2/3 trying to log in with the same details…"
  code=$(curl -sS -o "$TMP/reg.json" -w '%{http_code}' -X POST "$API/auth/token/" \
         -H 'Content-Type: application/json' -d "$payload")
  echo "    HTTP $code"
  [ "$code" = "200" ] || { say_error "$TMP/reg.json"; echo "Stopped: no token."; exit 1; }
fi

ACCESS=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("access",""))' "$TMP/reg.json")
[ -n "$ACCESS" ] || { echo "Stopped: the response carried no access token."; say_error "$TMP/reg.json"; exit 1; }

echo "3/3 minting the API key…"
code=$(curl -sS -o "$TMP/key.json" -w '%{http_code}' -X POST "$API/account/keys/" \
       -H "Authorization: Bearer $ACCESS" -H 'Content-Type: application/json' \
       -d '{"env":"live","name":"settlement-check"}')
echo "    HTTP $code"
key=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("secret",""))' "$TMP/key.json" 2>/dev/null)
[ -n "$key" ] || { say_error "$TMP/key.json"; echo "Stopped: no key issued."; exit 1; }

mkdir -p "$(dirname "$OUT")"; printf '%s' "$key" > "$OUT"; chmod 600 "$OUT"
unset PASS key payload ACCESS
echo "Done. Key saved to $OUT ($(wc -c < "$OUT" | tr -d ' ') bytes)."
