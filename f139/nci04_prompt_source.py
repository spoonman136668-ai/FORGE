"""Validate actual Promptbreeder outputs against source-backed recipe bindings.

No prompt is interpreted as Python or as permission. Every member of the
frozen output population must have an independently pinned source artifact.
This pure boundary neither invokes an optimizer nor publishes or dispatches.
"""
from dataclasses import dataclass
import json
import re

from f139.nci04_portfolio_source_boundary import (
    PortfolioSourceRejected, SourceCandidate, _sha, validate_generation_batch,
)

DOMAIN = b"FORGE-F139-PROMPT-SOURCE-BINDINGS-V1\n"


def need(ok, reason):
    if not ok:
        raise PortfolioSourceRejected("PROMPT_SOURCE_" + reason)


def encoded(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def sha_pin(value):
    return type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "DUPLICATE_JSON_FIELD")
        result[key] = value
    return result


@dataclass(frozen=True)
class SourceBinding:
    prompt: str
    source: SourceCandidate


@dataclass(frozen=True)
class PromptSourceBatch:
    candidates: tuple
    generator_result_sha256: str
    frozen_sha256: str
    bindings_sha256: str
    mechanism_sha256: str
    source_sha: str


def bindings_digest(bindings):
    """Bind the complete recipe/source manifest, including research text.

    The expected pin is an external input, never inferred from optimizer JSON.
    Source bytes are independently checked against their recorded identities.
    """
    need(type(bindings) is tuple and 1 <= len(bindings) <= 16, "BINDINGS_BOUND")
    rows = []
    for binding in bindings:
        need(type(binding) is SourceBinding and type(binding.prompt) is str
             and type(binding.source) is SourceCandidate, "SOURCE_BINDING_REQUIRED")
        c = binding.source
        need(type(c.after) is bytes and _sha(c.after) == c.after_sha256, "BINDING_SOURCE_DRIFT")
        rows.append(dict(prompt=binding.prompt, generator=c.generator, lane=c.lane,
            path=c.path, parent_sha=c.parent_sha, before_sha256=c.before_sha256,
            after_sha256=c.after_sha256, mechanism_sha256=c.mechanism_sha256,
            question=c.question, hypothesis=c.hypothesis))
    return _sha(DOMAIN + encoded(rows))


def frozen_digest(frozen):
    """Exact Go promptlineage.Frozen JSON ordering and omitempty semantics."""
    need(type(frozen) is dict and set(frozen) == {
        "schema", "lane", "epoch", "source_sha", "parent", "vocabulary",
        "max_operations", "operations"}, "FROZEN_FIELDS")
    need(frozen["schema"] == "forge.promptlineage.frozen.v1"
         and frozen["lane"] in ("Wingless", "Yggdrasil")
         and type(frozen["epoch"]) is int and 0 < frozen["epoch"] < 2**64
         and type(frozen["source_sha"]) is str
         and re.fullmatch(r"[a-f0-9]{40}", frozen["source_sha"]) is not None,
         "FROZEN_IDENTITY")
    word = lambda x: type(x) is str and re.fullmatch(r"[a-z0-9-]{1,24}", x) is not None
    parent, vocab, ops = frozen["parent"], frozen["vocabulary"], frozen["operations"]
    need(type(parent) is str and 3 <= len(parent) <= 512
         and 2 <= len(parent.split(" ")) <= 24 and all(map(word, parent.split(" ")))
         and type(vocab) is list and 1 <= len(vocab) <= 24 and all(map(word, vocab))
         and len(set(vocab)) == len(vocab), "FROZEN_VOCABULARY")
    need(type(frozen["max_operations"]) is int and 1 <= frozen["max_operations"] <= 32
         and type(ops) is list and 1 <= len(ops) <= min(16, frozen["max_operations"]),
         "POPULATION_BOUND")
    normalized_ops = []
    for op in ops:
        need(type(op) is dict and {"kind", "position"} <= set(op)
             <= {"kind", "position", "replacement"}, "OPERATION_FIELDS")
        need(type(op["position"]) is int and 0 <= op["position"] < len(parent.split(" ")),
             "OPERATION_POSITION")
        item = dict(kind=op["kind"], position=op["position"])
        replacement = op.get("replacement", "")
        if op["kind"] == "replace":
            need(replacement in vocab and replacement != parent.split(" ")[op["position"]],
                 "OPERATION_REPLACEMENT")
            item["replacement"] = replacement
        else:
            need(op["kind"] == "swap-next" and replacement == ""
                 and op["position"]+1 < len(parent.split(" "))
                 and parent.split(" ")[op["position"]] != parent.split(" ")[op["position"]+1],
                 "OPERATION_KIND")
        normalized_ops.append(item)
    ordered = {key: frozen[key] for key in (
        "schema", "lane", "epoch", "source_sha", "parent", "vocabulary", "max_operations")}
    ordered["operations"] = normalized_ops
    return _sha(b"FORGE-PROMPTLINEAGE-FROZEN-V1\n" + encoded(ordered))


