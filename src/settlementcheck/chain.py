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


def websocket_endpoint():
    """Where to watch from. A Solami endpoint is a value here, not a code change.

    `SOLANA_WS` wins; otherwise the http endpoint is turned into its websocket twin, which is the
    convention every Solana provider follows.
    """
    explicit = os.environ.get("SOLANA_WS")
    if explicit:
        return explicit
    return RPC.replace("https://", "wss://", 1).replace("http://", "ws://", 1)


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


# The market program every Panta market is an account of. Its instruction names are readable in
# the transaction logs, which is what lets this tool answer "who settled it" without an IDL.
MARKET_PROGRAM = "6gM5afTQBq5VZCfgpGqcsqzfWd5maLSCKWtGjbEobZMp"

# The two instructions that decide a market. `SubmitOracleResultUsdc` puts the outcome on chain;
# `ResolveEventUsdc` closes the event against it. Everything else in a market's history is trading,
# creation or claiming.
SETTLEMENT_INSTRUCTIONS = ("SubmitOracleResultUsdc", "ResolveEventUsdc")


def transaction(signature):
    return rpc("getTransaction", [signature, {"encoding": "jsonParsed",
                                              "maxSupportedTransactionVersion": 0}])


def instructions_and_signer(result):
    """Instruction names from the logs, and the fee payer that signed them."""
    logs = (result.get("meta") or {}).get("logMessages") or []
    names = {line.split("Instruction: ", 1)[1].strip() for line in logs if "Instruction: " in line}
    keys = result["transaction"]["message"].get("accountKeys", [])
    signer = next((k["pubkey"] for k in keys if isinstance(k, dict) and k.get("signer")), None)
    return names, signer


def settlement(market_id, limit=12):
    """Who actually settled this market, read from the market account's own history.

    This is the whole correction at the centre of this tool. The catalogue's `oracle` field is a
    claim about who decides; it is not the account that does. On every market checked, the address
    in `oracle` turned out to be the wallet whose instruction is `CreateEventUsdc` — it creates
    markets, it does not resolve them. The account that resolves is found here, by reading the
    market's own transactions and looking for the two settlement instructions.

    Returns `{"signers": {...}, "instructions": {...}, "signatures": n}`, or None when the market
    has no settlement on chain yet. Raises ChainError upward if the endpoint will not answer — a
    lookup that failed must never be reported as a market that nobody settled.
    """
    signatures = recent_signatures(market_id, limit)
    signers, seen = set(), set()
    for entry in signatures:
        result = transaction(entry["signature"])
        if not result:
            continue
        names, signer = instructions_and_signer(result)
        settling = names.intersection(SETTLEMENT_INSTRUCTIONS)
        if settling:
            seen |= settling
            if signer:
                signers.add(signer)
    if not seen:
        return None
    return {"signers": signers, "instructions": seen, "signatures": len(signatures)}


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
