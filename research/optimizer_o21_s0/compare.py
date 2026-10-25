"""O21-S0 strictly source-only independent conventional equivalence of native Ygg R7.

Never execute external environment; pinned native learner used unchanged.
All source-only effects come from public original R7 test formula, not external physics.
"""
import hashlib
import importlib.util
import itertools
import json
import random
import time
from pathlib import Path

ORIGINAL_HEAD = "a509c23d8b0d0a11d3d5d38eaa70656c7ab07ddd"
ORIGINAL_BLOB = "204ecd993b954b23e66d6d1e8b3568e7c93183c5"
ORIGINAL_TEST_BLOB = "bec25db3632c8978f884f1e0a4c41fc78fa8e9f9"
SOURCE_LEARNER = Path("research/native/itd02/r7/learner.py")
SOURCE_TEST = Path("research/native/itd02/r7/test_learner.py")
DIAG_WORLDS = (7301, 7302)
ROWS_PER_ACTION = 192
ALL_PUBLIC_STATES = range(256)
ACTIONS = (0, 1, 2)
CHAINS = ((0,1,2),(2,0,0,1,2))
SCHEMA = "optimizer.itd02.o21-s0.public-original-r7-structural-equivalence.v1"


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_original(root):
    root=Path(root)
    model_file=root / SOURCE_LEARNER
    tests_file=root / SOURCE_TEST
    if git_blob(model_file.read_bytes()) != ORIGINAL_BLOB:
        raise ValueError("O21_NATIVE_ORIGINAL_LEARNER_IDENTITY_MISMATCH")
    if git_blob(tests_file.read_bytes()) != ORIGINAL_TEST_BLOB:
        raise ValueError("O21_NATIVE_ORIGINAL_TEST_IDENTITY_MISMATCH")
    spec=importlib.util.spec_from_file_location("o21_pinned_native_r7",model_file)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def source_only_public_effect(seed,action,state):
    """Exact public math in pinned original Ygg test_learner.py (AUDITOR ONLY)."""
    out=0
    for bit in range(8):
        p=(bit+action)%8
        q=(bit+action+2)%8
        r=(bit+action+5)%8
        value=(((state>>p)&1)&((state>>q)&1)) ^ ((state>>r)&1) ^ ((seed+bit+action)&1)
        out|=value<<bit
    return out


def independent_index(x,parents):
    idx=0
    for j,p in enumerate(parents):
        idx+=((x>>p)&1)*(1<<j)
    return idx


