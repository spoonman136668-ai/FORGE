import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def load(name):
    spec=importlib.util.spec_from_file_location("r29_"+name,ROOT/(name+".py"))
    x=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(x)
    return x

def test():
    ex=load("execute");rv=load("review")
    raw=(ROOT/"prereg.json").read_bytes()
    m=json.loads(raw)
    assert ex.PREREG_BLOB==rv.BLOB=="66d6908b1cc37a7aa819d1cc5a1c122d8c1ca444"
    assert ex.ID==rv.EXPERIMENT==m["experiment_id"]
    assert m["parent_run_id"]==38484042414
    seeds=sum(m["development_blocks"],[])+m["sealed_heldout_seeds"]
    assert len(seeds)==96 and len(set(seeds))==96
    assert m["limits"]["model_calls"]==0 and m["first_use"]["launch_authorized"] is False
    assert m["training_examples_per_arm"]==1728 and m["training_epochs"]==32
    for payload in (b"{}",b"null",b'{"x":1,"x":2}',b'{"classification":"ROBUST_SMOOTH_GAIN"}'):
        try:rv.verify(raw,payload)
        except (ValueError,KeyError,TypeError,AttributeError):pass
        else:raise AssertionError("R29 reviewer accepted unverified raw")
    assert ex.smooth_fit.__code__.co_names.count("evaluate")==0
    print("R29_FROZEN_SOURCE_NEGATIVE_ENFORCEMENT=PASS")
    print("R29_SCIENTIFIC_ORIGINAL_EXECUTED=FALSE")
if __name__=="__main__":
    test()
