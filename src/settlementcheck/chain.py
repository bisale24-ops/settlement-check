"""What Solana can tell us about the account that settles a market.

The endpoint is a setting, not a constant: today this runs against the public mainnet RPC, and
pointing `SOLANA_RPC` at a Solami endpoint changes the data path without changing any caller. Only
read methods are used — `getAccountInfo`, `getSignaturesForAddress`, `getTransaction`.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

RPC = os.environ.get("SOLANA_RPC", "https://api.mainnet-beta.solana.com")
SYSTEM_PROGRAM = "11111111111111111111111111111111"
BASE58 = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


class ChainError(RuntimeError):
    pass


def looks_like_address(value):
    """A pubkey is 32–44 base58 characters. A newsroom identifier is not."""
    return bool(BASE58.match((value or "").strip()))


def rpc(method, params, timeout=30, retries=3):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    request = urllib.request.Request(RPC, data=body, headers={
        "Content-Type": "application/json", "User-Agent": "settlement-check/0.1"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.load(response)
            if "error" in payload:
                raise ChainError(f"{method}: {payload['error'].get('message')}")
            return payload.get("result")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt + 1 < retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise ChainError(f"{method} failed after {retries} attempts") from None
    raise ChainError(method)


def account_owner(address):
    """The program that owns an account, or None when the account does not exist.

    This is the question that separates a real oracle from a person: an account owned by the
    System Program holds no program state — it is a keypair somebody controls.
    """
    value = rpc("getAccountInfo", [address, {"encoding": "base64"}]).get("value")
    if value is None:
        return None
    return value.get("owner")


def is_plain_wallet(address):
    return account_owner(address) == SYSTEM_PROGRAM


def recent_signatures(address, limit=25):
    return rpc("getSignaturesForAddress", [address, {"limit": limit}]) or []


def programs_touched(signature):
    """Which programs a transaction called — how we learn what the settler actually invokes."""
    result = rpc("getTransaction", [signature, {"encoding": "jsonParsed",
                                                "maxSupportedTransactionVersion": 0}])
    if not result:
        return set()
    found = set()
    message = result["transaction"]["message"]
    for instruction in message.get("instructions", []):
        program = instruction.get("programId") or instruction.get("program")
        if program:
            found.add(program)
    for inner in (result.get("meta", {}) or {}).get("innerInstructions", []) or []:
        for instruction in inner.get("instructions", []):
            program = instruction.get("programId") or instruction.get("program")
            if program:
                found.add(program)
    return found
