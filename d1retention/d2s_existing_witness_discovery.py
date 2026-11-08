"""D2S: bounded inventory of already-existing Cloudflare resources, GET only.

Does NOT provision keys, witnesses, scripts, storage, or issue scientific authority.
Cloudflare account identity comes only from the established F62 credential contract.
"""
from __future__ import annotations

import json
import os
import re
import sys

import install_remote as cf

SCHEMA = "forge.f139.d2s.existing-cloudflare-witness-readonly.v1"
KINDS = (
    ("worker_scripts", "workers/scripts?per_page=100&page=1", ("id",)),
    ("durable_object_namespaces", "workers/durable_objects/namespaces?per_page=100&page=1", ("name", "class")),
    ("kv_namespaces", "storage/kv/namespaces?per_page=100&page=1", ("title",)),
)
CANDIDATE = re.compile(r"(?:forge|fsa|witness|highwater|rollback|scientific)", re.I)

class Denied(ValueError):
    pass

def inspect(api):
    if not isinstance(getattr(api, "account", None), str) or not re.fullmatch(r"[a-f0-9]{32}", api.account):
        raise Denied("D2S_ACCOUNT_IDENTITY_NOT_PINNED")
    base = "accounts/" + api.account + "/"
    checks = {}
    for kind, path, identity_keys in KINDS:
        try:
            records = api.call(base + path, method="GET")
        except cf.InstallBlocked as exc:
            code = str(exc)
            if code in ("CLOUDFLARE_HTTP_401", "CLOUDFLARE_HTTP_403"):
                checks[kind] = {"status": "UNREADABLE_NOT_ABSENT", "candidate_names_observed": None,
                                "resource_count_observed": None}
                continue
            raise
        if not isinstance(records, list) or len(records) > 100:
            raise Denied("D2S_RESOURCE_LIST_SHAPE_INVALID")
        if len(records) == 100:
            checks[kind] = {"status": "BOUNDED_NONEXHAUSTIVE", "candidate_names_observed": None,
                            "resource_count_observed": 100}
            continue
        n = 0
        for record in records:
            if not isinstance(record, dict):
                raise Denied("D2S_RESOURCE_IDENTITY_INVALID")
            names = [record.get(k) for k in identity_keys]
            if not any(isinstance(v, str) and 0 < len(v) <= 250 for v in names):
                raise Denied("D2S_RESOURCE_IDENTITY_INVALID")
            if any(isinstance(v, str) and CANDIDATE.search(v) for v in names):
                n += 1
        checks[kind] = {"status": "METADATA_ONLY_NOT_CUSTODY_PROOF",
                        "candidate_names_observed": n,
                        "resource_count_observed": len(records)}
    return {
        "schema": SCHEMA,
        "checks": checks,
        "separate_witness_key_possession_authenticated": False,
        "independently_pinned_monotonic_firstuse_highwater": False,
        "complete_two_lane_original_firstuse_ledger_verified": False,
        "deployment_independence_verified": False,
        "fsa_witness_qualified": False,
        "scientific_execution_authorized": False,
        "new_origins_dispatched": 0,
        "cloudflare_mutations": 0,
        "disposition": "METADATA_INVENTORY_ONLY_SCIENTIFIC_FIRSTUSE_DENIED",
    }

if __name__ == "__main__":
    try:
        api = cf.Cloudflare(os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""),
                            os.environ.get("CLOUDFLARE_API_TOKEN", ""))
        print(json.dumps(inspect(api), sort_keys=True, separators=(",", ":")))
    except (cf.InstallBlocked, Denied) as exc:
        print("D2S_LIVE_INVENTORY_BLOCKED=" + type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)
