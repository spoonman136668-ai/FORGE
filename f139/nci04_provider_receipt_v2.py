"""G14 separate provider V2 receipt integrity reader (development only).

This reader has NO live controller, V1 parser, webhook, or database entrypoint.
Provider metadata + owner-authenticated NativeAdmission are mandatory; SHA256
alone is evidence integrity, not a credential, signer or scientific authority.
"""
from __future__ import annotations

import io
import json
import re
import zipfile

from f139.nci04_native_contract import canonical, digest, require
from f139.nci04_signed_native import NativeAdmission
from f139.nci04_worker_v2 import (
    REPORT_SCHEMA, RECEIPT_SCHEMA, receipt_v2, validate_v2,
)

MEMBERS = frozenset((
    "f139-v2-receipt.json",
    "f139-v2-receipt.sha256",
    "f139-v2-native-report.json",
))
MAX_ZIP = 2_000_000
MAX_MEMBER = 64_000


class V2ProviderDenied(ValueError):
    pass


def gate(value, reason):
    if not value:
        raise V2ProviderDenied("F139_G14_V2_" + reason)


def verify_v2_provider_zip(raw, meta, signed: NativeAdmission, *,
                           require_qualified=True):
    """Validate a genuine provider ZIP against the PREEXISTING signed admission.

    Never upgrade a V1 receipt to V2 and never classify a negative as verified.
    The original owner must independently authenticate workflow/run/artifact ID,
    signature/epoch and recorded immutable SQLite admission before calling.
    """
    gate(type(raw) is bytes and 0 < len(raw) < MAX_ZIP,
         "ZIP_SIZE_INVALID")
    gate(isinstance(meta, dict) and set(meta) == {
             "digest", "size_in_bytes", "run_id", "runner_os", "source_sha"}
         and meta["digest"] == "sha256:"+digest(raw)
         and type(meta["size_in_bytes"]) is int
         and meta["size_in_bytes"] == len(raw)
         and isinstance(signed, NativeAdmission)
         and meta["run_id"] == signed.run_id
         and meta["runner_os"] == signed.runner_os
         and meta["source_sha"] == signed.source_sha,
         "PROVIDER_SIGNED_IDENTITY_MISMATCH")
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos=archive.infolist()
            gate(len(infos)==len(MEMBERS)
                 and {info.filename for info in infos} == MEMBERS
                 and all(not info.is_dir() and info.file_size <= MAX_MEMBER
                         and info.compress_size <= MAX_MEMBER
                         and not (info.flag_bits & 1) for info in infos),
                 "PROVIDER_MEMBER_SET_INVALID")
            blob={name:archive.read(name) for name in MEMBERS}
    except V2ProviderDenied:
        raise
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
        raise V2ProviderDenied("F139_G14_V2_PROVIDER_ZIP_UNREADABLE") from exc
    receipt_raw=blob["f139-v2-receipt.json"]
    report_raw=blob["f139-v2-native-report.json"]
    gate(blob["f139-v2-receipt.sha256"]==
         (digest(receipt_raw)+"  f139-v2-receipt.json\n").encode("ascii"),
         "RECEIPT_SHA_INVALID")
    try:
        receipt=json.loads(receipt_raw)
        report=json.loads(report_raw)
    except (ValueError, UnicodeError) as exc:
        raise V2ProviderDenied("F139_G14_V2_JSON_INVALID") from exc
    gate(isinstance(report, dict) and isinstance(receipt, dict)
         and canonical(report)==report_raw and canonical(receipt)==receipt_raw
         and len(report_raw)<=MAX_MEMBER and len(receipt_raw)<=8192,
         "NONCANONICAL_OR_OVERSIZE")
    gate(report.get("schema")==REPORT_SCHEMA
         and receipt.get("schema")==RECEIPT_SCHEMA
         and receipt.get("development_only") is True
         and receipt.get("scientific_first_use_authorized") is False
         and type(receipt.get("accepted_ref_mutations")) is int
         and receipt["accepted_ref_mutations"]==0,
         "VERSION_OR_AUTHORITY_MISMATCH")
    try:
        expected=receipt_v2(signed, report)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise V2ProviderDenied("F139_G14_V2_SIGNED_REPORT_INVALID") from exc
    gate(receipt==expected,"SIGNED_RECEIPT_OR_RESULT_MISMATCH")
    qualified=validate_v2(signed.intent,report)
    gate(not require_qualified or qualified,
         "INCOMPLETE_NEGATIVE_CANNOT_BE_PROMOTED")
    return {"receipt":receipt,"report":report,"qualified":qualified,
            "artifact_sha256":digest(raw),"version":"v2"}
