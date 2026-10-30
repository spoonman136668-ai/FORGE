"""NR-M2E: full original-public, seven-action, mission-preserving transport.

Original source-authored MG19 and R18 ADMISSION FUNCTIONS are loaded unchanged
from exact pinned Git blobs, without importing unrelated native research models.
The original R10 transport handles its internal seven-action legacy projection.
This is not the original MG19 native model or Farama environment.
"""
import ast
import hashlib
import json
from pathlib import Path

from nr_m2d_pinned_original_public import (
    DoorKeyPublicAdapter, ACTION_NAMES, MISSION, public_observation,
    canonical, digest
)

R10_BLOB = "3917d36ce9f86a2c1b998a0a2f93fb27674a9205"
R18_BLOB = "531b4f258408eb38f38794f03a192aacdad42315"
MG19_BLOB = "3db67b40d8d59fdfb41f89185b65d2f16e1d8aab"
SCHEMA = "nr-m2e.original-mission-full-public-seven-action-transport.v1"
GOAL_MISSION = "get to the green goal square"
MAX_SNAPSHOT = 350000

def source_blob(name, expected):
    original=Path(__file__).with_name(name).read_bytes().replace(b"\r\n",b"\n")
    ident=hashlib.sha1(b"blob "+str(len(original)).encode()+b"\0"+original).hexdigest()
    if ident!=expected:
        raise ValueError("NRM2E_PINNED_ORIGINAL_SOURCE_CHANGED "+name)
    return original.decode("utf8")

def original_function(filename, expected_blob, name, globals_dict):
    # Execute ONLY the original unmodified, source-verified function AST.
    tree=ast.parse(source_blob(filename,expected_blob),filename=filename)
    matches=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==name]
    if len(matches)!=1:
        raise ValueError("NRM2E_ORIGINAL_FUNCTION_NOT_UNIQUE "+name)
    scope=dict(globals_dict)
    fragment=ast.fix_missing_locations(ast.Module(body=matches,type_ignores=[]))
    exec(compile(fragment,filename,"exec"),scope)
    return scope[name]

_r18_projected=original_function(
    "nr_m2e_pinned_r18_mission.py",R18_BLOB,"projected",
    {"MISSION":MISSION,"MISSIONS":(MISSION,GOAL_MISSION),
     "public_observation":public_observation})
_mg19_admitted=original_function(
    "nr_m2e_pinned_mg19_mission.py",MG19_BLOB,"admitted",
    {"LEGACY":(MISSION,GOAL_MISSION)})
_mg19_original_public=original_function(
    "nr_m2e_pinned_mg19_mission.py",MG19_BLOB,"original_public",
    {"admitted":_mg19_admitted,"MISSION":MISSION,
     "old_projected":_r18_projected})

def full_public(frame):
    """Preserve exact public mission, heading and all 147 pixel triplets."""
    _mg19_original_public(frame)
    projected=public_observation(dict(frame,mission=MISSION))
    return dict(projected,mission=frame["mission"])

def internal_legacy(frame):
    # Only ORIGINAL R10 internally sees DoorKey mission; source mission is
    # externally retained independently and never inferred from projection.
    return dict(full_public(frame),mission=MISSION)

