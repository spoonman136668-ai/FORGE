"""NCI-04: fail-closed, data-only native candidate contract for F139.

Not wired into the live F139 admission, dispatch, worker or SQLite schema.
No arbitrary commands, controller scheduling, shell, promotion or science access.
A future qualified worker must independently authenticate GitHub source identities,
verify checkout cleanliness/isolation, run the fixed test inventory and retain
original receipts before any contract record can become executable.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass

SCHEMA = "forge.f139.nci04.native-candidate-intent.v1"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
PATH = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]{0,199}\Z")
REPOS = {
    "Wingless": ("spoonman136668-ai/Wingless", ("cognition/", "cmd/wingless/"), ".go"),
    "Yggdrasil": ("spoonman136668-ai/Yggdrasil", ("yggdrasil/", "scripts/"), ".py"),
}
# Exactly two already-preregistered R7 test paths may use the native V1
# development contract. This is not a broad research/ path grant.
# Only this exact, publicly visible native R8 training-session source may
# enter model-generated Wingless drafts; no other research tree is authorized.
WINGLESS_R8_TRAINING = "research/native/itd02/outcome/training_session.go"


def model_source_path_allowed(lane: str, path: str) -> bool:
    if not isinstance(lane, str) or lane not in REPOS or not isinstance(path, str):
        return False
    _, prefixes, suffix = REPOS[lane]
    return (path.startswith(prefixes) and path.endswith(suffix)
            or (lane == "Wingless" and path == WINGLESS_R8_TRAINING))


R7_TEST_PATHS = {
    "Wingless": frozenset({"research/native/itd01/r7/native_test.go"}),
    "Yggdrasil": frozenset({"research/native/itd01/r7/test_native_cells.py"}),
}
MAX_CANDIDATE_BYTES = 32768
FIELDS = frozenset({
    "schema", "controller_source_sha", "lane", "target_repository", "target_commit",
    "target_tree_sha", "dependency_sha256", "qualification_harness_sha256",
    "training_config_sha256", "toolchain_identity", "suite_identity_sha256",
    "path", "before_sha256", "after_sha256", "after_base64", "worker_mode",
    "scientific_first_use", "paid_api_calls", "accepted_ref_mutations",
    "optimizer_policy_mutations", "protected_holdouts_accessed",
})


class NativeContractError(ValueError):
    pass


def require(value: bool, reason: str) -> None:
    if not value:
        raise NativeContractError("F139_NCI04_" + reason)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


@dataclass(frozen=True)
class Candidate:
    intent_sha256: str
    qualification_key: str
    target_commit: str
    target_tree_sha: str
    path: str
    before_sha256: str
    after_sha256: str
    after_bytes: bytes
    lane: str

    def materialize_bytes(self, original: bytes) -> bytes:
        """Construct only bytes; no filesystem, Git, process or network mutation."""
        require(isinstance(original, bytes) and digest(original) == self.before_sha256,
                "ORIGINAL_BYTES_DRIFT")
        return self.after_bytes


def parse_intent(raw: bytes, *, protected_main: str, target_commit: str,
                 target_tree_sha: str) -> Candidate:
    """Parse one immutable candidate only when provider-pinned identities agree.

    The caller must obtain all three identity arguments independently from its
    authenticated, read-only provider inspection; user-authored values alone
    never establish authentic source identity or confer execution authority.
    """
    require(isinstance(raw, bytes) and 0 < len(raw) <= 60000, "INTENT_BYTES_INVALID")
    def unique_object(pairs):
        result = {}
        for key, item in pairs:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = item
        return result
    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise NativeContractError("F139_NCI04_INVALID_JSON") from exc
    require(isinstance(value, dict) and set(value) == FIELDS, "INTENT_FIELDS_INVALID")
    require(value["schema"] == SCHEMA, "SCHEMA_INVALID")
    require(isinstance(protected_main, str) and SHA40.fullmatch(protected_main) is not None
            and value["controller_source_sha"] == protected_main, "CONTROLLER_IDENTITY_DRIFT")
    require(isinstance(target_commit, str) and SHA40.fullmatch(target_commit) is not None
            and value["target_commit"] == target_commit, "TARGET_COMMIT_DRIFT")
    require(isinstance(target_tree_sha, str) and SHA40.fullmatch(target_tree_sha) is not None
            and value["target_tree_sha"] == target_tree_sha, "TARGET_TREE_DRIFT")
    for key in ("dependency_sha256", "qualification_harness_sha256",
                "training_config_sha256", "suite_identity_sha256", "before_sha256", "after_sha256"):
        require(isinstance(value[key], str) and SHA64.fullmatch(value[key]) is not None,
                "DIGEST_INVALID")
    require(isinstance(value["lane"], str) and value["lane"] in REPOS, "LANE_FORBIDDEN")
    repo, prefixes, suffix = REPOS[value["lane"]]
    require(value["target_repository"] == repo, "REPOSITORY_LANE_MISMATCH")
    path = value["path"]
    require(isinstance(path, str) and PATH.fullmatch(path) is not None and "\\" not in path
            and not path.startswith("/")
            and all(part not in ("", ".", "..") and not part.startswith(".")
                    and not part.endswith(".") and part.split(".")[0].casefold() not in
                    {"con", "prn", "aux", "nul", *("com" + str(i) for i in range(1, 10)),
                     *("lpt" + str(i) for i in range(1, 10))}
                    for part in path.split("/"))
            and (model_source_path_allowed(value["lane"], path)
                 or path in R7_TEST_PATHS[value["lane"]]),
            "SOURCE_PATH_FORBIDDEN")
    require(value["toolchain_identity"] in ("go1.25.0", "python3.11.11")
            and (value["toolchain_identity"].startswith("go") == (value["lane"] == "Wingless")),
            "TOOLCHAIN_NOT_QUALIFIED")
    require(value["worker_mode"] == "isolated-candidate-only"
            and value["scientific_first_use"] is False
            and type(value["paid_api_calls"]) is int and value["paid_api_calls"] == 0
            and type(value["accepted_ref_mutations"]) is int and value["accepted_ref_mutations"] == 0
            and type(value["optimizer_policy_mutations"]) is int and value["optimizer_policy_mutations"] == 0
            and type(value["protected_holdouts_accessed"]) is int and value["protected_holdouts_accessed"] == 0,
            "AUTHORITY_ESCALATION_REJECTED")
    encoded = value["after_base64"]
    require(isinstance(encoded, str) and len(encoded) <= (MAX_CANDIDATE_BYTES * 4 // 3 + 8),
            "CANDIDATE_SIZE_INVALID")
    try:
        after = base64.b64decode(encoded, validate=True)
        after.decode("utf-8")
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise NativeContractError("F139_NCI04_CANDIDATE_ENCODING_INVALID") from exc
    require(0 < len(after) <= MAX_CANDIDATE_BYTES and b"\x00" not in after,
            "CANDIDATE_BYTES_INVALID")
    require(base64.b64encode(after).decode("ascii") == encoded and digest(after) == value["after_sha256"]
            and value["before_sha256"] != value["after_sha256"], "CANDIDATE_DIGEST_OR_NOOP")
    identity = {k: value[k] for k in FIELDS if k != "after_base64"}
    # Qualification key includes every semantic identity: source, tree, diff, dependencies,
    # harness, toolchain, suites and training. Incidental issue metadata is excluded.
    qkey = digest(canonical(identity))
    return Candidate(digest(canonical(value)), qkey, target_commit, target_tree_sha,
                     path, value["before_sha256"], value["after_sha256"], after, value["lane"])
