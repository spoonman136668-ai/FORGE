"""Development fixture: actual Go Promptbreeder -> independently bound source.

The sources reuse existing operators. They do NOT expand the live owner's
exhausted seven-source space; that replay is an explicit required negative.
"""
import itertools
import json
from pathlib import Path
import sys

from f139.nci04_genenv_source import source_for_vector
from f139.nci04_model_free_search import PARENT, PATH, candidates, normalized
from f139.nci04_portfolio_source_boundary import PortfolioSourceRejected, SourceCandidate, _sha
from f139.nci04_prompt_source import (
    SourceBinding, bindings_digest, compile_prompt_sources, frozen_digest,
)


def fixture():
    before = Path("f139/fixtures/model_free_yggdrasil_992ef.py").read_bytes()
    frozen = dict(schema="forge.promptlineage.frozen.v1", lane="Yggdrasil", epoch=1,
        source_sha=PARENT, parent="shrinkage standalone", vocabulary=["abstention", "recency"],
        max_operations=2, operations=[dict(kind="replace", position=1, replacement=x)
                                    for x in ("abstention", "recency")])
    names = ("promptlineage/lineage.go", "cmd/f139-genenv-source/main.go",
             "f139/nci04_prompt_source.py", "f139/nci04_genenv_source.py",
             "f139/nci04_model_free_search.py")
    mechanism = b"".join(n.encode()+b"\0"+Path(n).read_bytes() for n in names)
    bindings = []
    for prompt, vector in (("shrinkage abstention", (1,1,0)), ("shrinkage recency", (1,0,1))):
        after, operators = source_for_vector(before, vector)
        bindings.append(SourceBinding(prompt, SourceCandidate(
            generator="promptbreeder", lane="Yggdrasil", path=PATH, parent_sha=PARENT,
            before_sha256=_sha(before), after_sha256=_sha(after),
            mechanism_sha256=_sha(mechanism), after=after,
            question="Does composing "+", ".join(operators)+" improve public native decisions?",
            hypothesis="Existing explicit source recipes; retain all negative controls.")))
    return before, frozen, mechanism, tuple(bindings)


def request():
    _, frozen, _, _ = fixture()
    return dict(promptbreeder=dict(frozen=frozen, frozen_sha256=frozen_digest(frozen)))


def check(raw):
    before, frozen, mechanism, bindings = fixture()
    args = dict(result_sha256=_sha(raw), frozen=frozen, frozen_sha256=frozen_digest(frozen),
        bindings=bindings, bindings_sha256=bindings_digest(bindings), mechanism=mechanism,
        mechanism_sha256=_sha(mechanism), lane="Yggdrasil", path=PATH, parent_sha=PARENT,
        before=before)
    old = tuple(candidates(before))
    batch = compile_prompt_sources(raw, **args,
        historical_sha256=frozenset(_sha(x[1]) for x in old),
        historical_ast_sha256=frozenset(normalized(x[1]) for x in old))
    if len(batch.candidates) != 2:
        raise AssertionError("PROMPT_ACTUAL_POPULATION_MISSING")
    all_seven = tuple(source_for_vector(before, v)[0]
        for v in itertools.product((0,1), repeat=3) if any(v))
    try:
        compile_prompt_sources(raw, **args,
            historical_sha256=frozenset(_sha(x) for x in all_seven),
            historical_ast_sha256=frozenset(normalized(x) for x in all_seven))
    except PortfolioSourceRejected as exc:
        if str(exc) != "HISTORICAL_REPLAY":
            raise
    else:
        raise AssertionError("PROMPT_RELABELED_HISTORICAL_SOURCE")
    return dict(actual_promptbreeder_outputs=2, bound_source_candidates=2,
        complete_seven_consumed_replay_rejected=True,
        source_sha=PARENT, generator_result_sha256=batch.generator_result_sha256,
        frozen_sha256=batch.frozen_sha256, bindings_sha256=batch.bindings_sha256,
        mechanism_sha256=batch.mechanism_sha256,
        source_after_sha256=[c.after_sha256 for c, _ in batch.candidates],
        owner_demonstration=False, live_generation_space_expanded=False,
        model_calls=0, publications=0, dispatches=0)


if __name__ == "__main__":
    if sys.argv[1:] == ["--request"]:
        print(json.dumps(request(), separators=(",", ":")))
    elif len(sys.argv) == 3 and sys.argv[1] == "--result":
        print(json.dumps(check(Path(sys.argv[2]).read_bytes()), sort_keys=True))
    else:
        raise SystemExit("--request or --result PATH required")
