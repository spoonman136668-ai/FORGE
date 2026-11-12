"""Bounded, READ-ONLY reconstruction of an already stored FORGE original.
The trust pin MUST originate from an independent authenticated source;
a D1 row, its seal and its own keys cannot create their own trust anchor.
This module creates no tables, changes no rows and launches no experiments.
"""
from dataclasses import dataclass
import hashlib
import hmac
import re

MAX_ORIGINAL_BYTES = 4 * 1024 * 1024
MAX_CHUNKS = 64
MAX_CHUNK_BYTES = 65536

class UnqualifiedArchive(ValueError):
    pass

@dataclass(frozen=True)
class IndependentPin:
    lane: str
    experiment: str
    repository: str
    run_id: int
    artifact_id: int
    source_sha: str
    frozen_manifest_sha256: str
    archive_sha256: str

@dataclass(frozen=True)
class ByteIntegrityReview:
    lane: str
    archive_sha256: str
    original_length: int
    chunk_count: int
    chunk_digests_verified: bool
    assembled_original_digest_verified: bool
    independent_source_custody_verified: bool = False
    first_use_reconciled: bool = False
    scientific_accepted: bool = False
    dispatch_authorized: bool = False

def _sha(data):
    return hashlib.sha256(data).hexdigest()

def _hex(value, size):
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{%d}" % size, value))

def verify_original(db, pin: IndependentPin) -> ByteIntegrityReview:
    # A supplied pin's actual independent origin is outside this verifier.
    # Do not use a pin materialized from the same D1 database.
    if not isinstance(pin, IndependentPin) or pin.lane not in ("Wingless", "Yggdrasil"):
        raise UnqualifiedArchive("INVALID_PIN")
    if pin.repository != "spoonman136668-ai/" + pin.lane or not (
        _hex(pin.source_sha, 40) and _hex(pin.frozen_manifest_sha256, 64)
        and _hex(pin.archive_sha256, 64)
    ) or not pin.experiment or len(pin.experiment) > 128 or (
        isinstance(pin.run_id, bool) or not isinstance(pin.run_id, int) or pin.run_id <= 0
    ) or (
        isinstance(pin.artifact_id, bool) or not isinstance(pin.artifact_id, int)
        or pin.artifact_id <= 0
    ):
        raise UnqualifiedArchive("INVALID_PIN")

    try:
        parent = db.execute(
            "SELECT lane,experiment,repository,run_id,artifact_id,source_sha,"
            "frozen_manifest_sha256,original_length,chunk_count,scientific_state "
            "FROM forge_research_originals WHERE archive_sha256=?", (pin.archive_sha256,)
        ).fetchone()
        if parent is None or tuple(parent[:7]) != (
            pin.lane, pin.experiment, pin.repository, pin.run_id,
            pin.artifact_id, pin.source_sha, pin.frozen_manifest_sha256
        ):
            raise UnqualifiedArchive("SOURCE_IDENTITY_DRIFT")
        nbytes, count, status = parent[7], parent[8], parent[9]
        if (not isinstance(nbytes, int) or isinstance(nbytes,bool)
            or not 0 < nbytes <= MAX_ORIGINAL_BYTES
            or not isinstance(count, int) or not 0 < count <= MAX_CHUNKS
            or status != "UNQUALIFIED"):
            raise UnqualifiedArchive("SIZE_OR_AUTHORITY_DRIFT")
        sealed = db.execute(
            "SELECT declared_restored_sha256,declared_restored_length,seal_receipt_sha256 "
            "FROM forge_research_seals WHERE archive_sha256=?", (pin.archive_sha256,)
        ).fetchone()
        if (sealed is None or sealed[0] != pin.archive_sha256
            or sealed[1] != nbytes or not _hex(sealed[2],64)):
            raise UnqualifiedArchive("MISSING_OR_FORGED_SEAL_CLAIM")

        chunks = db.execute(
            "SELECT chunk_index,chunk_sha256,chunk_bytes "
            "FROM forge_research_chunks WHERE archive_sha256=? "
            "ORDER BY chunk_index LIMIT 65", (pin.archive_sha256,)
        ).fetchall()
        if len(chunks) != count:
            raise UnqualifiedArchive("PARTIAL_OR_EXTRA_CHUNKS")
        assembled = bytearray()
        for i, (index, chunk_sha, raw) in enumerate(chunks):
            if (index != i or not isinstance(raw, bytes)
                or not 0 < len(raw) <= MAX_CHUNK_BYTES
                or not _hex(chunk_sha,64)
                or not hmac.compare_digest(_sha(raw),chunk_sha)):
                raise UnqualifiedArchive("CHUNK_CORRUPTION")
            assembled.extend(raw)
            if len(assembled)>MAX_ORIGINAL_BYTES:
                raise UnqualifiedArchive("EXCEEDS_ORIGINAL_SIZE")
        if len(assembled)!=nbytes or not hmac.compare_digest(
            _sha(assembled),pin.archive_sha256
        ):
            raise UnqualifiedArchive("ORIGINAL_DIGEST_MISMATCH")
    except (TypeError, OverflowError) as exc:
        raise UnqualifiedArchive("INVALID_RECORD_SHAPE") from exc
    return ByteIntegrityReview(
        lane=pin.lane, archive_sha256=pin.archive_sha256,
        original_length=nbytes, chunk_count=count,
        chunk_digests_verified=True, assembled_original_digest_verified=True
    )
