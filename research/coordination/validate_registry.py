"""Offline advisory registry validation only; never an execution or acceptance oracle."""
import json
import re
import sys
from pathlib import Path

SCHEMA = "forge.unified-research-coordination.v1"
CANONICAL = {"wingless", "yggdrasil", "bio", "optimizer", "mass-research", "language-research"}
# Original RSH-01 source custody: six independently owned evidence lanes.
# A trusted repository is not interchangeable with another trusted owner.
CANONICAL_OWNERS = {
    "wingless": ("spoonman136668-ai/Wingless", "native"),
    "yggdrasil": ("spoonman136668-ai/Yggdrasil", "native"),
    "bio": ("spoonman136668-ai/FORGE", "support"),
    "optimizer": ("spoonman136668-ai/FORGE", "support"),
    "mass-research": ("spoonman136668-ai/FORGE", "support"),
    "language-research": ("spoonman136668-ai/FORGE", "support"),
}
GATES = {"owner-continuity", "research-handoff", "evidence-routing", "unattended-cycles", "science-and-owner-signoff"}
FALSE_CAPABILITIES = {"execute", "dispatch", "scientific_accept", "first_use", "promote", "deploy",
                      "modify_controller", "create_scheduler", "modify_queues"}
ID = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
URL = re.compile(r"^https://github\.com/spoonman136668-ai/(FORGE|Wingless|Yggdrasil)/(pull/[0-9]+|blob/[0-9a-f]{40}/[a-zA-Z0-9_./-]+)$")


class Invalid(ValueError):
    pass


def _unique_object_pairs(pairs):
    obj = {}
    for key, val in pairs:
        if not isinstance(key, str) or key.lower() in {k.lower() for k in obj}:
            raise Invalid("duplicate or invalid JSON key")
        obj[key] = val
    return obj


def _keys(obj, expected):
    if not isinstance(obj, dict) or set(obj) != set(expected):
        raise Invalid("invalid object keys")


def _line(text):
    if not isinstance(text, str) or not text.strip() or len(text) > 600 or "\n" in text:
        raise Invalid("invalid bounded text")


def _check_id(text):
    if not isinstance(text, str) or not ID.fullmatch(text):
        raise Invalid("invalid id")


def validate(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 65536:
        raise Invalid("invalid input length")
    try:
        root = json.loads(raw, object_pairs_hook=_unique_object_pairs)
    except (ValueError, UnicodeDecodeError) as exc:
        raise Invalid("malformed JSON") from exc
    _keys(root, {"schema", "generated_from_forge_main", "advisory_only", "authority",
                 "oversight", "tracks", "readiness_gates", "targets"})
    if root["schema"] != SCHEMA or root["advisory_only"] is not True:
        raise Invalid("invalid schema or advisory boundary")
    if not isinstance(root["generated_from_forge_main"], str) or not SHA.fullmatch(root["generated_from_forge_main"]):
        raise Invalid("non-immutable baseline")
    auth = root["authority"]
    _keys(auth, FALSE_CAPABILITIES)
    if any(value is not False for value in auth.values()):
        raise Invalid("authority escalation denied")
    oversight = root["oversight"]
    if not isinstance(oversight, list) or len(oversight) != 2:
        raise Invalid("exactly two oversight roles required")
    for role in oversight:
        _keys(role, {"id", "responsibility"})
        _check_id(role["id"])
        _line(role["responsibility"])
    if {r["id"] for r in oversight} != {"forge-operations", "unified-research"}:
        raise Invalid("oversight role drift")
    tracks = root["tracks"]
    if not isinstance(tracks, list) or not 6 <= len(tracks) <= 40:
        raise Invalid("bounded, preserved scientific lanes required")
    seen = set()
    for track in tracks:
        _keys(track, {"id", "scope", "custodian_repo", "evidence_route", "source_pointer",
                      "source_status", "scientific_status", "next_goal"})
        ident = track["id"]
        _check_id(ident)
        if ident.lower() in seen:
            raise Invalid("duplicate lane")
        seen.add(ident.lower())
        if track["scope"] not in ("native", "support", "discovery", "methods"):
            raise Invalid("unsupported scope")
        if track["custodian_repo"] not in ("spoonman136668-ai/FORGE",
                                           "spoonman136668-ai/Wingless",
                                           "spoonman136668-ai/Yggdrasil"):
            raise Invalid("untrusted custodian")
        if ident in CANONICAL_OWNERS:
            # Do not silently move a canonical source owner or reclassify
            # an independent native architecture as a support science lane.
            if (track["custodian_repo"], track["scope"]) != CANONICAL_OWNERS[ident]:
                raise Invalid("original scientific lane owner or scope drift")
        if track["evidence_route"] != ("EXISTING_SIX_LANE" if ident in CANONICAL else "SEPARATE_ADVISORY"):
            raise Invalid("unqualified evidence-route expansion")
        if track["source_status"] != "POINTER_ONLY" or track["scientific_status"] != "UNVERIFIED":
            raise Invalid("unsupported acceptance or source claim")
        pointer = track["source_pointer"]
        if not isinstance(pointer, str) or not URL.fullmatch(pointer):
            raise Invalid("untrusted source pointer")
        # Require the referenced GitHub repository to match declared custody
        # even for advisory-only added tracks. This does not authenticate
        # the PR, original source bytes, or permission to use them.
        if not pointer.startswith("https://github.com/" + track["custodian_repo"] + "/"):
            raise Invalid("source pointer crosses declared custodian")
        if "/blob/" in pointer:
            # GitHub URLs with traversal, dot segments or repeated separators
            # are ambiguous provenance even when the repository is allowlisted.
            relative_path = pointer.split("/blob/", 1)[1].split("/", 1)[1]
            if any(part in ("", ".", "..") for part in relative_path.split("/")):
                raise Invalid("noncanonical source pointer path")
        _line(track["next_goal"])
    if not CANONICAL.issubset(seen):
        raise Invalid("lost original evidence lanes")
    gates = root["readiness_gates"]
    if not isinstance(gates, list) or len(gates) != len(GATES):
        raise Invalid("readiness gate count")
    gs = set()
    for gate in gates:
        _keys(gate, {"id", "status", "criterion", "evidence"})
        _check_id(gate["id"])
        if gate["id"] in gs:
            raise Invalid("duplicate readiness gate")
        gs.add(gate["id"])
        _line(gate["criterion"])
        if gate["status"] != "UNVERIFIED" or gate["evidence"] != []:
            raise Invalid("do not self-certify readiness in advisory data")
    if gs != GATES:
        raise Invalid("readiness gate identities")
    _keys(root["targets"], {"research_chat_count", "qualified_throughput_speedup_target", "learning_speedup_claim"})
    t = root["targets"]
    # The two oversight ROLES are not the number of scientific conversations.
    # Preserve the three separately scoped research discussions agreed at H54.
    if type(t["research_chat_count"]) is not int or t["research_chat_count"] != 3:
        raise Invalid("three-research-chat target drift")
    if type(t["qualified_throughput_speedup_target"]) is not int or t["qualified_throughput_speedup_target"] != 2:
        raise Invalid("unfounded target")
    if t["learning_speedup_claim"] != "UNVERIFIED":
        raise Invalid("fabricated learning-speed result")
    return {"registry_valid": True, "tracks": len(tracks), "advisory_only": True,
            "retirement_ready": False, "reason": "Independent original-owner and research-gate evidence required"}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Usage: python validate_registry.py registry.v1.json", file=sys.stderr)
        return 2
    try:
        report = validate(Path(args[0]).read_bytes())
    except (OSError, Invalid) as exc:
        print("INVALID_REGISTRY: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
