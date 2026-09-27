"""Read Yellowstone `SubscribeUpdate` frames from a Solami Mirage stream, with no protobuf library.

Mirage is the geyser firehose over a plain WebSocket: the server holds the filter (a saved
subscription naming the accounts to watch), and every frame is the same `SubscribeUpdate`
protobuf gRPC clients get. The usual way to read it is `yellowstone-grpc-proto`, which drags in
grpcio and a generated module. This project has no dependencies, and it needs three fields out
of the whole message — the signature, the log lines and whether the transaction failed — so it
walks the protobuf wire format by hand and stops at those.

The field numbers come from yellowstone-grpc `geyser.proto` and `solana-storage.proto`:

    SubscribeUpdate            .transaction        = 4   (message)
    SubscribeUpdateTransaction .transaction        = 1   (SubscribeUpdateTransactionInfo)
    SubscribeUpdateTransactionInfo .signature      = 1   (bytes, 64)
                                   .is_vote        = 2   (bool)
                                   .meta           = 4   (TransactionStatusMeta)
    TransactionStatusMeta      .err                = 1   (message; present only on failure)
                               .log_messages       = 6   (repeated string)

Anything else in the frame — the account keys, the instructions, balances — is skipped by its
length, which is what makes this decoder safe against fields it has never heard of.
"""
import struct

ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


class MirageError(ValueError):
    pass


def fields(buffer):
    """Yield `(field_number, wire_type, value)` for one protobuf message.

    Wire types: 0 varint (int), 1 fixed64 (bytes), 2 length-delimited (bytes), 5 fixed32 (bytes).
    Groups (3, 4) have been deprecated for twenty years and Yellowstone does not use them.
    """
    view = memoryview(buffer)
    pos, end = 0, len(view)
    while pos < end:
        tag, pos = _varint(view, pos)
        number, wire = tag >> 3, tag & 0x7
        if wire == 0:
            value, pos = _varint(view, pos)
        elif wire == 1:
            value, pos = bytes(view[pos:pos + 8]), pos + 8
        elif wire == 2:
            length, pos = _varint(view, pos)
            if pos + length > end:
                raise MirageError("length-delimited field runs past the end of the message")
            value, pos = bytes(view[pos:pos + length]), pos + length
        elif wire == 5:
            value, pos = bytes(view[pos:pos + 4]), pos + 4
        else:
            raise MirageError(f"unsupported wire type {wire} for field {number}")
        yield number, wire, value


def _varint(view, pos):
    result, shift = 0, 0
    while True:
        if pos >= len(view):
            raise MirageError("varint runs past the end of the message")
        byte = view[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7
        if shift > 70:
            raise MirageError("varint longer than ten bytes")


def field(buffer, number, wire=2):
    """The first occurrence of one field, or None."""
    for found, kind, value in fields(buffer):
        if found == number and kind == wire:
            return value
    return None


def base58(raw):
    """Encode bytes the way Solana prints signatures and addresses."""
    count = 0
    for byte in raw:
        if byte:
            break
        count += 1
    number = int.from_bytes(raw, "big")
    out = bytearray()
    while number:
        number, rem = divmod(number, 58)
        out.append(ALPHABET[rem])
    out.extend(ALPHABET[:1] * count)
    return bytes(reversed(out)).decode()


def read_update(frame):
    """Turn one Mirage frame into `(signature, log_lines, failed)`, or None for anything else.

    None covers pings, slot updates, account updates and votes — every frame that is not a
    non-vote transaction. The same shape `watch.read_notification` returns for a JSON-RPC
    `logsNotification`, so the watcher does not care which wire it is reading.
    """
    try:
        transaction = field(frame, 4)
        if transaction is None:
            return None
        info = field(transaction, 1)
        if info is None:
            return None
        signature = None
        is_vote = False
        meta = None
        for number, wire, value in fields(info):
            if number == 1 and wire == 2:
                signature = value
            elif number == 2 and wire == 0:
                is_vote = bool(value)
            elif number == 4 and wire == 2:
                meta = value
        if not signature or is_vote:
            return None
        logs, failed = [], False
        if meta is not None:
            for number, wire, value in fields(meta):
                if number == 1 and wire == 2:
                    failed = True
                elif number == 6 and wire == 2:
                    logs.append(bytes(value).decode("utf-8", "replace"))
        return base58(signature), logs, failed
    except MirageError:
        return None


def stream_url(subscription_id, key):
    return f"wss://ws.solami.dev/mirage/stream/{subscription_id}?api_key={key}"


# -- encoding, for tests and for building frames by hand ---------------------------------------

def encode_varint(value):
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def encode_field(number, value):
    """One field: ints become varints, bytes/str become length-delimited."""
    if isinstance(value, bool):
        value = int(value)
    if isinstance(value, int):
        return encode_varint((number << 3) | 0) + encode_varint(value)
    if isinstance(value, str):
        value = value.encode()
    return encode_varint((number << 3) | 2) + encode_varint(len(value)) + value


def encode_fixed64(number, value):
    return encode_varint((number << 3) | 1) + struct.pack("<Q", value)