def compile_prompt_sources(raw, *, result_sha256, frozen, frozen_sha256,
                           bindings, bindings_sha256, mechanism, mechanism_sha256,
                           lane, path, parent_sha, before,
                           historical_sha256, historical_ast_sha256):
    need(type(raw) is bytes and 0 < len(raw) <= 256_000 and sha_pin(result_sha256)
         and _sha(raw) == result_sha256, "RESULT_DRIFT")
    need(sha_pin(frozen_sha256) and frozen_digest(frozen) == frozen_sha256
         and frozen["lane"] == lane and frozen["source_sha"] == parent_sha,
         "FROZEN_DRIFT")
    need(sha_pin(bindings_sha256) and bindings_digest(bindings) == bindings_sha256,
         "BINDINGS_DRIFT")
    try:
        envelope = json.loads(raw, object_pairs_hook=unique_object)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise PortfolioSourceRejected("PROMPT_SOURCE_RESULT_JSON") from exc
    need(type(envelope) is dict and set(envelope) == {"schema", "source_sha", "result"}
         and envelope["schema"] == "forge.f139.prompt-source-output.v1"
         and envelope["source_sha"] == parent_sha, "SOURCE_IDENTITY")
    result = envelope["result"]
    need(type(result) is dict and set(result) == {"schema", "lane", "frozen_sha256",
        "parent_sha256", "operations_used", "candidates", "scientific_accepted",
        "dispatch_authorized", "sealed_evaluation_consumed"}, "RESULT_FIELDS")
    parent = _sha(("FORGE-PROMPTLINEAGE-PARENT-V1\n"+lane+"\n"+parent_sha+"\n"+
                   frozen["parent"]).encode("ascii"))
    need(result["schema"] == "forge.promptlineage.advisory.v1" and result["lane"] == lane
         and result["frozen_sha256"] == frozen_sha256 and result["parent_sha256"] == parent
         and all(result[key] is False for key in (
             "scientific_accepted", "dispatch_authorized", "sealed_evaluation_consumed")),
         "RESULT_CONTRACT")
    entries = result["candidates"]
    need(type(entries) is list and len(entries) == len(frozen["operations"]) == len(bindings)
         and type(result["operations_used"]) is int and result["operations_used"] == len(entries),
         "COMPLETE_POPULATION_REQUIRED")
    by_prompt = {b.prompt: b.source for b in bindings}
    need(len(by_prompt) == len(bindings), "DUPLICATE_BINDING")
    outputs, seen = [], set()
    for index, (entry, op) in enumerate(zip(entries, frozen["operations"])):
        need(type(entry) is dict and set(entry) == {"parent_sha256", "candidate_sha256",
             "prompt", "operation", "classification"}, "CANDIDATE_FIELDS")
        # Validate the declared mutation. This is output validation of the
        # existing Go generator, not a replacement generation/search engine.
        words = frozen["parent"].split(" ")
        pos = op["position"]
        if op["kind"] == "replace":
            words[pos] = op["replacement"]
        else:
            words[pos], words[pos+1] = words[pos+1], words[pos]
        prompt = " ".join(words)
        child = _sha(("FORGE-PROMPTLINEAGE-CHILD-V1\n"+frozen_sha256+"\n"+parent+"\n"+
                      str(index)+"\n"+prompt).encode("ascii"))
        expected_op = dict(kind=op["kind"], position=pos)
        if op.get("replacement", ""):
            expected_op["replacement"] = op["replacement"]
        need(entry["prompt"] == prompt and prompt in by_prompt and prompt not in seen
             and entry["parent_sha256"] == parent and entry["candidate_sha256"] == child
             and entry["classification"] == "UNTESTED"
             and encoded(entry["operation"]) == encoded(expected_op),
             "OUTPUT_BINDING_MISMATCH")
        seen.add(prompt)
        outputs.append(by_prompt[prompt])
    receipts = validate_generation_batch(tuple(outputs), generator="promptbreeder",
        mechanism=mechanism, mechanism_sha256=mechanism_sha256, lane=lane, path=path,
        parent_sha=parent_sha, before=before, historical_sha256=historical_sha256,
        historical_ast_sha256=historical_ast_sha256)
    return PromptSourceBatch(receipts, result_sha256, frozen_sha256,
                             bindings_sha256, mechanism_sha256, parent_sha)
