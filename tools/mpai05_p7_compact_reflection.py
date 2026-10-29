"""P7 compact reflection policy, a new *development* cohort with a same-run P6 memory-only control.

Inherits exact successful P6 read-only source, frozen eight exposed tasks, model
hash, resource limits and scoring. The only arm change is the reflection
instruction length. A PASS here is neither first-use nor scientific admission.
"""
import contextlib
import io
import json
import os
from pathlib import Path

from tools import mpai05_p6_fourarm_dev as base

P6_INSTRUCTION = "Apply the reflected output-cap mitigation hypothesis: cite only the exact requested figure or a direct negative answer, in one concise sentence; never invent proof of accuracy."
COMPACT_INSTRUCTION = "Copy exact figures. Answer briefly. Never claim accuracy was independently proven."

def main():
    assert base.INSTRUCTIONS["memory_reflection"] == P6_INSTRUCTION, "MPAI05_P7_ORIGINAL_POLICY_DRIFT"
    assert len(COMPACT_INSTRUCTION) < len(P6_INSTRUCTION), "MPAI05_P7_POLICY_NOT_SHORTER"
    assert len(base.CASES)==8 and len(base.ARMS)==4, "MPAI05_P7_FROZEN_CASE_DRIFT"
    assert base.MODEL_SHA=="2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2", "MPAI05_P7_MODEL_DRIFT"
    assert base.SOURCE=="fd9d1d5cec917063a0a9d2d263affe7f0cce3f12", "MPAI05_P7_SOURCE_DRIFT"
    base.INSTRUCTIONS["memory_reflection"] = COMPACT_INSTRUCTION
    path=Path(os.environ["MPAI05_P6_SCRATCH"])
    with contextlib.redirect_stdout(io.StringIO()):
        base.main()
    data=json.loads((path/"private-development-receipts.json").read_text(encoding="utf-8"))
    result=data["audit"]
    records=data["receipt"]["trials"]
    assert len(records)==32 and len({(x["task_id"],x["arm"]) for x in records})==32, "MPAI05_P7_TRIAL_COUNT"
    assert result["classification"]=="DEVELOPMENT_ONLY_SELF_REPORTED", "MPAI05_P7_CLASSIFICATION"
    assert result["scientific_accepted"] is False and result["accepted_ice_writes"]==0, "MPAI05_P7_PRIVILEGE"
    assert result["development_candidate_budget_eligible"] is False, "MPAI05_P7_GATE_AUTHORITY"
    arms=result["arms"]
    b=arms["memory_only"];c=arms["memory_reflection"]
    correct=int(c["correct"])>int(b["correct"])
    no_task_regression=result["no_memory_only_task_regression"]
    costs=int(c["tokens"])<=int(b["tokens"]) and int(c["latency_ms"])<=int(b["latency_ms"])
    no_claims=int(c["hard_false_claims"])==0
    cap=int(c["cap_hits"])<=int(b["cap_hits"])
    metrics=bool(correct and no_task_regression and costs and no_claims and cap)
    # This P7 paired memory-policy decision is distinct from P4's full
    # four-arm comparison against a no-memory-sized placebo. Neither test
    # grants experiment or scientific qualification authority.
    print("MPAI05_P7_MODEL_CALLS=32")
    print("MPAI05_P7_MODEL_HASH_VERIFIED=PASS")
    print("MPAI05_P7_REAL_PRIVATE_MCP=PASS")
    print("MPAI05_P7_REFLECTION=PROPOSE_ONLY")
    print("MPAI05_P7_OLD_POLICY_CHARS="+str(len(P6_INSTRUCTION)))
    print("MPAI05_P7_COMPACT_POLICY_CHARS="+str(len(COMPACT_INSTRUCTION)))
    for arm in base.ARMS:
        for key in ("correct","tokens","latency_ms","hard_false_claims","cap_hits"):
            print("MPAI05_P7_"+arm.upper()+"_"+key.upper()+"="+str(arms[arm][key]))
    print("MPAI05_P7_POLICY_CANDIDATE_METRICS_PASS_UNVERIFIED="+str(metrics).upper())
    print("MPAI05_P7_BUDGET_ELIGIBLE=FALSE")
    print("MPAI05_P7_INDEPENDENT_GRADING=FALSE")
    print("MPAI05_P7_FIRST_USE=FALSE")
    print("MPAI05_P7_SCIENTIFIC_ACCEPTANCE=FALSE")
    print("MPAI05_P7_PRODUCTION_WRITES=0")

if __name__=="__main__":
    main()