def frozen_json(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


class ConventionalExhaustiveTriple:
    """Independent equally-informed 3-parent fully trained categorical estimator."""
    def __init__(self):
        self.raw={}
        self.models={}
        self.events=0

    def observe(self,world,action,before,after):
        if not (isinstance(world,str) and action in ACTIONS and
                type(before) is int and 0<=before<256 and
                type(after) is int and 0<=after<256):
            raise ValueError("O21_BAD_PUBLIC_OBSERVATION")
        d=self.raw.setdefault(world,{0:{},1:{},2:{}})[action]
        if before in d:raise ValueError("O21_DUPLICATE")
        d[before]=after
        self.events+=1

    def fit(self):
        for world,by_action in sorted(self.raw.items()):
            self.models[world]={}
            for action in ACTIONS:
                pairs=sorted(by_action[action].items())
                if len(pairs)!=ROWS_PER_ACTION:
                    raise ValueError("O21_INCOMPLETE_EQUAL_INFORMATION")
                out_models=[]
                for outbit in range(8):
                    best=None
                    for parents in itertools.combinations(range(8),3):
                        frequency=[[0,0] for _ in range(8)]
                        for state,effect in pairs:
                            bucket=independent_index(state,parents)
                            frequency[bucket][(effect>>outbit)&1]+=1
                        mistakes=sum(min(zero,one) for zero,one in frequency)
                        # Ordered combinations and strictly-less comparison independently
                        # implement lexicographic tie break, as a conventional rule.
                        if best is None or mistakes<best[0]:
                            majority=[int(one*2 >= zero+one) if zero+one else 0
                                      for zero,one in frequency]
                            best=(mistakes,parents,majority)
                    out_models.append({"parents":list(best[1]),
                                       "table":best[2],"fit_errors":best[0]})
                self.models[world][str(action)]=out_models
        self.raw={}

    def step(self,world,action,state):
        bits=self.models[world][str(action)]
        result=0
        for j,m in enumerate(bits):
            result|=m["table"][independent_index(state,m["parents"])]<<j
        return result

    def predict(self,world,start,actions):
        v=start
        for action in actions:v=self.step(world,action,v)
        return v


def audit(root):
    native_mod=load_original(root)
    original=native_mod.NonlinearLocalLearner()
    independent=ConventionalExhaustiveTriple()
    public_records=[]
    for seed in DIAG_WORLDS:
        for state in random.Random(seed).sample(range(256),ROWS_PER_ACTION):
            for action in ACTIONS:
                after=source_only_public_effect(seed,action,state)
                key=str(seed)
                original.observe(key,action,state,after)
                independent.observe(key,action,state,after)
                public_records.append((key,action,state,after))
    assert original.events==independent.events==1152
    train_digest=hashlib.sha256(frozen_json(public_records)).hexdigest()
    t0=time.process_time_ns()
    original.fit()
    t1=time.process_time_ns()
    independent.fit()
    t2=time.process_time_ns()
    native_serial=frozen_json(original.models)
    classic_serial=frozen_json(independent.models)
    if native_serial!=classic_serial:
        raise AssertionError("O21_MODELS_DISAGREE_WITH_EQUAL_PUBLIC_FIT")
    original_checkpoint=original.checkpoint()
    restored=native_mod.NonlinearLocalLearner.restore(original_checkpoint)
    assert frozen_json(restored.models)==native_serial
    direct_equal=0
    direct_true_native=0
    direct_true_control=0
    for seed in DIAG_WORLDS:
        for action in ACTIONS:
            for state in ALL_PUBLIC_STATES:
                world=str(seed)
                truth=source_only_public_effect(seed,action,state)
                n=original.step(world,action,state)
                c=independent.step(world,action,state)
                if n!=c:raise AssertionError("O21_PREDICTION_DISAGREE")
                direct_equal+=1
                direct_true_native+=int(n==truth)
                direct_true_control+=int(c==truth)
    chain_equal=0
    chain_truth_native=0
    for seed in DIAG_WORLDS:
        for state in tuple(range(16)):
            for actions in CHAINS:
                world=str(seed)
                actual=state
                for action in actions:actual=source_only_public_effect(seed,action,actual)
                n=original.predict(world,state,actions)
                c=independent.predict(world,state,actions)
                if n!=c:raise AssertionError("O21_COMPOSED_PREDICTION_DISAGREE")
                chain_equal+=1
                chain_truth_native+=int(n==actual)
    # Source-only same-target tie stress test. Never original new environment.
    native_tie=native_mod.NonlinearLocalLearner()
    ctrl_tie=ConventionalExhaustiveTriple()
    for state in random.Random(7319).sample(range(256),192):
        for action in ACTIONS:
            native_tie.observe("zero",action,state,0)
            ctrl_tie.observe("zero",action,state,0)
    native_tie.fit()
    ctrl_tie.fit()
    if frozen_json(native_tie.models)!=frozen_json(ctrl_tie.models):
        raise AssertionError("O21_TIE_RULE_DRIFT")
    if not all(p["parents"]==[0,1,2] and p["fit_errors"]==0
               for entries in native_tie.models["zero"].values() for p in entries):
        raise AssertionError("O21_FIRST_PARENT_TIE_RULE")
    report={
        "schema":SCHEMA,
        "scientific_first_use":False,
        "science_go":False,
        "original_external_environment_steps":0,
        "original_protected_cohorts_consumed":0,
        "native_source_head":ORIGINAL_HEAD,
        "native_source_blob":ORIGINAL_BLOB,
        "native_test_blob":ORIGINAL_TEST_BLOB,
        "diagnostic_worlds":list(DIAG_WORLDS),
        "public_training_rows":len(public_records),
        "public_training_rows_sha256":train_digest,
        "direct_matched_predictions":direct_equal,
        "direct_correct_native":direct_true_native,
        "direct_correct_conventional":direct_true_control,
        "composed_matched_predictions":chain_equal,
        "composed_correct_native":chain_truth_native,
        "model_canonical_bytes":len(native_serial),
        "equal_model_sha256":hashlib.sha256(native_serial).hexdigest(),
        "native_integrity_framed_checkpoint_bytes":len(original_checkpoint),
        "zero_effect_tie_stress":True,
        "native_fit_process_CPU_ns":t1-t0,
        "conventional_fit_process_CPU_ns":t2-t1,
        "cost_warning":"One-process Python-only fit CPU values, not complete cost or architectural Pareto evidence",
        "disposition":"O21_S0_NATIVE_EXHAUSTIVE_CONVENTIONAL_STRUCTURAL_EQUIVALENCE_NO_NOVELTY",
    }
    return report


if __name__=="__main__":
    import sys
    if len(sys.argv)!=2:raise SystemExit("Usage: compare.py <pinned Yggdrasil root>")
    print(json.dumps(audit(sys.argv[1]),sort_keys=True,indent=2))
