import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def module(name):
    spec=importlib.util.spec_from_file_location("r28_"+name,ROOT/(name+".py"))
    x=importlib.util.module_from_spec(spec);spec.loader.exec_module(x)
    return x

def test():
    execute=module("execute");review=module("review")
    m=json.loads((ROOT/"prereg.json").read_text())
    assert execute.PREREG_BLOB==review.BLOB=="0f51aedd38a726347780990027129c6881736b5d"
    assert execute.ID==review.EXPERIMENT==m["experiment_id"]
    assert m["parent_r26_run_id"]==38480506640
    assert len(set(sum(m["development_blocks"],[])+m["sealed_heldout_seeds"]))==96
    for payload in (b"{}",b'{"schema":"forge.r28.source-robust-original.v1"}',
                    b'{"x":1,"x":2}',b'null'):
        try:review.verify((ROOT/"prereg.json").read_bytes(),payload)
        except (ValueError,KeyError,TypeError,AttributeError):pass
        else:raise AssertionError("R28 reviewer accepted unauthenticated raw")
    print("R28_PRE_FIRST_USE_SOURCE_NEGATIVES=PASS")
    print("R28_ORIGINAL_EXECUTED=FALSE")
if __name__=="__main__":test()
