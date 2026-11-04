#!/usr/bin/env python3
"""Run G98 original-model parity within the existing pinned G97 development setup.

Uses G97's original dataset, model staging, cohort, stream and runtime contract.
Only the first G97 arm is instrumented; remaining frozen G97 arms run normally.
This is diagnostic, not a repeatable performance acceptance.
"""
import hashlib,importlib.util,json,os
from pathlib import Path
from g98_original_parity import compare

HERE=Path(__file__).resolve().parent
def main():
    if os.environ.get("G98_DEVELOPMENT_ONLY")!="1":
        raise RuntimeError("G98_DEVELOPMENT_ONLY_GUARD")
    spec=importlib.util.spec_from_file_location("g98_pinned_g97",HERE/"g97_development_original.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original=module.run_g97
    executed=[False]
    def guarded(model,stream,prefixes,keys,torch,proc):
        if executed[0]:
            return original(model,stream,prefixes,keys,torch,proc)
        executed[0]=True
        reference,baseline=original(model,stream,prefixes,keys,torch,proc)
        g=module._g95()
        stream_path=Path("cpu_g97_development_stream.json")
        if not stream_path.exists():raise RuntimeError("G98_FROZEN_STREAM_MISSING")
        manifest=json.loads(stream_path.read_text())
        digest=hashlib.sha256(stream_path.read_bytes()).hexdigest()
        if manifest.get("schema") is None:
            raise RuntimeError("G98_FROZEN_MANIFEST_SCHEMA_MISSING")
        compare(model,stream,prefixes,keys,torch,proc,
                model_revision=g.MODEL_REV,weights_sha256=g.WEIGHTS_SHA,
                stream_sha256=digest,reference_outputs=reference,
                output_path="cpu_g98_original_parity_receipt.json")
        return reference,baseline
    module.run_g97=guarded
    module.main()
    if not executed[0]:raise RuntimeError("G98_COMPARISON_NOT_EXECUTED")
    result=json.loads(Path("cpu_g97_development_result.json").read_text())
    parity=json.loads(Path("cpu_g98_original_parity_receipt.json").read_text())
    if result["correctness"]!="PASS" or parity["parity"]!="PASS" or not parity["timing_accepted"]:
        raise RuntimeError("G98_PARITY_OR_ORIGINAL_CORRECTNESS_FAIL")
    print("G98_ORIGINAL_MODEL_DEVELOPMENT_PARITY=PASS; G97_DECISION=",result["decision"])

if __name__=="__main__":main()
