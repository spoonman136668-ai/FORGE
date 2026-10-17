"""F124-L fixture-only validation-binding of the ORIGINAL F124-H forward bytecode.

No source/model patch, model reimplementation, weight update, privileged
first-use, or protected-source constructor. Predictions are DEVELOPMENT
FIXTURES only. The isolated copy changes exactly original.source.validate
to the independently prequalified F124-K public-shape validator.
"""
from __future__ import annotations
import ast
import hashlib
import inspect
import json
from pathlib import Path
from types import FunctionType, SimpleNamespace

import f124h_signed_evidence as original
import f124h_source as original_source
import f124h_train_receipt as training
import f124k_extended_source as fixture

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f124l-fixture-only-model-interface-freeze.json"
FREEZE_BLOB="0280d0a669f68fb739833ec2f2e05a943b2124f1"
ORIGINAL_MODEL_BLOB="599d7a87f0812f3a7d2c8680861b6360d3640bc0"
ORIGINAL_SOURCE_BLOB="3feab91460f29ec169e1904479a134bb04691937"
FIXTURE_SOURCE_BLOB="b7c665e20c0fcff6655dba969a7e3de2c525ffab"
ORIGINAL_TRAIN_RECEIPT_SHA256="3ce0356ad9c19aeb4557ffe0b138908707c65ab3ce4b6af952adbf9899988254"
ORIGINAL_TRAIN_SOURCE_SHA="409f9129442f3d47b3d9bc032342f48042f3127a"
SCHEMA="forge.research.f124l.fixture-only-original-forward-equation-v1"

class Quarantined(ValueError): pass
def need(ok,code):
    if not ok:raise Quarantined("F124L_"+code)
def git_blob(module):
    raw=Path(module.__file__).read_bytes().replace(b"\r\n",b"\n")
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def canonical(x):return (json.dumps(x,sort_keys=True,separators=(",",":"))+"\n").encode()

def frozen():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    need(fixture.git_blob(raw)==FREEZE_BLOB,"FROZEN_PROTOCOL_MUTATION")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124l.frozen-validation-only-original-forward-adapter.v1"
         and p["stage"]=="PREIMPLEMENTATION_VALIDATION_ADAPTER_FREEZE"
         and p["parent"]["qualified_head"]=="404ace81943d20cf34be13a2f1b7a0d31fc5180e"
         and p["parent"]["original_f124h_model_git_blob"]==ORIGINAL_MODEL_BLOB
         and p["parent"]["original_f124h_source_git_blob"]==ORIGINAL_SOURCE_BLOB
         and p["parent"]["fixture_generator_git_blob"]==FIXTURE_SOURCE_BLOB
         and p["parent"]["original_train_receipt_sha256"]==ORIGINAL_TRAIN_RECEIPT_SHA256
         and p["mechanism"]["original_function_body_changed"] is False
         and p["mechanism"]["threshold"]==0.5
         and p["mechanism"]["training_epochs"]==0
         and p["scientific_boundary"]["protected_generated"]==0
         and p["scientific_boundary"]["independent_first_use"] is False
         and p["scientific_boundary"]["scientific_acceptance"] is False,
         "FROZEN_PROTOCOL_VIOLATION")
    need(git_blob(original)==ORIGINAL_MODEL_BLOB and
         git_blob(original_source)==ORIGINAL_SOURCE_BLOB and
         git_blob(fixture)==FIXTURE_SOURCE_BLOB and original.frozen(),
         "UPSTREAM_SOURCE_DRIFT")
    return p

def validation_only_clone(fn,global_name):
    """Clone unmodified code; replace exactly one *input validator binding*."""
    tree=ast.parse(inspect.getsource(fn))
    calls=[node.func for node in ast.walk(tree) if isinstance(node,ast.Call)]
    source_refs=[node for node in ast.walk(tree)
         if isinstance(node,ast.Attribute) and isinstance(node.value,ast.Name)
         and node.value.id==global_name]
    need(len(source_refs)==1 and source_refs[0].attr=="validate"
         and sum(isinstance(call,ast.Attribute) and
             isinstance(call.value,ast.Name) and call.value.id==global_name
             and call.attr=="validate" for call in calls)==1,
         "NOT_VALIDATION_ONLY_GLOBAL_REFERENCE")
    rebinding=dict(fn.__globals__)
    rebinding[global_name]=SimpleNamespace(validate=fixture.validate_public)
    clone=FunctionType(fn.__code__,rebinding,fn.__name__,fn.__defaults__,fn.__closure__)
    clone.__kwdefaults__=fn.__kwdefaults__
    need(clone.__code__ is fn.__code__ and
         fn.__globals__[global_name] is not rebinding[global_name],
         "ORIGINAL_CODE_OR_MODULE_MUTATED")
    return clone

