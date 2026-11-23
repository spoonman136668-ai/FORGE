"""GET-only first step of a future original-owner F139 V3 source forward.

Run this BEFORE any Disable/Stop-ScheduledTask action. This does not create a
certificate, verify original Windows cold state, dispatch work, or grant a
PREPARE or START authority. It does not change the original V1/V2 installation.
"""
from __future__ import annotations

import base64
import binascii
import json
import os
import re
import subprocess
import sys

from f139.nci04_native_contract import canonical
from f139.nci04_v3_remote_readonly_preflight import (
    V3RemotePreflightDenied, inspect_merged_source_readonly,
)

FIELDS = frozenset((
    "owner_source_sha", "owner_source_tree", "pr_number", "pr_head_sha",
    "regression_run_id", "source_run_id", "rehearsal_run_id",
))
REPO = "repos/spoonman136668-ai/FORGE"
ROUTE = re.compile(
    r"repos/spoonman136668-ai/FORGE/(?:branches/main|"
    r"git/commits/[a-f0-9]{40}|pulls/[1-9][0-9]*|"
    r"compare/[a-f0-9]{40}\.\.\.[a-f0-9]{40}|"
    r"actions/runs/[1-9][0-9]*(?:/jobs\?per_page=100)?)\Z"
)


class V3OwnerRemoteDenied(ValueError):
    pass


def deny(code):
    raise V3OwnerRemoteDenied("F139_V3_OWNER_REMOTE_" + code)


def _unique_pairs(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            deny("DUPLICATE_JSON_KEY")
        result[name] = value
    return result


def decode_request(encoded):
    """Canonical typed request; fail before network on bad scope or replay."""
    if type(encoded) is not str or not 0 < len(encoded) <= 4096:
        deny("REQUEST_SIZE")
    try:
        raw = base64.b64decode(encoded, validate=True)
        if not 0 < len(raw) <= 3072:
            deny("REQUEST_SIZE")
        doc = json.loads(raw.decode("ascii"), object_pairs_hook=_unique_pairs)
    except (binascii.Error, UnicodeError, ValueError) as exc:
        raise V3OwnerRemoteDenied("F139_V3_OWNER_REMOTE_REQUEST_INVALID") from exc
    if type(doc) is not dict or set(doc) != FIELDS or raw != canonical(doc):
        deny("REQUEST_NONCANONICAL_OR_SCOPE")
    if (type(doc["pr_number"]) is not int or doc["pr_number"] <= 1870
            or any(type(doc[k]) is not int or not 0 < doc[k] < 2**63
                   for k in ("regression_run_id", "source_run_id",
                             "rehearsal_run_id"))
            or any(type(doc[k]) is not str or
                   re.fullmatch(r"[a-f0-9]{40}", doc[k]) is None
                   for k in ("owner_source_sha", "owner_source_tree",
                             "pr_head_sha"))):
        deny("REQUEST_FIELDS")
    return doc


class GitHubGET:
    """Fixed-route read-only gh API adapter; no POST, shell or task access."""

    def get(self, route):
        if type(route) is not str or ROUTE.fullmatch(route) is None:
            deny("UNSAFE_PROVIDER_ROUTE")
        if len(os.environ.get("GH_TOKEN", "")) < 16:
            deny("EXPLICIT_READ_CREDENTIAL_REQUIRED")
        try:
            command = ["gh", "api", "--method", "GET", route]
            reply = subprocess.run(
                command, capture_output=True, text=True, timeout=30,
                check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise V3OwnerRemoteDenied(
                "F139_V3_OWNER_REMOTE_PROVIDER_UNAVAILABLE") from exc
        if reply.returncode != 0 or not 0 < len(reply.stdout) <= 1_000_000:
            deny("PROVIDER_READ_FAILED")
        try:
            result = json.loads(reply.stdout, object_pairs_hook=_unique_pairs)
        except ValueError as exc:
            raise V3OwnerRemoteDenied(
                "F139_V3_OWNER_REMOTE_PROVIDER_JSON_INVALID") from exc
        if type(result) is not dict:
            deny("PROVIDER_DOCUMENT_INVALID")
        return result


def inspect_before_owner_stop(encoded, *, api=None):
    params = decode_request(encoded)
    result = inspect_merged_source_readonly(
        GitHubGET() if api is None else api, **params)
    if (result["remote_evidence"] != "VERIFIED_READ_ONLY"
            or result["safe_to_disable_task"] is not False
            or result["signed_source_forward"] is not False
            or result["worker_dispatches"] != 0
            or result["scientific_first_use"] is not False):
        deny("UNEXPECTED_AUTHORITY")
    return result


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) != 1:
            deny("ARGUMENTS")
        inspect_before_owner_stop(args[0])
    except (V3OwnerRemoteDenied, V3RemotePreflightDenied):
        print("F139_V3_OWNER_REMOTE_PREFLIGHT=DENIED", file=sys.stderr)
        return 2
    print("F139_V3_OWNER_REMOTE_PREFLIGHT=READ_ONLY_PASS")
    print("F139_V3_ORIGINAL_COLD_CUSTODY=NOT_CHECKED")
    print("F139_V3_TASK_MUTATION_AUTHORIZED=FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