class MissionSevenActionTransport:
    def __init__(self):
        self.inner=DoorKeyPublicAdapter()
        self.initial=None
        self.current=None
        self.pending=None
        self.events=0
        self.ledger=[]

    def begin_episode(self,frame):
        if self.pending is not None:
            raise ValueError("NRM2E_PENDING_BEFORE_RESET")
        public=full_public(frame)
        self.inner.reset_public(internal_legacy(public))
        self.initial=public
        self.current=public
        self.pending=None
        self.events=0
        self.ledger=[]

    def commit(self,before,selected_action):
        observed=full_public(before)
        if self.current is None or self.pending is not None or digest(observed)!=digest(self.current):
            raise ValueError("NRM2E_INCORRECT_SELECTED_PUBLIC_SOURCE")
        if type(selected_action) is not int or selected_action not in range(7):
            raise ValueError("NRM2E_NATIVE_ACTION_NOT_SUPPORTED")
        original_selected=self.inner.submit(selected_action)
        if original_selected!=selected_action:
            raise ValueError("NRM2E_ACTION_IDENTITY_REMAP")
        self.pending=(observed,selected_action)
        return selected_action

    def feedback(self,before,selected_action,returned_public,reward=0.0,terminated=False,truncated=False):
        observed=full_public(before)
        result=full_public(returned_public)
        if self.pending is None or self.current is None or type(selected_action) is not int:
            raise ValueError("NRM2E_FEEDBACK_WITHOUT_SELECTED_SOURCE")
        recorded,selected=self.pending
        if (selected!=selected_action or digest(observed)!=digest(recorded)
            or digest(observed)!=digest(self.current)):
            raise ValueError("NRM2E_MISMATCHED_PUBLIC_SELECTED_FEEDBACK")
        if observed["mission"]!=result["mission"]:
            raise ValueError("NRM2E_ORIGINAL_MISSION_DRIFT")
        # Inner source adapter validates reward, termination, source roster,
        # and selected sequence before mutating its immutable event history.
        inner_event=self.inner.complete(internal_legacy(result),reward,terminated,truncated)
        if inner_event["action"]!=selected:
            raise ValueError("NRM2E_INNER_SOURCE_ACTION_DRIFT")
        entry={"ordinal":self.events+1,"action":selected,"action_name":ACTION_NAMES[selected],
               "mission":observed["mission"],"full_before_sha256":digest(observed),
               "full_after_sha256":digest(result),"legacy_event":inner_event}
        self.current=result
        self.pending=None
        self.events+=1
        self.ledger=(self.ledger+[entry])[-64:]
        return entry

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("NRM2E_PENDING_SOURCE_CHECKPOINT")
        body={"schema":SCHEMA,"source_blobs":[R10_BLOB,R18_BLOB,MG19_BLOB],
              "inner":json.loads(self.inner.checkpoint()),"initial":self.initial,
              "current":self.current,"events":self.events,"ledger":self.ledger}
        raw=canonical({"body":body,"sha256":digest(body)})
        if len(raw)>MAX_SNAPSHOT:
            raise ValueError("NRM2E_FULL_PUBLIC_SOURCE_CHECKPOINT_CAP")
        return raw

    @classmethod
    def restore(cls,raw,trusted_sha):
        if (type(raw) is not bytes or len(raw)==0 or len(raw)>MAX_SNAPSHOT
            or type(trusted_sha) is not str
            or hashlib.sha256(raw).hexdigest()!=trusted_sha):
            raise ValueError("NRM2E_EXTERNAL_CHECKPOINT_CUSTODY")
        try:
            item=json.loads(raw)
            if set(item)!={"body","sha256"} or canonical(item)!=raw:
                raise ValueError("NRM2E_NONCANONICAL")
            body=item["body"]
            if (set(body)!={"schema","source_blobs","inner","initial","current","events","ledger"}
                or body["schema"]!=SCHEMA
                or body["source_blobs"]!=[R10_BLOB,R18_BLOB,MG19_BLOB]
                or digest(body)!=item["sha256"]):
                raise ValueError("NRM2E_WRONG_SOURCE_SCHEMA")
            original=DoorKeyPublicAdapter.restore(canonical(body["inner"]))
            if type(body["events"]) is not int or body["events"]!=original.events:
                raise ValueError("NRM2E_ORIGINAL_EVENT_COUNT_DRIFT")
            instance=cls()
            instance.inner=original
            instance.initial=full_public(body["initial"]) if body["initial"] is not None else None
            instance.current=full_public(body["current"]) if body["current"] is not None else None
            instance.events=body["events"]
            instance.ledger=body["ledger"]
            if (type(instance.ledger) is not list or len(instance.ledger)>64
                or (instance.current is None)!=(original.current is None)
                or (instance.current is not None
                    and (digest(internal_legacy(instance.current))!=digest(original.current)
                         or digest(internal_legacy(instance.initial))!=digest(original.initial)))
                or (instance.events>0 and (not instance.ledger or
                      instance.ledger[-1]["ordinal"]!=instance.events))):
                raise ValueError("NRM2E_SOURCE_IDENTITY_DRIFT")
            if instance.checkpoint()!=raw:
                raise ValueError("NRM2E_COLD_SOURCE_CHECKPOINT_MISMATCH")
            return instance
        except (TypeError,KeyError,ValueError,AttributeError,OverflowError,UnicodeError) as error:
            raise ValueError("NRM2E_UNTRUSTED_SOURCE_RESTORE") from error
