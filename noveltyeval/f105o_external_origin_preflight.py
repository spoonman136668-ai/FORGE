"""F105-O: strict, answer-free external provenance/compatibility preflight.

Only Git HEAD/tree/blob *metadata* is queried for FreebaseQA datasets.
Question, parser, answer and Freebase KG bytes are neither opened nor scored.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

REPO = "kelvin-jiang/FreebaseQA"
HEAD = "d16aae5149aaa25e43ff2a7bd00a06f280ca19b9"
FILES = {
    "README.md": ("dd4c65cbe5428b2a86afc47ae2309cb11328b31b", 3564),
    "LICENSE": ("10fabd90118f7ce38bb2e4753e105e744442a429", 18658),
    "FreebaseQA-train.json": ("24dc4b13a9c4a0ad734732db094c124d086b7d67", 23888089),
    "FreebaseQA-dev.json": ("2e16ac381efb7b9e362cbf9bd0cee90006244ea8", 4656349),
    "FreebaseQA-eval.json": ("d7d06ae721aedca26a0838d0113cddc1aa6774a8", 4660561),
}
DATAFILES = frozenset({"FreebaseQA-train.json", "FreebaseQA-dev.json", "FreebaseQA-eval.json"})
SCHEMA = "forge.optimizer.f105o.external-origin-metadata-eligibility.v1"
VERDICT = "EXTERNAL_ORIGIN_VERIFIED_COMPATIBILITY_BLOCKED"


class Denied(Exception):
    pass


def require(condition: bool, explanation: str) -> None:
    if not condition:
        raise Denied("F105O_METADATA_DENIED_" + explanation)


def git_output(root: Path, command: list[str]) -> str:
    require(not any(a in ("show", "cat-file", "-p", "--batch") for a in command),
            "GIT_CONTENT_READ_NOT_AUTHORIZED")
    # git cat-file -s queries original object size ONLY, not object contents.
    require(command[:2] == ["git", "-C"] and
            command[2] == str(root), "GIT_REPOSITORY_SCOPE")
    proc = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, timeout=25,
    )
    require(proc.returncode == 0, "EXACT_GIT_IDENTITY_UNAVAILABLE")
    output = proc.stdout.decode("ascii", "strict").strip()
    require(output != "" and len(output) < 256, "GIT_METADATA_UNEXPECTED")
    return output


def identify(root: Path) -> dict[str, object]:
    root = root.resolve(strict=True)
    require(root.is_dir(), "SOURCE_DIRECTORY_MISSING")
    head = git_output(root, ["git", "-C", str(root), "rev-parse", "HEAD"])
    require(head == HEAD, "INDEPENDENT_SOURCE_COMMIT_DRIFT")
    objects = {}
    for path, (blob, size) in FILES.items():
        src = "HEAD:" + path
        obj_id = git_output(root, ["git", "-C", str(root), "rev-parse", src])
        obj_size = git_output(root, ["git", "-C", str(root), "cat-file", "-s", src])
        require(obj_id == blob and obj_size.isdecimal() and int(obj_size) == size,
                "IMMUTABLE_ORIGINAL_BLOB_OR_SIZE_DRIFT")
        objects[path] = {"original_git_blob": blob, "original_blob_size": size}
    # README/license are explicitly allowed; three split JSONs never opened.
    readme = root / "README.md"
    license_file = root / "LICENSE"
    require(readme.is_file() and license_file.is_file(), "ONLY_METADATA_FILE_CHECKOUT")
    readme_text = readme.read_text(encoding="utf-8")
    license_text = license_file.read_text(encoding="utf-8")
    require("FreebaseQA" in readme_text and "CC-BY-4.0" in readme_text,
            "AUTHOR_LICENSE_RECORD_UNVERIFIED")
    require("3,996" in readme_text and "20,358" in readme_text and
            "3,994" in readme_text, "ORIGINAL_POPULATION_DOCUMENTATION_DRIFT")
    for field in ("RawQuestion", "ProcessedQuestion", "Parses",
                  "TopicEntityMid", "InferentialChain", "AnswersMid"):
        require(field in readme_text, "INDEPENDENT_SCHEMA_DOCUMENTATION_DRIFT")
    require("Creative Commons" in license_text and
            ("Attribution" in license_text or "attribution" in license_text),
            "CC_BY_LICENSE_RECORD_DRIFT")
    # Files are deliberately absent from sparse materialized worktree.
    for path in DATAFILES:
        require(not (root / path).exists(),
                "EVALUATION_OR_TRAIN_DATA_MATERIALIZED_IN_SPARSE_WORKTREE")
    return objects


def make_report(objects: dict[str, object]) -> dict:
    require(set(objects) == set(FILES), "SOURCE_MEMBERS_INCOMPLETE")
    for key, (want_blob, want_bytes) in FILES.items():
        obj = objects[key]
        require(isinstance(obj, dict) and obj.get("original_git_blob") == want_blob and
                obj.get("original_blob_size") == want_bytes,
                "SOURCE_IDENTITY_FALSE_ACCEPTANCE")
    return {
        "schema": SCHEMA,
        "status": VERDICT,
        "candidate_repo": REPO,
        "candidate_commit": HEAD,
        "declared_license": "CC-BY-4.0",
        "data_splits_original_git_metadata": {
            k: objects[k] for k in sorted(DATAFILES)
        },
        "readme_and_license_object_metadata": {
            k: objects[k] for k in ("README.md", "LICENSE")
        },
        "author_declared_population": {"train": 20358, "dev": 3994, "eval": 3996},
        "population_verified_by_decoding_samples": False,
        "independent_external_author_origin": True,
        "independently_sealed_content_proven": False,
        "f104_policy_frozen_identity": "inverse-two-hop-exact-root-only-removal.v1",
        "f104_parent_head": "cce1aeb9142827aec709971fce2bf6c1f50b164a",
        "requires_separate_question_to_typed_role_adapter": True,
        "requires_separate_freebase_graph_admission": True,
        "requires_independent_evaluator_custody": True,
        "graph_over_f100_budget_per_original_readme": True,
        "candidate_format_is_f101_f102_bracketed_metaqa": False,
        "qa_file_contents_read_by_application": False,
        "evaluation_questions_seen": 0,
        "evaluation_answers_seen": 0,
        "candidate_questions_scored": 0,
        "reported_accuracy": None,
        "new_scientific_firstuse": False,
        "generalization_qualified": False,
        "accepted_science": False,
        "accepted_ref_mutation": False,
        "dream_pareto_promotion": False,
        "thetaevolve_accepted_training": False,
        "science_dispatch": False,
        "model_calls": 0,
        "codex_calls": 0,
        "cloudflare_writes": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-sparse", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    require(not args.out.exists(), "REFUSE_EVIDENCE_OVERWRITE")
    report = make_report(identify(args.upstream_sparse))
    payload = (json.dumps(report, indent=2, sort_keys=True,
                          ensure_ascii=True) + "\n").encode("utf-8")
    # Cross-OS identical evidence bytes, no CRLF normalization.
    with args.out.open("xb") as f:
        f.write(payload)
    print("F105O_INDEPENDENT_ORIGIN_METADATA_ATTESTED=TRUE")
    print("F105O_EXTERNAL_SCHEMA_COMPATIBILITY_AND_SCIENCE=BLOCKED")
    print("F105O_EVAL_QUESTION_OR_ANSWER_BYTES_EXPOSED=ZERO")


if __name__ == "__main__":
    try:
        main()
    except (Denied, OSError, UnicodeError, subprocess.SubprocessError,
            ValueError) as exc:
        print("F105O_SOURCE_METADATA_OR_SEPARATION_DENIED:", exc, file=sys.stderr)
        sys.exit(1)
