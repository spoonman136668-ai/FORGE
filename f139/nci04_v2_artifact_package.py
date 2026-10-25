"""G33 deterministic, bounded V2 DEVELOPMENT evidence packaging.

Converts the credential-free V2 worker's two canonical JSON outputs into the
exact three members understood by the independently versioned G14 ZIP reader.
This writes no GitHub artifact, original-owner event, or scientific permission.
A locally constructed metadata digest is NOT a provider-authenticated receipt.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import stat
import zipfile

from f139.nci04_native_contract import canonical, digest
from f139.nci04_provider_receipt_v2 import (
    MAX_MEMBER, MAX_ZIP, MEMBERS, verify_v2_provider_zip,
)
from f139.nci04_signed_native import NativeAdmission
from f139.nci04_worker_v2 import receipt_v2

INPUT_RECEIPT = "f139-v2-development-receipt.json"
INPUT_REPORT = "f139-v2-development-report.json"
PACKAGE = "f139-v2-development-provider.zip"
FROZEN_INPUTS = frozenset((INPUT_RECEIPT, INPUT_REPORT))
OUTPUT_MEMBERS = (
    "f139-v2-receipt.json",
    "f139-v2-receipt.sha256",
    "f139-v2-native-report.json",
)


class V2PackagingDenied(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise V2PackagingDenied("F139_G33_" + reason)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _canonical_file(path: Path, *, limit: int) -> tuple[bytes, dict]:
    # Reject file symlinks and strange files before reading; a caller must
    # already own an isolated output directory without concurrent writers.
    require(not path.is_symlink() and path.is_file(),
            "V2_SOURCE_FILE_NOT_REGULAR")
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= limit,
            "V2_SOURCE_FILE_SIZE_INVALID")
    raw = path.read_bytes()
    require(0 < len(raw) <= limit, "V2_SOURCE_READ_SIZE_INVALID")
    try:
        value = json.loads(raw, object_pairs_hook=_unique)
    except V2PackagingDenied:
        raise
    except (ValueError, UnicodeError) as exc:
        raise V2PackagingDenied("F139_G33_SOURCE_JSON_INVALID") from exc
    require(isinstance(value, dict) and canonical(value) == raw,
            "V2_SOURCE_NONCANONICAL")
    return raw, value


def _archive(parts: dict[str, bytes]) -> bytes:
    require(set(parts) == MEMBERS and len(parts) == 3,
            "V2_MEMBER_SET_INVALID")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED,
                         allowZip64=False) as z:
        for name in OUTPUT_MEMBERS:
            blob = parts[name]
            require(type(blob) is bytes and 0 < len(blob) <= MAX_MEMBER,
                    "V2_MEMBER_BYTES_INVALID")
            item = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_STORED
            item.external_attr = 0o100644 << 16
            z.writestr(item, blob)
    data = out.getvalue()
    require(0 < len(data) < MAX_ZIP, "V2_ARCHIVE_TOO_LARGE")
    return data


def package_v2_development_output(output: Path,
                                  admission: NativeAdmission) -> dict:
    """Build and *locally* verify one inert ZIP after a V2 API execution.

    No remote provider or actual owner custody is assumed. Caller supplies an
    authenticated NativeAdmission from the existing original owner; provider
    must separately authenticate real run/artifact metadata after upload.
    """
    output = Path(output)
    require(type(admission) is NativeAdmission
            and output.is_dir() and not output.is_symlink(),
            "V2_OUTPUT_OR_SIGNED_ADMISSION_INVALID")
    contents = list(output.iterdir())
    require({p.name for p in contents} == FROZEN_INPUTS
            and len(contents) == len(FROZEN_INPUTS),
            "V2_INPUT_INVENTORY_OR_REPLAY_INVALID")
    raw_receipt, receipt = _canonical_file(
        output / INPUT_RECEIPT, limit=8192)
    raw_report, report = _canonical_file(
        output / INPUT_REPORT, limit=MAX_MEMBER)
    # The G13 signature binding and exhaustive fixed report checks occur
    # before any ZIP is written, even for a negative test outcome.
    expected = receipt_v2(admission, report)
    require(receipt == expected, "V2_SIGNED_RECEIPT_OR_REPORT_MISMATCH")
    checkfile = (
        digest(raw_receipt) + "  f139-v2-receipt.json\n"
    ).encode("ascii")
    parts = {
        OUTPUT_MEMBERS[0]: raw_receipt,
        OUTPUT_MEMBERS[1]: checkfile,
        OUTPUT_MEMBERS[2]: raw_report,
    }
    raw_zip = _archive(parts)
    # Locally constructed metadata validates byte shape/binding ONLY,
    # never provenance of a genuine GitHub Actions job or provider artifact.
    local_metadata = {
        "digest": "sha256:" + digest(raw_zip),
        "size_in_bytes": len(raw_zip),
        "run_id": admission.run_id,
        "runner_os": admission.runner_os,
        "source_sha": admission.source_sha,
    }
    local = verify_v2_provider_zip(
        raw_zip, local_metadata, admission, require_qualified=False)
    require(local["receipt"] == expected
            and local["qualified"] is receipt["native_qualified"],
            "V2_LOCAL_ROUNDTRIP_MISMATCH")
    dst = output / PACKAGE
    with dst.open("xb") as stream:
        stream.write(raw_zip)
        stream.flush()
        os.fsync(stream.fileno())
    return {
        "schema": "forge.f139.g33.v2-development-zip-packaged.v1",
        "filename": PACKAGE,
        "zip_sha256": digest(raw_zip),
        "zip_size_bytes": len(raw_zip),
        "native_qualified": local["qualified"],
        "development_only": True,
        "provider_origin_authenticated": False,
        "owner_event_written": False,
        "scientific_first_use_authorized": False,
        "accepted_ref_mutations": 0,
        "paid_model_calls": 0,
    }
