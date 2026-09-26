"""What Solana can tell us about the account that settles a market.

The endpoint is a setting, not a constant: today this runs against the public mainnet RPC, and
pointing `SOLANA_RPC` at a Solami endpoint changes the data path without changing any caller. Only
read methods are used — `getAccountInfo`, `getSignaturesForAddress`, `getTransaction`.
"""
import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.request

PUBLIC_RPC = "https://api.mainnet-beta.solana.com"
SOLAMI_KEY_FILE = pathlib.Path(os.environ.get(
    "SOLAMI_KEY_FILE", pathlib.Path.home() / ".config/solami.key"))


def _endpoint():
    """Where to read the chain. A key on disk beats the public node, and beats neither in code.

    Order: `SOLANA_RPC` if set, then a Solami key at `~/.config/solami.key`, then the public node.
    The key is read from outside the repository and never printed — `safe()` masks it for any
    message that names the endpoint.
    """
    explicit = os.environ.get("SOLANA_RPC")
    if explicit:
        return explicit
    if SOLAMI_KEY_FILE.exists():
        key = SOLAMI_KEY_FILE.read_text().strip()
        if key:
            return f"https://rpc.solami.dev/solana?api-key={key}"
    return PUBLIC_RPC


def safe(url):
    """An endpoint with its credential removed, fit to print."""
    return re.sub(r"(api[-_]?key=)[^&\s]+", r"\1<key>", url or "")


RPC = _endpoint()
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
    # Solami serves websockets from a different host and spells the parameter with an underscore:
    # rpc.solami.dev answers a subscription upgrade with 405, ws.solami.dev/ws/sol with 101.
    if SOLAMI_KEY_FILE.exists() and "solami.dev" in RPC:
        key = SOLAMI_KEY_FILE.read_text().strip()
        if key:
            return f"wss://ws.solami.dev/ws/sol?api_key={key}"
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

# The two instructions that decide a market. `SubmitOracleResult` puts the outcome on chain;
# `ResolveEvent` closes the event against it. Everything else in a market's history is trading,
# creation or claiming.
#
# They appear under two names. Markets carrying a `MigrateEventV2` in their history settle as
# `ResolveEvent` and `SubmitOracleResult`; the rest settle as `ResolveEventUsdc` and
# `SubmitOracleResultUsdc`. Matching only the suffixed pair — which this tool did — reports a
# market settled under the other names as one that nothing has settled, which is the false clean
# bill this project exists to refuse. The same keypair signs both families.
SETTLEMENT_INSTRUCTIONS = ("SubmitOracleResult", "ResolveEvent")


def base_instruction(name):
    """An instruction name with the quote-asset suffix removed, so both families compare equal."""
    return name[:-4] if name.endswith("Usdc") else name


def settlement_instructions_in(names):
    """The settlement instructions among these, under whichever name they arrived."""
    return {name for name in names if base_instruction(name) in SETTLEMENT_INSTRUCTIONS}


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


# A market's whole life on this program, when that life is short enough to see all of it.
FULL_HISTORY = 1000


def history(market_id, limit=FULL_HISTORY):
    """Every signature on a market account, and whether that is genuinely all of them.

    `getSignaturesForAddress` returns the most RECENT n, so a count that hits the limit says
    nothing about what came before it. Only a count below the limit is a complete history — and
    only then can "this market has never had an order" be said at all. Getting that wrong is easy:
    a market showing no orders in its last 25 transactions had eight in its last 40.

    Returns `(signatures, complete)`.
    """
    signatures = recent_signatures(market_id, limit)
    return signatures, len(signatures) < limit


ORDER_INSTRUCTIONS = ("PrimaryOrder", "SecondaryLimitOrder", "SecondaryMarketOrder")


def traded_on_chain(market_id, limit=FULL_HISTORY):
    """Has an order ever been placed on this market, here?

    True, False, or None when the history is too long to read in full — never a guess. A market
    whose entire history is a `MigrateEventV2` has not traded on this program, whatever volume
    the catalogue reports against it.
    """
    signatures, complete = history(market_id, limit)
    if not complete:
        return None
    for entry in signatures:
        result = transaction(entry["signature"])
        if not result:
            continue
        names, _signer = instructions_and_signer(result)
        if any(base_instruction(name) in ORDER_INSTRUCTIONS for name in names):
            return True
    return False


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
        settling = settlement_instructions_in(names)
        if settling:
            seen |= settling
            if signer:
                signers.add(signer)
    if not seen:
        return None
    return {"signers": signers, "instructions": seen, "signatures": len(signatures)}


def settlements(market_ids, limit=12, workers=1):
    """Settlement for many markets, `workers` requests in flight at once.

    Sequential reads waste an endpoint's headroom on round-trip latency: a node that will answer
    200 requests a second still only answers one every 300ms if you ask for one at a time. This
    is where a real endpoint turns into wall-clock, and why the number is a setting — the public
    node starts refusing above a couple in flight, a Solami key does not.

    Returns `{market_id: settlement-or-None}`, and a market whose lookup raised is simply absent,
    never present with a None that would read as "nobody settled it".
    """
    if workers <= 1:
        out = {}
        for market_id in market_ids:
            try:
                out[market_id] = settlement(market_id, limit)
            except ChainError:
                pass
        return out

    from concurrent.futures import ThreadPoolExecutor
    out = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(settlement, mid, limit): mid for mid in market_ids}
        for future, market_id in futures.items():
            try:
                out[market_id] = future.result()
            except ChainError:
                pass
    return out


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
