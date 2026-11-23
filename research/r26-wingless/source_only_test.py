import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
def load(name):
    s=importlib.util.spec_from_file_location(name,HERE/(name+".py"))
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_source_only():
    execute=load("execute")
    reviewer=load("review")
    raw=(HERE/"prereg.json").read_bytes()
    assert execute.PREREG_GIT_BLOB==reviewer.FROZEN_BLOB
    assert reviewer.FROZEN_BLOB=="ba54fa51807e7135b598ac2cefbe09984f162da6"
    assert execute.EXPERIMENT==reviewer.EXPERIMENT
    m=json.loads(raw)
    assert len(m["development_blocks"])==3
    assert len(set(sum(m["development_blocks"],[])+m["sealed_heldout_seeds"]))==96
    assert m["decision_rule"]["precedence"]==[
        "FAMILY_DIVERSITY_ROBUST iff all three blocks strict",
        "else PARTIAL_FAMILY_GAIN iff at least partial_cohorts_min blocks partial",
        "else NO_CONFIRMED_DIVERSITY_GAIN"]
    for damaged in (b"{}",b'{"science_production_accepted":true}',
                    b'{"x":1,"x":2}',b'not-json'):
        try:reviewer.verify(raw,damaged)
        except (ValueError,KeyError,TypeError,AttributeError):pass
        else:raise AssertionError("non-science raw passed independent reviewer")
    print("R26_FROZEN_SOURCE_ONLY_NEGATIVES=PASS")
    print("R26_ORIGINAL_EXECUTED=FALSE")
if __name__=="__main__":test_source_only()
