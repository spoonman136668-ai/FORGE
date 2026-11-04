"""Actual Promptbreeder -> typed source, after the seven-source fixture.

Two generations retain every consumed source. No original owner, scientific
execution, publication, optimizer learning or dispatch is claimed here.
"""
import itertools
import json
from pathlib import Path
import sys

from f139.nci04_genenv_source import source_for_vector
from f139 import nci04_model_free_search as search
from f139.nci04_native_contract import canonical,digest
from f139.nci04_prompt_program import build_plan
from f139.nci04_prompt_source import compile_prompt_sources,frozen_digest


def fixture(previous=None):
    before = Path("f139/fixtures/model_free_yggdrasil_992ef.py").read_bytes()
    sources = tuple(source_for_vector(before,v)[0]
                    for v in itertools.product((0,1),repeat=3) if any(v))
    names = ("promptlineage/lineage.go", "cmd/f139-genenv-source/main.go",
        "f139/nci04_prompt_program.py", "f139/nci04_prompt_source.py",
        "f139/nci04_model_free_search.py", "f139/nci04_genenv_source.py",
        "f139/nci04_native_contract.py", "f139/nci04_portfolio_source_boundary.py")
    mechanism = b"".join(n.encode()+b"\0"+Path(n).read_bytes() for n in names)
    if previous is not None:
        # Recover a parent only from the complete validated first real output.
        first_before,first_sources,first_mechanism,first = fixture()
        batch = validate(previous,first_before,first_sources,first_mechanism,first)
        sources += (batch.candidates[0][0].after,)
    history = digest(b"F139-TYPED-PUBLIC-DEVELOPMENT-SOURCE-USE-FIXTURE\n"+
                     canonical([digest(source) for source in sources]))
    plan = build_plan(before,history_sources=sources,
        consumed_sha256={digest(x) for x in sources},
        historical_ast_sha256={search.normalized(x) for x in sources},
        history_sha256=history,mechanism_sha256=digest(mechanism))
    if plan is None:
        raise AssertionError("TYPED_SOURCE_NO_FRESH_PLAN_AFTER_EXHAUSTION")
    return before,sources,mechanism,plan


def validate(raw,before,sources,mechanism,plan):
    return compile_prompt_sources(raw,result_sha256=digest(raw),frozen=plan.frozen,
        frozen_sha256=frozen_digest(plan.frozen),bindings=plan.bindings,
        bindings_sha256=plan.source_bindings_sha256,mechanism=mechanism,
        mechanism_sha256=digest(mechanism),lane="Yggdrasil",path=search.PATH,
        parent_sha=search.PARENT,before=before,
        historical_sha256=frozenset(digest(x) for x in sources),
        historical_ast_sha256=frozenset(search.normalized(x) for x in sources))


def check(raw,previous=None):
    before,sources,mechanism,plan = fixture(previous)
    batch = validate(raw,before,sources,mechanism,plan)
    return dict(schema="forge.f139.typed-prompt-source-development.v1",
        generation=2 if previous is not None else 1,
        complete_consumed_source_count=len(sources),fresh_source_candidates=len(batch.candidates),
        source_after_sha256=[c.after_sha256 for c,_ in batch.candidates],
        generator_result_sha256=batch.generator_result_sha256,
        original_fixture_history_sha256=plan.history_sha256,
        frozen_sha256=batch.frozen_sha256,bindings_sha256=batch.bindings_sha256,
        mechanism_sha256=batch.mechanism_sha256,
        original_owner_demonstration=False,scientific_improvement_established=False,
        parent_selection_is_reward_learning=False,model_calls=0,publications=0,dispatches=0)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--request",action="store_true")
    action.add_argument("--result",type=Path)
    parser.add_argument("--previous",type=Path)
    args = parser.parse_args()
    previous = args.previous.read_bytes() if args.previous else None
    if args.request:
        print(json.dumps(fixture(previous)[3].request(),separators=(",",":")))
    else:
        print(json.dumps(check(args.result.read_bytes(),previous),sort_keys=True))
