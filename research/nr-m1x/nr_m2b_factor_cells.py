"""NR-M2B: optional online action-conditioned factor cells, SOURCE-ONLY.

Each public output bit infers its 3-of-8 input-bit parents from actual
selected before/action/after evidence. This is an engineering mechanism
prototype, NOT integration into Yggdrasil native research, proof of new
causal-world transfer, or a substitute for strong trained controls.
"""
from hashlib import sha256
import json
from nr_m1z_pinned_r7 import NonlinearLocalLearner, TRIPLES, index

SCHEMA = "forge.nr-m2b.cross-episode-factor-cells.source-only.v1"
R7_BLOB = "204ecd993b954b23e66d6d1e8b3568e7c93183c5"
CAP = 192
MAX_EVENTS = 4096
MAX_STEPS = 8
MAX_SNAPSHOT = 25000

def canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def sha(x):
    return sha256(x).hexdigest()
def valid_public(x):
    return type(x) is int and 0 <= x <= 255
def valid_action(x):
    return type(x) is int and 0 <= x <= 2

class PersistentFactorCells:
    """A bounded factorized learned predictive state with explicit custody."""
    def __init__(self, original_r7):
        if type(original_r7) is not NonlinearLocalLearner or not original_r7.models or original_r7.source:
            raise ValueError("NRM2B_ORIGINAL_R7_NOT_FROZEN")
        self.base_raw=original_r7.checkpoint()
        self.base_sha=sha(self.base_raw)
        self.rows={a:[] for a in range(3)}
        self.pending=None
        self.episodes=0
        self.events=0
        self.evictions=0
        self._cache={}

    def begin_episode(self):
        if self.pending is not None:
            raise ValueError("NRM2B_UNFINISHED_SELECTED_ACTION")
        self.episodes+=1
        # Retain ALL bounded past selected evidence across episodes.

    def commit(self, before, selected_action):
        if self.episodes < 1 or self.pending is not None:
            raise ValueError("NRM2B_SOURCE_ACTION_ORDER")
        if not valid_public(before) or not valid_action(selected_action):
            raise ValueError("NRM2B_INVALID_PUBLIC_ACTION")
        self.pending=(before,selected_action)

    def feedback(self, before, selected_action, observed_after):
        if not valid_public(before) or not valid_action(selected_action) or not valid_public(observed_after):
            raise ValueError("NRM2B_BAD_SOURCE_FEEDBACK")
        if self.pending != (before,selected_action):
            raise ValueError("NRM2B_UNMATCHED_OR_DUPLICATE_SOURCE_FEEDBACK")
        if self.events >= MAX_EVENTS:
            raise ValueError("NRM2B_TOTAL_SELECTED_EVENT_CAP")
        data=self.rows[selected_action]
        if len(data)==CAP:
            del data[0]
            self.evictions+=1
        data.append((before,observed_after))
        self.events+=1
        self.pending=None
        self._cache.pop(selected_action,None)

    def _infer_action(self,action):
        if action in self._cache:
            return self._cache[action]
        selected=self.rows[action]
        output=[]
        if len(selected)<16:
            self._cache[action]=None
            return None
        for out_bit in range(8):
            admissible=[]
            for parents in TRIPLES:
                counts=[0]*8
                positives=[0]*8
                for before,after in selected:
                    p=index(before,parents)
                    counts[p]+=1
                    positives[p]+=(after>>out_bit)&1
                if min(counts)<2:
                    continue
                errors=sum(min(k,n-k) for k,n in zip(positives,counts))
                table=[int(2*k >= n) for k,n in zip(positives,counts)]
                admissible.append((errors,parents,table))
            if len(admissible)<2:
                self._cache[action]=None
                return None
            admissible.sort(key=lambda z:(z[0],z[1]))
            best,runner=admissible[:2]
            if best[0]!=0 or runner[0]<2:
                self._cache[action]=None
                return None
            output.append((best[1],best[2]))
        self._cache[action]=tuple(output)
        return self._cache[action]

    def step(self, public_before, action):
        if not valid_public(public_before) or not valid_action(action):
            raise ValueError("NRM2B_INVALID_PREDICTION")
        model=self._infer_action(action)
        if model is None:
            return None,False
        result=0
        for bit,(parents,table) in enumerate(model):
            result |= table[index(public_before,parents)] << bit
        return result,True

    def forecast(self,public_before,actions):
        if not valid_public(public_before) or type(actions) not in (list,tuple) or not 1 <= len(actions) <= MAX_STEPS:
            raise ValueError("NRM2B_INVALID_COMPOSITION")
        state=public_before
        for action in actions:
            state,ok=self.step(state,action)
            if not ok:
                return None,False
        return state,True

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("NRM2B_PENDING_SOURCE_FEEDBACK")
        body={
            "schema":SCHEMA,"r7_source_blob":R7_BLOB,
            "base":json.loads(self.base_raw),"base_sha256":self.base_sha,
            "episodes":self.episodes,"events":self.events,
            "evictions":self.evictions,
            "rows":[[a,[[b,y] for b,y in self.rows[a]]] for a in range(3)],
        }
        data=canon({"body":body,"sha256":sha(canon(body))})
        if len(data)>MAX_SNAPSHOT:
            raise ValueError("NRM2B_SNAPSHOT_BUDGET")
        return data

    @classmethod
    def restore(cls,raw,trusted_base_sha,trusted_snapshot_sha):
        if (type(raw) is not bytes or len(raw)<1 or len(raw)>MAX_SNAPSHOT
            or type(trusted_snapshot_sha) is not str or sha(raw)!=trusted_snapshot_sha):
            raise ValueError("NRM2B_UNTRUSTED_SNAPSHOT")
        try:
            obj=json.loads(raw)
            if set(obj)!={"body","sha256"} or raw != canon(obj):
                raise ValueError("NRM2B_NONCANONICAL")
            body=obj["body"]
            if (set(body)!={"schema","r7_source_blob","base","base_sha256","episodes","events","evictions","rows"}
                or body["schema"]!=SCHEMA or body["r7_source_blob"]!=R7_BLOB
                or sha(canon(body))!=obj["sha256"]):
                raise ValueError("NRM2B_SCHEMA_INTEGRITY")
            original=canon(body["base"])
            if (type(trusted_base_sha) is not str or sha(original)!=trusted_base_sha
                or body["base_sha256"]!=trusted_base_sha):
                raise ValueError("NRM2B_BASE_IDENTITY")
            base=NonlinearLocalLearner.restore(original)
            state=cls(base)
            ep,ev,drop=body["episodes"],body["events"],body["evictions"]
            if not all(type(x) is int for x in (ep,ev,drop)) or not 0<=ep<=MAX_EVENTS or not 0<=drop<=ev<=MAX_EVENTS:
                raise ValueError("NRM2B_COUNTERS")
            rows=body["rows"]
            if type(rows) is not list or len(rows)!=3:
                raise ValueError("NRM2B_BAD_ACTION_ROWS")
            total=0
            for action,row in rows:
                if not valid_action(action) or action in state._cache or type(row) is not list or len(row)>CAP:
                    raise ValueError("NRM2B_BAD_ACTION_ROSTER")
                if action in state._cache:
                    raise ValueError("NRM2B_DUPLICATE_ACTION")
                state._cache[action]=True
                parsed=[]
                for sample in row:
                    if type(sample) is not list or len(sample)!=2 or not all(valid_public(z) for z in sample):
                        raise ValueError("NRM2B_INVALID_SELECTED_SAMPLE")
                    parsed.append(tuple(sample))
                state.rows[action]=parsed
                total+=len(parsed)
            if set(state._cache)!={0,1,2} or total+drop!=ev or (ep==0 and ev>0):
                raise ValueError("NRM2B_CUSTODY_COUNTERS")
            state._cache.clear()
            state.episodes=ep
            state.events=ev
            state.evictions=drop
            if state.checkpoint()!=raw:
                raise ValueError("NRM2B_COLD_IDENTITY_DRIFT")
            return state
        except (TypeError,KeyError,ValueError,OverflowError,UnicodeError) as e:
            raise ValueError("NRM2B_COLD_RESTORE_REJECTED") from e
