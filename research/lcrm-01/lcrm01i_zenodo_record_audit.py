"""LCRM01-I provider-metadata structural audit: no scientific authority.

The caller cannot self-attest HTTP origin, release bytes, signature or
independent first-use. This code never downloads, opens or evaluates datasets.
"""
from __future__ import annotations

import hashlib
import json
from urllib.parse import urlparse

EXACT_ID = 23095083
EXACT_VERSION = "1.2.0"
EXPECTED_DOI = "10.5281/zenodo.23095083"
SUITE = "dot-Identifiability-v1"


def result(status: str, *, files: list[dict] | None = None, record_sha: str | None = None) -> dict:
    return {"schema": "mass.lcrm01.i.provider-metadata-audit.v1", "status": status,
            "listed_files": files or [], "metadata_canonical_sha256": record_sha,
            "provider_http_origin_authenticated": False,
            "provider_raw_bytes_verified": False,
            "shared_exogenous_noise_verified": False,
            "independent_source_birth_verified": False,
            "scientific_firstuse_authorized": False,
            "original_scientific_firstuse_consumed": 0}


def is_hex_md5(value: object) -> bool:
    return (isinstance(value, str) and len(value) == 36
            and value.startswith("md5:")
            and all(c in "0123456789abcdef" for c in value[4:]))


def name_safe(value: object) -> bool:
    return (isinstance(value, str) and bool(value)
            and value == value.strip() and len(value) <= 160
            and "\\" not in value and not value.startswith("/")
            and all(p not in ("", ".", "..") for p in value.split("/")))


def inspect_record(record: object) -> dict:
    """Validate a supplied JSON object, without authenticating its origin.

    Even syntactically perfect records are untrusted until a separate authority
    captures the remote HTTP response, pinned exact source and raw checksums.
    """
    if not isinstance(record, dict):
        return result("PROVIDER_RECORD_NOT_RETRIEVED")
    if type(record.get("id")) is not int or record.get("id") != EXACT_ID:
        return result("DENY_WRONG_EXACT_RECORD_ID")
    if record.get("doi") != EXPECTED_DOI:
        return result("DENY_CONCEPT_OR_OTHER_VERSION_DOI")
    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        return result("DENY_NO_PROVIDER_METADATA")
    title, version = metadata.get("title"), metadata.get("version")
    if (not isinstance(title, str) or SUITE not in title
            or not isinstance(version, str) or version != EXACT_VERSION):
        return result("DENY_SUITE_OR_VERSION_MISMATCH")
    license_info = metadata.get("license")
    license_id = (license_info.get("id") if isinstance(license_info, dict)
                  else license_info if isinstance(license_info, str) else None)
    if not isinstance(license_id, str) or license_id.lower() != "cc-by-4.0":
        return result("DENY_RELEASE_LICENSE_NOT_CONFIRMED")
    candidates = record.get("files")
    if not isinstance(candidates, list) or not candidates:
        return result("DENY_MISSING_PROVIDER_FILE_INVENTORY")
    files, seen = [], set()
    for row in candidates:
        if not isinstance(row, dict):
            return result("DENY_INVALID_FILE_ROW")
        name = row.get("key") or row.get("filename")
        if not name_safe(name) or name in seen:
            return result("DENY_MALFORMED_OR_DUPLICATE_FILENAME")
        seen.add(name)
        size = row.get("size")
        if type(size) is not int or size <= 0 or size > 10**12:
            return result("DENY_INVALID_PROVIDER_FILE_SIZE")
        checksum = row.get("checksum")
        if not is_hex_md5(checksum):
            return result("DENY_MISSING_OR_INVALID_MD5_CLAIM")
        links = row.get("links")
        link = links.get("self") if isinstance(links, dict) else None
        parsed = urlparse(link) if isinstance(link, str) else None
        if (not parsed or parsed.scheme != "https"
                or parsed.hostname not in ("zenodo.org", "www.zenodo.org")):
            return result("DENY_UNTRUSTED_FILE_LINK")
        files.append({"name": name, "bytes_claimed": size,
                      "provider_claimed_checksum": checksum})
    names = {file["name"] for file in files}
    if "manifest.json" not in names or not any(n.endswith(".parquet") for n in names):
        return result("DENY_NO_RELEASE_MANIFEST_OR_PARQUET_SHARDS")
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True).encode("utf-8")
    return result("PROVIDER_METADATA_SHAPE_CONSISTENT_RAW_BYTES_UNVERIFIED",
                  files=sorted(files, key=lambda v: v["name"]),
                  record_sha=hashlib.sha256(canonical).hexdigest())
