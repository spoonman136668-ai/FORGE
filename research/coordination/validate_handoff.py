"""Offline H5 chat-handoff completeness checks; never converts history into authority."""
import json
import re
import sys
from pathlib import Path

from validate_registry import Invalid, _unique_object_pairs

HANDOFF_SCHEMA = "forge.research-chat-handoff.v1"
MANDATORY = {"native-intelligence", "n-research", "e-research", "replay-acceleration",
             "llm-acceleration", "independent-science", "bio-research", "optimizer-research", "language-research",
             "mass-research", "forge-operations"}
RETIREMENT = {"owner-continuity", "research-handoff", "evidence-routing",
              "unattended-cycles", "science-and-owner-signoff"}
ID = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
URL = re.compile(r"^https://github\.com/spoonman136668-ai/(FORGE|Wingless|Yggdrasil)/pull/([1-9][0-9]*)$")

def _keys(obj, keys):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        raise Invalid("H5_BAD_KEYS")

def _bounded(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 700 or any(x in value for x in "\r\n\x00"):
        raise Invalid("H5_BAD_TEXT")

def validate_handoff(raw):
    if not isinstance(raw, bytes) or len(raw) < 2 or len(raw) > 65536:
        raise Invalid("H5_BAD_LENGTH")
    try:
        obj = json.loads(raw, object_pairs_hook=_unique_object_pairs)
    except (ValueError, UnicodeDecodeError) as e:
        raise Invalid("H5_BAD_JSON") from e
    _keys(obj, {"schema","observed_on","snapshot_forge_main","advisory_only",
                "execution_authorized","chat_retirement_ready","inventory_completeness",
                "protected_boundaries","workstreams","retirement_gates"})
    if obj["schema"] != HANDOFF_SCHEMA or obj["observed_on"] != "2026-10-30":
        raise Invalid("H5_UNKNOWN_SCHEMA_OR_SNAPSHOT")
    if not isinstance(obj["snapshot_forge_main"], str) or not SHA.fullmatch(obj["snapshot_forge_main"]):
        raise Invalid("H5_UNPINNED_MAIN")
    if obj["advisory_only"] is not True or obj["execution_authorized"] is not False or obj["chat_retirement_ready"] is not False or obj["inventory_completeness"] != "UNVERIFIED":
        raise Invalid("H5_FORBIDDEN_AUTHORITY_OR_RETIREMENT")
    boundaries = obj["protected_boundaries"]
    if not isinstance(boundaries, list) or not 6 <= len(boundaries) <= 20:
        raise Invalid("H5_BOUNDARY_COUNT")
    for x in boundaries: _bounded(x)
    rows=obj["workstreams"]
    if not isinstance(rows, list) or not 11 <= len(rows) <= 40:
        raise Invalid("H5_MISSING_WORKSTREAMS")
    seen=set()
    for row in rows:
        _keys(row, {"id","source_owner","oversight","separate_scientific_lineage",
                    "source_pointers","unverified_handoff","handoff_status"})
        ident=row["id"]
        if not isinstance(ident,str) or not ID.fullmatch(ident) or ident in seen:
            raise Invalid("H5_DUPLICATE_OR_INVALID_ID")
        seen.add(ident)
        _bounded(row["source_owner"])
        _bounded(row["unverified_handoff"])
        if row["oversight"] != ("forge-operations" if ident=="forge-operations" else "unified-research"):
            raise Invalid("H5_WRONG_OVERSIGHT")
        if row["separate_scientific_lineage"] is not True or row["handoff_status"] != "UNVERIFIED":
            raise Invalid("H5_CROSS_LANE_OR_FABRICATED_PASS")
        pointers=row["source_pointers"]
        if not isinstance(pointers, list) or len(pointers) > 10:
            raise Invalid("H5_UNBOUNDED_POINTERS")
        for ref in pointers:
            _keys(ref, {"url","sha","claim"})
            if (not isinstance(ref["url"],str) or not URL.fullmatch(ref["url"]) or
                not isinstance(ref["sha"],str) or not SHA.fullmatch(ref["sha"]) or
                ref["claim"] != "SOURCE_POINTER_ONLY"):
                raise Invalid("H5_BAD_SOURCE_POINTER")
        if ident=="forge-operations" and not pointers:
            raise Invalid("H5_ORIGINAL_OWNER_WITNESS_MISSING")
        if ident=="mass-research" and not any(
            ref["url"] == "https://github.com/spoonman136668-ai/Yggdrasil/pull/423"
            and ref["sha"] == "d31c8d00ccc2bb00f098b87097610329637a37f6"
            for ref in pointers
        ):
            raise Invalid("H13_MASS_SYMBOLIC_SOURCE_WITNESS_MISSING")
        if ident=="language-research":
            required_language = {
                ("https://github.com/spoonman136668-ai/FORGE/pull/820", "d15ce497843244894642735ee218a185bb87c1e4"),
                ("https://github.com/spoonman136668-ai/FORGE/pull/945", "407004e7b962c2baac45bd2ed8c6c1c14868d647"),
            }
            observed_language = {(ref["url"], ref["sha"]) for ref in pointers}
            if observed_language != required_language or len(pointers) != len(required_language):
                raise Invalid("H17_LANGUAGE_SOURCE_WITNESS_MISSING_OR_SUBSTITUTED")
    if not MANDATORY.issubset(seen):
        raise Invalid("H5_REQUIRED_INDEPENDENT_WORKSTREAM_MISSING")
    if not isinstance(obj["retirement_gates"], list) or set(obj["retirement_gates"]) != RETIREMENT or len(obj["retirement_gates"]) != len(RETIREMENT):
        raise Invalid("H5_RETIREMENT_GATES_DRIFT")
    return {"handoff_index_valid":True,"retirement_ready":False,"workstreams":len(rows),
            "reason":"No signed original-owner or research custody transfer from advisory evidence"}

def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if len(args)!=1:
        print("Usage: validate_handoff.py handoff.v1.json",file=sys.stderr)
        return 2
    try:
        result=validate_handoff(Path(args[0]).read_bytes())
    except (OSError,Invalid) as e:
        print("INVALID_HANDOFF: "+str(e),file=sys.stderr)
        return 1
    print(json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    sys.exit(main())
