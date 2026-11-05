#!/usr/bin/env python3
"""G103 P0: model-free exact adaptive block sharing for immutable KV bytes.

This is a structural-reuse hypothesis, not a novel algorithm claim.
It does NOT change live GPT2, decoding, cache policy, or heldout data.
"""
import hashlib
import zlib

MAX_BLOB = 86114304
SCHEMA = "forge.cpu-g103.immutable-block-reuse.v1"
# Fixed metadata-accounting model, not Python object-size or measured RSS.
DIGEST_BYTES, OFFSET_BYTES, LENGTH_BYTES = 32, 8, 8
REF_BYTES = DIGEST_BYTES + OFFSET_BYTES + LENGTH_BYTES
STORE_META_BYTES = DIGEST_BYTES + LENGTH_BYTES


class BlockError(ValueError):
    pass


def split_fixed(data, size=256):
    if type(size) is not int or size <= 0:
        raise BlockError("G103_FIXED_SIZE")
    return tuple(data[i:i + size] for i in range(0, len(data), size))


def split_adaptive(data, *, minimum=64, average=256, maximum=512):
    """Deterministic content-defined boundaries with bounded 64-bit rolling state."""
    if (any(type(x) is not int for x in (minimum, average, maximum))
            or minimum < 16 or average & (average - 1)
            or not minimum <= average <= maximum or maximum > 8192):
        raise BlockError("G103_CHUNK_CONFIG")
    chunks, start, state, mask = [], 0, 0, average - 1
    for i, value in enumerate(data):
        state = ((state << 1) + value + 1) & ((1 << 64) - 1)
        length = i - start + 1
        if length >= maximum or (length >= minimum and not (state & mask)):
            chunks.append(data[start:i + 1])
            start, state = i + 1, 0
    if start < len(data):
        chunks.append(data[start:])
    return tuple(chunks)


def _sha(data):
    return hashlib.sha256(data).digest()


def pack(states, *, mode="adaptive", digest_fn=_sha):
    if not isinstance(states, (tuple, list)) or len(states) < 2:
        raise BlockError("G103_STATES_REQUIRED")
    if any(not isinstance(state, bytes) or not state or len(state) > MAX_BLOB
           for state in states):
        raise BlockError("G103_INVALID_STATE")
    if mode not in ("fixed", "adaptive"):
        raise BlockError("G103_INVALID_MODE")
    if not callable(digest_fn):
        raise BlockError("G103_DIGEST")
    splitter = split_adaptive if mode == "adaptive" else split_fixed
    pool, manifests, identities = {}, [], []
    for state in states:
        manifest = []
        for block in splitter(state):
            key = digest_fn(block)
            if not isinstance(key, bytes) or len(key) != 32:
                raise BlockError("G103_INVALID_DIGEST")
            existing = pool.get(key)
            if existing is not None and existing != block:
                # A hash alone is never sufficient to assert content identity.
                raise BlockError("G103_DIGEST_COLLISION")
            if existing is None:
                pool[key] = block
            manifest.append((key, len(block)))
        manifests.append(tuple(manifest))
        identities.append(_sha(state))
    return {"schema": SCHEMA, "mode": mode, "pool": pool,
            "manifests": tuple(manifests), "state_hashes": tuple(identities)}


def unpack(bundle, index):
    if not isinstance(bundle, dict) or bundle.get("schema") != SCHEMA:
        raise BlockError("G103_BUNDLE_CONTRACT")
    manifests = bundle.get("manifests")
    if type(index) is not int or not isinstance(manifests, tuple) or not 0 <= index < len(manifests):
        raise BlockError("G103_INDEX")
    chunks = []
    for key, length in manifests[index]:
        data = bundle["pool"].get(key)
        if data is None or len(data) != length or _sha(data) != key:
            raise BlockError("G103_POOL_IDENTITY")
        chunks.append(data)
    state = b"".join(chunks)
    if len(state) > MAX_BLOB or _sha(state) != bundle["state_hashes"][index]:
        raise BlockError("G103_RECONSTRUCTION_IDENTITY")
    return state


def costs(bundle, originals):
    if not isinstance(originals, (tuple, list)) or len(originals) != len(bundle["manifests"]):
        raise BlockError("G103_ACCOUNTING_STATE_COUNT")
    if any(unpack(bundle, i) != original for i, original in enumerate(originals)):
        raise BlockError("G103_ACCOUNTING_INTEGRITY")
    payload = sum(len(blob) for blob in bundle["pool"].values())
    refs = sum(len(m) for m in bundle["manifests"])
    # Charge physical pool, its identity/length metadata, all block references,
    # and complete per-state hashes; deliberately exclude only runtime allocator
    # overhead, which must be measured in subsequent original-model diagnostics.
    total = (payload + len(bundle["pool"]) * STORE_META_BYTES
             + refs * REF_BYTES + len(originals) * DIGEST_BYTES)
    raw = sum(len(s) for s in originals)
    independent = sum(len(zlib.compress(s, 6)) for s in originals)
    return {"raw_bytes": raw, "independent_zlib_bytes": independent,
            "shared_total_modeled_bytes": total, "physical_payload_bytes": payload,
            "unique_blocks": len(bundle["pool"]), "references": refs,
            "metadata_modeled_bytes": total - payload,
            "beats_both_controls": total < min(raw, independent)}
