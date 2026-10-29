"""Read-only, exact-source authentication of the Yggdrasil ITD-02 negative evidence.

NOT wired into original F139 owner or candidate selection. A proposal, not an
approved steering manifest, dispatch authority, science result, or model release.
"""
from __future__ import annotations

import base64
import binascii
import hashlib

REPOSITORY = "spoonman136668-ai/FORGE"
SOURCE_COMMIT = "38efed14903aa20019bc5cb96d4d756268c48f21"
PATH = "docs/research-steering/YGGDRASIL-ITD02-NEGATIVE-EVIDENCE-1031.md"
BLOB_SHA = "ca5cc791d03533e03f8ef0551c5f386a5b2bde50"
MAX_BYTES = 16384


class EvidenceDenied(ValueError):
    pass


def authenticate(get):
    """Return only provenance if Git contents metadata and bytes match exactly."""
    if not callable(get):
        raise EvidenceDenied("PROVIDER_INVALID")
    route = f"repos/{REPOSITORY}/contents/{PATH}?ref={SOURCE_COMMIT}"
    item = get(route)
    if not (isinstance(item, dict) and item.get("type") == "file"
            and item.get("encoding") == "base64"
            and item.get("sha") == BLOB_SHA
            and type(item.get("size")) is int
            and 0 < item["size"] <= MAX_BYTES
            and isinstance(item.get("content"), str)):
        raise EvidenceDenied("SOURCE_METADATA_INVALID")
    encoded = item["content"].replace("\n", "")
    try:
        raw = base64.b64decode(encoded, validate=True)
        content = raw.decode("utf-8", "strict")
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise EvidenceDenied("SOURCE_BYTES_INVALID") from exc
    calculated = hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()
    if (calculated != BLOB_SHA or len(raw) != item["size"]
            or base64.b64encode(raw).decode("ascii") != encoded
            or "\x00" in content):
        raise EvidenceDenied("SOURCE_IDENTITY_DRIFT")
    if not all(x in content.lower() for x in
               ("yggdrasil", "failed to generalize", "not in that manifest", "source-bound")):
        raise EvidenceDenied("SOURCE_SCOPE_INVALID")
    return {
        "schema": "forge.f139.itd02-negative-evidence-provenance.v1",
        "status": "AUTHENTICATED_UNADMITTED",
        "repository": REPOSITORY,
        "source_commit": SOURCE_COMMIT,
        "path": PATH,
        "blob_sha": BLOB_SHA,
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "advisory_only": True,
        "steering_manifest_admitted": False,
        "candidate_selection_authorized": False,
        "dispatch_authorized": False,
        "scientific_first_use": False,
        "accepted_ref_mutation": False,
    }
