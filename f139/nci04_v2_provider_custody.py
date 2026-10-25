"""G14 detached, read-only V2 provider ZIP custody; no owner or worker wiring.

Provider metadata and NativeAdmission MUST come from separately authenticated
sources. A SHA256 digest by itself is not a signature and cannot authorize
a new research task. This parser cannot replay original ticket #907.
"""
from __future__ import annotations

import io
import json
import re
import stat
import zipfile

from f139.nci04_native_contract import NativeContractError, canonical, digest, require
from f139.nci04_signed_native import NativeAdmission
from f139.nci04_worker_v2 import RECEIPT_SCHEMA, REPORT_SCHEMA, receipt_v2

MEMBERS = frozenset((
    "f139-receipt.json", "f139-receipt.sha256",
    "f139-native-report.json",
))
MAX_ZIP = 2_000_000
MAX_RECEIPT = 8192
MAX_REPORT = 64_000
SHA = re.compile(r"sha256:[a-f0-9]{64}\Z")


def _unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, "V2_DUPLICATE_JSON_FIELD")
        value[key] = item
    return value


def _json(data: bytes, max_bytes: int):
    require(isinstance(data, bytes) and 0 < len(data) <= max_bytes,
            "V2_JSON_SIZE_INVALID")
    try:
        item = json.loads(data.decode("utf-8"), object_pairs_hook=_unique)
    except (UnicodeError, ValueError) as exc:
        raise NativeContractError("F139_NCI04_V2_MALFORMED_JSON") from exc
    require(isinstance(item, dict) and canonical(item) == data,
            "V2_NONCANONICAL_JSON")
    return item


def inspect_provider_v2_zip(raw: bytes, *, admission: NativeAdmission,
                            provider_sha256: str, provider_size: int,
                            provider_run_id: int, provider_head_sha: str,
                            artifact_name: str) -> dict:
    """Return a diagnostic, never an owner admission or a scientific approval."""
    require(type(raw) is bytes and 0 < len(raw) <= MAX_ZIP,
            "V2_PROVIDER_ZIP_SIZE_INVALID")
    require(isinstance(admission, NativeAdmission),
            "V2_ORIGINAL_SIGNED_ADMISSION_REQUIRED")
    require(isinstance(provider_sha256, str)
            and SHA.fullmatch(provider_sha256) is not None
            and provider_sha256 == "sha256:" + digest(raw)
            and type(provider_size) is int and provider_size == len(raw),
            "V2_PROVIDER_ARTIFACT_DIGEST_MISMATCH")
    require(type(provider_run_id) is int and
            provider_run_id == admission.run_id and
            provider_head_sha == admission.source_sha and
            artifact_name == "forge-f139-native-receipt-" + admission.runner_os,
            "V2_PROVIDER_RUN_OR_OS_IDENTITY_DRIFT")
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
        with archive:
            files = archive.infolist()
            require(len(files) == len(MEMBERS) and
                    set(f.filename for f in files) == MEMBERS,
                    "V2_PROVIDER_ZIP_MEMBERS_INVALID")
            for entry in files:
                require(not entry.is_dir()
                        and entry.file_size <= (
                            MAX_REPORT if entry.filename=="f139-native-report.json"
                            else MAX_RECEIPT)
                        and (entry.external_attr >> 16 & 0o170000)
                            not in (stat.S_IFLNK, stat.S_IFDIR)
                        and entry.compress_type in (
                            zipfile.ZIP_DEFLATED, zipfile.ZIP_STORED),
                        "V2_PROVIDER_ZIP_MEMBER_UNSAFE")
            receipt_data = archive.read("f139-receipt.json")
            sidecar = archive.read("f139-receipt.sha256")
            report_data = archive.read("f139-native-report.json")
    except (zipfile.BadZipFile, OSError, RuntimeError, ValueError) as exc:
        raise NativeContractError("F139_NCI04_V2_PROVIDER_ZIP_INVALID") from exc
    require(sidecar == (digest(receipt_data) +
                        "  f139-receipt.json\n").encode("ascii"),
            "V2_PROVIDER_RECEIPT_DIGEST_DRIFT")
    report = _json(report_data, MAX_REPORT)
    receipt = _json(receipt_data, MAX_RECEIPT)
    require(report.get("schema") == REPORT_SCHEMA
            and receipt.get("schema") == RECEIPT_SCHEMA,
            "V2_RECEIPT_SCHEMA_DOWNGRADE_DENIED")
    expected = receipt_v2(admission, report)
    require(receipt == expected, "V2_PROVIDER_ORIGINAL_ADMISSION_BINDING_DRIFT")
    require(receipt["native_qualified"] is expected["native_qualified"]
            and receipt["scientific_first_use_authorized"] is False,
            "V2_PROVIDER_SCIENTIFIC_AUTHORITY_DENIED")
    return {
        "schema": "forge.f139.nci04.provider-v2-custody-diagnostic.v1",
        "run_id": admission.run_id,
        "os": admission.runner_os,
        "zip_sha256": digest(raw),
        "report_sha256": digest(report_data),
        "native_qualified": expected["native_qualified"],
        "scientific_first_use": False,
        "development_only": True,
        "owner_admission": False,
    }
