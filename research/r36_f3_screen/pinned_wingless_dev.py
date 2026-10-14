"""Source-pinned Wingless development adapter (no scientific original).

Loads the exact immutable Wingless method-source commit and constructs only
R36 preregistered development training examples. Does NOT score, select,
claim first use, or inspect reserved sealed cohorts.
"""
import importlib.util
import json
import pathlib
import subprocess
import sys

SOURCE_COMMIT = "b1e4972f04142f1f35f76f9483b12491dec4846c"
SOURCE_PATH = "research/contrib/chatgpt/20261013-w-r52-batch-diversity/execute.py"
PORTFOLIO_BLOB = "4140cf897c05d27dd6dac01cea796f383fa2ef44"

def _git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],stderr=subprocess.DEVNULL).decode().strip()

def load_training(wingless_checkout, portfolio, block_index):
    from wingless_methods import SOURCES, ROWS_PER_SOURCE
    root=pathlib.Path(wingless_checkout).resolve(strict=True)
    if _git(root,"rev-parse","HEAD") != SOURCE_COMMIT:
        raise ValueError("R36_WING_SOURCE_COMMIT_DRIFT")
    if _git(root,"status","--porcelain"):
        raise ValueError("R36_WING_DIRTY_SOURCE")
    if _git(root,"ls-files","--error-unmatch",SOURCE_PATH) != SOURCE_PATH:
        raise ValueError("R36_WING_SOURCE_PATH_DRIFT")
    if not isinstance(block_index,int) or isinstance(block_index,bool) or block_index not in (0,1,2):
        raise ValueError("R36_INVALID_DEVELOPMENT_BLOCK")
    if portfolio.get("schema") != "forge.r36-f3.pre-execution-hypothesis-portfolio.v1":
        raise ValueError("R36_PORTFOLIO_DRIFT")
    w=portfolio["wingless"]
    if w.get("method_source_commit") != SOURCE_COMMIT:
        raise ValueError("R36_METHOD_IDENTITY_DRIFT")
    blocks=w["development_blocks"]
    if len(blocks)!=3 or any(len(x)!=16 for x in blocks):
        raise ValueError("R36_DEVELOPMENT_SHAPE")
    selected=blocks[block_index]
    sealed=set(w["reserved_sealed_heldout_seeds"])
    if len(set(sum(blocks,[]))) != 48 or sealed.intersection(sum(blocks,[])):
        raise ValueError("R36_DEV_SEALED_COLLISION")
    path=root/SOURCE_PATH
    spec=importlib.util.spec_from_file_location("r36_pinned_w52",path)
    if spec is None or spec.loader is None:
        raise ValueError("R36_PINNED_WORKER_UNAVAILABLE")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from pathlib import Path
    # Reuse already qualified example construction; no evaluator or heldout.
    import importlib.util as ilu
    adapter=pathlib.Path(__file__).resolve().parents[1]/"r34-wingless"/"execute.py"
    spec2=ilu.spec_from_file_location("r36_frozen_family_constructor",adapter)
    if spec2 is None or spec2.loader is None:
        raise ValueError("R36_TRAINING_ADAPTER_MISSING")
    m2=ilu.module_from_spec(spec2)
    spec2.loader.exec_module(m2)
    by_source=m2.families(module,selected)
    if len(by_source)!=SOURCES or any(len(rows)!=ROWS_PER_SOURCE for rows in by_source.values()):
        raise ValueError("R36_TRAINING_BUDGET_DRIFT")
    return tuple(tuple(rows) for rows in by_source.values())
