#!/usr/bin/env python3
"""G102 P0: exact, content-addressed cross-prefix KV XOR-residual reconstruction.

Model-free primitive only. Never applied to live model, heldout, or production.
A base must be immutable and separately retained. Account for its full bytes.
"""
import hashlib
import zlib

MAX_BYTES = 86114304
SCHEMA = "forge.cpu-g102.exact-xor-residual.v1"


class ReconstructionError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(base, target, *, max_bytes=MAX_BYTES):
    if not isinstance(base, bytes) or not isinstance(target, bytes):
        raise ReconstructionError("G102_BYTES_REQUIRED")
    if not base or len(base) != len(target):
        raise ReconstructionError("G102_BASE_TARGET_LENGTH")
    if type(max_bytes) is not int or max_bytes <= 0 or len(base) > max_bytes:
        raise ReconstructionError("G102_BUDGET")
    delta = bytes(x ^ y for x, y in zip(base, target))
    packed = zlib.compress(delta, level=6)
    return {"schema": SCHEMA, "base_sha256": digest(base),
            "target_sha256": digest(target), "length": len(target),
            "payload": packed}


def decode(base, packet, *, max_bytes=MAX_BYTES):
    if not isinstance(base, bytes) or not isinstance(packet, dict):
        raise ReconstructionError("G102_PACKET_TYPE")
    if (packet.get("schema") != SCHEMA or
            type(packet.get("length")) is not int or
            packet["length"] <= 0 or packet["length"] > max_bytes or
            len(base) != packet["length"]):
        raise ReconstructionError("G102_PACKET_CONTRACT")
    if digest(base) != packet.get("base_sha256"):
        raise ReconstructionError("G102_BASE_IDENTITY")
    packed = packet.get("payload")
    if not isinstance(packed, bytes) or not packed:
        raise ReconstructionError("G102_PAYLOAD")
    # Bound decompression, rather than trusting a potentially corrupt zlib stream.
    try:
        z = zlib.decompressobj()
        delta = z.decompress(packed, packet["length"] + 1)
        if (len(delta) != packet["length"] or not z.eof or
                z.unconsumed_tail or z.unused_data):
            raise ReconstructionError("G102_DELTA_LENGTH_OR_TRAILING")
    except zlib.error as exc:
        raise ReconstructionError("G102_CORRUPT_PAYLOAD") from exc
    target = bytes(x ^ y for x, y in zip(base, delta))
    if digest(target) != packet.get("target_sha256"):
        raise ReconstructionError("G102_TARGET_INTEGRITY")
    return target


def accounting(base, targets, packets):
    """Full resident-state accounting: base + encoded targets, no free base."""
    if (not isinstance(base, bytes) or not targets or
            len(targets) != len(packets)):
        raise ReconstructionError("G102_ACCOUNTING_INPUT")
    if any(not isinstance(t, bytes) or len(t) != len(base) for t in targets):
        raise ReconstructionError("G102_TARGET_LAYOUT")
    if any(p.get("base_sha256") != digest(base) for p in packets):
        raise ReconstructionError("G102_BASE_MISMATCH")
    n = len(targets)
    plain_bytes = sum(len(t) for t in targets)
    independent_zlib = sum(len(zlib.compress(t, level=6)) for t in targets)
    proposal_bytes = len(base) + sum(len(p["payload"]) for p in packets)
    return {"targets": n, "raw_bytes": plain_bytes,
            "standalone_zlib_bytes": independent_zlib,
            "residual_with_base_bytes": proposal_bytes,
            "wins_both_storage_controls": proposal_bytes <
                min(plain_bytes, independent_zlib)}
