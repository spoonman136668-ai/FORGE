#!/usr/bin/env python3
"""R8 original-world harness: fail-closed source and cohort preflight.

No MiniGrid reset or step occurs during preflight. Execution requires a
separate complete comparator implementation and qualified source runner.
"""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "itd02_r8_frozen_original_minigrid_01.json"
F5 = HERE / "k4t_f5_frozen_r6_edges.json"
R8 = "9061b256b9d68e4d83b3a10e51fb8b7ef365259f"
R5 = "978825064dd6076058a1a38ae1a9a3d80e28d99e"
MINIGRID = "7f5853792ea7f04f75614661006d87fcf949f26d"
CONTROLS = {
    "unchanged original Wingless R5",
    "independent equal-information conditional Beta posterior (expected R8 tie)",
    "independent six-field fitted conventional planner",
    "stronger full-public-map conventional planner where observation access is equalized",
    "R8 previous-action conditioning ablated",
}
def seeds(cohort):
    assert set(cohort) == {"start", "count"}
    assert type(cohort["start"]) is int and type(cohort["count"]) is int
    assert cohort["count"] > 0
    return set(range(cohort["start"], cohort["start"] + cohort["count"]))

def preflight():
    raw = FROZEN.read_bytes()
    p = json.loads(raw)
    assert p["protocol_id"] == "ITD02-R8-ORIGINAL-MINIGRID-01"
    assert p["status"] == "FROZEN_BEFORE_FIRST_ORIGINAL_WORLD_R8_RUN"
    assert p["source_pins"]["wingless_r8_commit"] == R8
    assert p["source_pins"]["wingless_r5_commit"] == R5
    assert p["source_pins"]["minigrid_commit"] == MINIGRID
    assert set(p["comparators"]) == CONTROLS
    assert p["worlds"] == ["MiniGrid-Empty-8x8-v0", "MiniGrid-FourRooms-v0"]
    cohorts = p["cohorts"]
    fit, check, dev = (seeds(cohorts[k]) for k in ("fit_seeds", "check_seeds", "development_seeds"))
    assert len(fit) == 24 and len(check) == 8 and len(dev) == 8
    assert not (fit & check or fit & dev or check & dev)
    historical = json.loads(F5.read_text())["cohorts"]
    for key in ("FIT", "CHECK", "DEV"):
        old = historical[key]
        assert type(old) is list and len(old) == 2
        assert not (fit | check | dev) & set(range(old[0], old[1] + 1))
    assert p["execution"].startswith("NOT_AUTHORIZED_BY_THIS_FILE")
    return {"result": "SOURCE_ONLY_PREFLIGHT_PASS",
            "protocol_sha256": hashlib.sha256(raw).hexdigest(),
            "fresh_seed_counts": {"FIT":len(fit),"CHECK":len(check),"DEV":len(dev)},
            "comparators_registered": len(CONTROLS),
            "original_world_resets":0,"original_world_steps":0,
            "scientific_first_use":False,"scientific_accepted":False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=preflight()
    text=json.dumps(result,sort_keys=True,indent=2)+"\n"
    if args.output:
        if args.output.exists():raise ValueError("REFUSE_OVERWRITE")
        args.output.write_text(text)
    print(text,end="")
if __name__=="__main__":
    main()