def original_arm_b_adapter():
    frozen()
    return validation_only_clone(original.forward,"source")

def fixed_12of16_adapter():
    frozen()
    return validation_only_clone(training.fixed_comparator,"graph")

def fixture_pair(lane,seed,vector):
    need(lane in fixture.FIXTURES and type(seed) is int and
         seed in fixture.FIXTURES[lane] and
         vector in ([1,1,2],[3,2,0]),
         "FIXTURE_ONLY_OR_PROTECTED")
    return fixture.build_fixture(seed,list(vector),lane,"QUALIFICATION_FIXTURE")

def authenticate_train_receipt(raw):
    frozen()
    need(type(raw) is bytes and
         hashlib.sha256(raw).hexdigest()==ORIGINAL_TRAIN_RECEIPT_SHA256,
         "AUTHENTIC_TRAIN_RECEIPT_SHA")
    result=json.loads(raw)
    need(result["schema"]=="forge.research.f124h.train-only-signed-competing-evidence.v1"
         and result["source_sha"]==ORIGINAL_TRAIN_SOURCE_SHA
         and result["phase"]=="TRAIN_ONLY"
         and result["model_git_blob"]==ORIGINAL_MODEL_BLOB
         and result["source_git_blob"]==ORIGINAL_SOURCE_BLOB
         and result["protected_confirmation_cases_generated"]==0
         and result["independent_original_first_use"] is False
         and result["scientific_acceptances"]==0
         and len(result["lanes"])==2,
         "TRAIN_RECEIPT_AUTHORITY")
    weights={}
    for lane in result["lanes"]:
        name=lane["lane"]
        need(name in ("Wingless","Yggdrasil") and name not in weights
             and lane["arms"]["B"]["arm"]=="B"
             and lane["arms"]["B"]["phase"]=="TRAIN_ONLY"
             and lane["arms"]["B"]["epochs"]==100,
             "ORIGINAL_ARM_B_CUSTODY")
        arm=lane["arms"]["B"]
        w=arm["weights"]
        need(type(w) is list and len(w)==21 and original.sha(w)==arm["weight_sha256"],
             "FROZEN_WEIGHTS_IDENTITY")
        weights[name]=w
    need(set(weights)=={"Wingless","Yggdrasil"},"BOTH_LANES")
    return weights

def evaluate_fixture(lane,seed,vector,weights,forward=None,fixed=None):
    need(type(weights) is list and len(weights)==21
         and all(type(x) in (float,int) for x in weights),
         "ORIGINAL_B_WEIGHTS_ONLY")
    positive,negative=fixture_pair(lane,seed,vector)
    forward=forward or original_arm_b_adapter()
    fixed=fixed or fixed_12of16_adapter()
    results=[]
    for graph in (positive,negative):
        # Do not feed label, source seed, true path or paired counterpart into
        # the original forward function or original fixed comparator.
        try:
            p,logit,gradient,work=forward(graph,weights,"B")
            need(gradient is None,"NO_TRAINING_OR_GRADIENTS")
            b,control_work=fixed(graph)
            results.append({"failed":False,"probability":p,"logit":logit,
                "positive_prediction":p>=0.5,"fixed_12of16_prediction":bool(b),
                "work":work,"fixed_public_work":control_work})
        except (original_source.Invalid,OverflowError,ValueError) as e:
            results.append({"failed":True,"failure_type":type(e).__name__,
                "failure_code":str(e)[:160]})
    return results,{"positive_symbolic_routes":fixture.symbolic_routes(positive),
        "negative_symbolic_routes":fixture.symbolic_routes(negative),
        "positive_role_only_routes":fixture.symbolic_routes(positive,True)}
