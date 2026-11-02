"""Compile explicit GenEnv operator vectors; no optimizer, dispatch or inference.

This is a bounded compiler for the existing Yggdrasil source operators, not a
claim that arbitrary environment vectors or policy scores are source edits.
Caller pins must come from the separately authenticated generator invocation.
"""
import json
from dataclasses import dataclass

from f139.nci04_model_free_search import (
    OPERATORS, PARENT, PATH, candidates,
)
from f139.nci04_portfolio_source_boundary import (
    PortfolioSourceRejected, SourceCandidate, _sha, validate_generation_batch,
)


@dataclass(frozen=True)
class CompiledBatch:
    candidates: tuple
    generator_result_sha256: str
    frozen_sha256: str
    history_sha256: str
    mechanism_sha256: str
    source_sha: str


def source_for_vector(before, vector):
    """One compiler implementation shared by history projection and output checks."""
    if (type(vector) not in (list, tuple) or len(vector) != len(OPERATORS) or
            any(type(x) is not int or x not in (0, 1) for x in vector) or not any(vector)):
        raise PortfolioSourceRejected("GENENV_SOURCE_RECIPE")
    tuple(candidates(before))
    source = before.decode("utf-8")
    names = []
    for enabled, (name, anchor, replacement, _, _) in zip(vector, OPERATORS):
        if enabled:
            if source.count(anchor) != 1:
                raise PortfolioSourceRejected("GENENV_OPERATOR_ANCHOR_DRIFT")
            source = source.replace(anchor, replacement, 1)
            names.append(name)
    return source.encode("utf-8"), names


def compile_operator_vectors(raw, *, result_sha256, frozen_sha256,
                             history_sha256, mechanism, mechanism_sha256,
                             before, historical_sha256, historical_ast_sha256):
    if type(raw) is not bytes or len(raw) > 256_000 or _sha(raw) != result_sha256:
        raise PortfolioSourceRejected("GENENV_RESULT_DRIFT")
    envelope = json.loads(raw)
    if (type(envelope) is not dict or
            envelope.get("schema") != "forge.f139.genenv-source-output.v1" or
            envelope.get("source_sha") != PARENT or type(envelope.get("result")) is not dict):
        raise PortfolioSourceRejected("GENENV_SOURCE_IDENTITY")
    result = envelope["result"]
    if (result.get("schema") != "forge.genenvironment.advisory.v1" or
            result.get("lane") != "Yggdrasil" or
            result.get("frozen_sha256") != frozen_sha256 or
            result.get("history_sha256") != history_sha256 or
            any(result.get(key) is not False for key in (
                "scientific_accepted", "dispatch_authorized", "sealed_holdout_consumed"))):
        raise PortfolioSourceRejected("GENENV_RESULT_CONTRACT")
    for pin in (frozen_sha256, history_sha256):
        if type(pin) is not str or len(pin) != 64 or any(c not in "0123456789abcdef" for c in pin):
            raise PortfolioSourceRejected("GENENV_PIN")
    # Reuse the existing immutable source guard and operator anchors.
    tuple(candidates(before))
    entries = result.get("candidates")
    if type(entries) is not list or not 1 <= len(entries) <= 16:
        raise PortfolioSourceRejected("GENENV_BATCH_BOUND")
    outputs = []
    for entry in entries:
        vector = entry.get("vector")
        if (entry.get("classification") != "UNTESTED_PROPOSAL" or
                type(vector) is not list or len(vector) != len(OPERATORS) or
                any(type(x) is not int or x not in (0, 1) for x in vector) or not any(vector)):
            raise PortfolioSourceRejected("GENENV_SOURCE_RECIPE")
        after, names = source_for_vector(before, vector)
        outputs.append(SourceCandidate(
            generator="dgm_genenv", lane="Yggdrasil", path=PATH, parent_sha=PARENT,
            before_sha256=_sha(before), after_sha256=_sha(after),
            mechanism_sha256=mechanism_sha256,
            question="Does composing " + ", ".join(names) + " improve public native decisions?",
            hypothesis="The existing operators may interact; retain standalone-parent, coverage, "
                       "stationary-retention and unfamiliar-transfer negative controls.", after=after))
    validated = validate_generation_batch(
        tuple(outputs), generator="dgm_genenv", mechanism=mechanism,
        mechanism_sha256=mechanism_sha256, lane="Yggdrasil", path=PATH,
        parent_sha=PARENT, before=before, historical_sha256=historical_sha256,
        historical_ast_sha256=historical_ast_sha256)
    return CompiledBatch(validated, result_sha256, frozen_sha256,
                         history_sha256, mechanism_sha256, PARENT)
