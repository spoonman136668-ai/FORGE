"""K4X-O2: deterministic handwritten, capacity-matched temporal-credit falsifier.

STRICT DEVELOPMENT FIXTURE: no original environments, no FIT/CHECK/DEV, no permits.
This tests model mechanisms, not scientific performance.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
import math

ACTIONS = (0, 1, 2)
FEATURE_COUNT = 9
PARAMETERS = FEATURE_COUNT * len(ACTIONS)
ALPHA = 0.2
GAMMA = 0.9
LAM_TRACE = 0.8
PROGRESS_WEIGHT = 0.15

@dataclass(frozen=True)
class PublicGrid:
    x: int
    y: int
    goal_x: int
    goal_y: int
    direction: int
    front_blocked: bool
    def __post_init__(self):
        if (any(type(x) is not int or not (0 <= x <= 64) for x in
                (self.x, self.y, self.goal_x, self.goal_y)) or
            type(self.direction) is not int or self.direction not in range(4) or
            type(self.front_blocked) is not bool):
            raise ValueError('NON_PUBLIC_OR_INVALID_GRID')

PUBLIC_KEYS = frozenset({'X', 'Y', 'GoalX', 'GoalY', 'Direction', 'FrontBlocked'})

def public_from(raw: dict) -> PublicGrid:
    if type(raw) is not dict or raw.keys() != PUBLIC_KEYS:
        raise ValueError('ONLY_SIX_PUBLIC_FIELDS')
    return PublicGrid(*(raw[k] for k in ('X','Y','GoalX','GoalY','Direction','FrontBlocked')))

def features(st: PublicGrid) -> tuple[float, ...]:
    if type(st) is not PublicGrid:
        raise ValueError('PUBLIC_GRID_REQUIRED')
    dx, dy = st.goal_x-st.x, st.goal_y-st.y
    values = (1., max(-1.,min(1.,dx/16)), max(-1.,min(1.,dy/16)),
              max(0.,min(1.,(abs(dx)+abs(dy))/32)))
    values += tuple(float(st.direction==i) for i in range(4))
    return values+(float(st.front_blocked),)

def taxi(st: PublicGrid) -> int:
    return abs(st.goal_x-st.x)+abs(st.goal_y-st.y)

@dataclass(frozen=True)
class Event:
    before: PublicGrid
    action: int
    after: PublicGrid
    reward: float
    terminated: bool
    truncated: bool
    def __post_init__(self):
        if (type(self.before) is not PublicGrid or type(self.after) is not PublicGrid or
            type(self.action) is not int or self.action not in ACTIONS or
            type(self.reward) not in (int,float) or not math.isfinite(self.reward) or
            type(self.terminated) is not bool or type(self.truncated) is not bool or
            (self.terminated and self.truncated) or
            (self.before.goal_x,self.before.goal_y)!=(self.after.goal_x,self.after.goal_y)):
            raise ValueError('INVALID_ACTION_OR_FEEDBACK')
    @property
    def shaped(self) -> float:
        return float(self.reward)+PROGRESS_WEIGHT*(taxi(self.before)-taxi(self.after))

def validate_sequence(ep: tuple[Event,...]) -> None:
    # PRE-validate whole episode to prevent mutating a model before a late error.
    if (type(ep) is not tuple or not ep or
        not (ep[-1].terminated or ep[-1].truncated)):
        raise ValueError('COMPLETE_EPISODE_REQUIRED')
    for t,event in enumerate(ep):
        if type(event) is not Event or (t and ep[t-1].after!=event.before):
            raise ValueError('PUBLIC_SEQUENCE_DISCONTINUITY')
        if t < len(ep)-1 and (event.terminated or event.truncated):
            raise ValueError('EARLY_TERMINAL_THEN_MORE_EVENTS')

class LinearTD:
    """Same 27 trainable params, features, experiences, alpha, gamma and targets.

    TD(0) versus accumulating eligibility TD(lambda) differ only in trace.
    Lambda method carries an extra 27 transient values and costs extra updates.
    """
    def __init__(self, lam: float):
        if type(lam) is not float or lam not in (0.,LAM_TRACE):
            raise ValueError('FROZEN_LAMBDA_REQUIRED')
        self.lam=lam
        self.weights=[0.]*PARAMETERS
        self.events_seen=0
        self.scalar_weight_updates=0
    def score(self, st: PublicGrid, action: int) -> float:
        if type(action) is not int or action not in ACTIONS:
            raise ValueError('ACTION_OUTSIDE_THREE_LEGAL_VALUES')
        z=features(st)
        return sum(self.weights[action*FEATURE_COUNT+i]*v for i,v in enumerate(z))
    def choose(self, st: PublicGrid) -> int:
        return max(ACTIONS,key=lambda a:(self.score(st,a),-a))
    def train(self, ep:tuple[Event,...]):
        validate_sequence(ep)
        trace=[0.]*PARAMETERS
        for event in ep:
            current=self.score(event.before,event.action)
            continuation=0. if event.terminated else GAMMA*max(self.score(event.after,a) for a in ACTIONS)
            error=event.shaped+continuation-current
            for k in range(PARAMETERS): trace[k]*=GAMMA*self.lam
            for i,value in enumerate(features(event.before)):
                trace[event.action*FEATURE_COUNT+i]+=value
            for k,value in enumerate(trace):
                if value != 0.:
                    self.weights[k]+=ALPHA*error*value
                    self.scalar_weight_updates+=1
            self.events_seen+=1
        return self
    def snapshot(self) -> bytes:
        payload={'schema':'optimizer.k4x-o2.matched-linear-td.v1',
                 'lambda':self.lam,'weights':self.weights,
                 'events_seen':self.events_seen,
                 'scalar_weight_updates':self.scalar_weight_updates}
        raw=json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        return json.dumps({'payload':payload,'sha256':sha256(raw).hexdigest()},
                          sort_keys=True,separators=(',',':')).encode()
    @classmethod
    def restore(cls, blob:bytes):
        if type(blob) is not bytes or not (0 < len(blob) < 16384):
            raise ValueError('CHECKPOINT_INVALID_LENGTH')
        try:
            wire=json.loads(blob)
            if type(wire) is not dict or set(wire)!={'payload','sha256'}:
                raise ValueError('CHECKPOINT_FORMAT')
            p=wire['payload']
            raw=json.dumps(p,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
            if sha256(raw).hexdigest()!=wire['sha256']:
                raise ValueError('CHECKPOINT_TAMPERED')
            if (set(p)!={'schema','lambda','weights','events_seen','scalar_weight_updates'} or
                p['schema']!='optimizer.k4x-o2.matched-linear-td.v1' or
                type(p['lambda']) is not float or p['lambda'] not in (0.,LAM_TRACE) or
                type(p['weights']) is not list or len(p['weights'])!=PARAMETERS or
                not all(type(v) in (float,int) and math.isfinite(v) for v in p['weights']) or
                any(type(p[k]) is not int or p[k]<0 for k in ('events_seen','scalar_weight_updates'))):
                raise ValueError('CHECKPOINT_SCHEMA_OR_VALUES')
            result=cls(p['lambda'])
            result.weights=[float(x) for x in p['weights']]
            result.events_seen=p['events_seen']
            result.scalar_weight_updates=p['scalar_weight_updates']
            return result
        except (TypeError,KeyError,OverflowError) as e:
            raise ValueError('CHECKPOINT_CORRUPT') from e

def handwritten_matched_pair():
    """Not a real MiniGrid route. Two counterfactual action trajectories.

    Both start with IDENTICAL six public fields; one turns right toward a goal,
    one turns left away from it. An original-environment simulator is NEVER used.
    """
    s0=PublicGrid(3,3,5,3,3,True)
    right1=PublicGrid(3,3,5,3,0,False)
    right2=PublicGrid(4,3,5,3,0,False)
    right3=PublicGrid(5,3,5,3,0,False)
    left1=PublicGrid(3,3,5,3,2,False)
    left2=PublicGrid(2,3,5,3,2,False)
    left3=PublicGrid(1,3,5,3,2,False)
    success=(Event(s0,1,right1,0.,False,False),
             Event(right1,2,right2,0.,False,False),
             Event(right2,2,right3,1.,True,False))
    failure=(Event(s0,0,left1,0.,False,False),
             Event(left1,2,left2,0.,False,False),
             Event(left2,2,left3,0.,False,True))
    return failure,success

def ablate_terminal_reward(ep):
    e=ep[-1]
    return ep[:-1]+(Event(e.before,e.action,e.after,0.,e.terminated,e.truncated),)

def preflight():
    fail,success=handwritten_matched_pair()
    td=LinearTD(0.)
    trace=LinearTD(LAM_TRACE)
    trace_no_terminal=LinearTD(LAM_TRACE)
    for ep in (fail,success):
        td.train(ep)
        trace.train(ep)
        trace_no_terminal.train(ablate_terminal_reward(ep))
    start=success[0].before
    return {'status':'HANDWRITTEN_CAPACITY_MATCHED_ONLY',
            'native_original_episodes':0,'reserved_fit_check_dev_roles':0,
            'scientific_fsa_permit':False,
            'same_public_state_for_both_actions':fail[0].before==success[0].before,
            'matched_trainable_parameters_each':PARAMETERS,
            'matched_training_events_each':td.events_seen,
            'td0_first_action':td.choose(start),
            'td_lambda_first_action':trace.choose(start),
            'trace_terminal_reward_ablation_first_right_value':trace_no_terminal.score(start,1),
            'trace_actual_first_right_value':trace.score(start,1),
            'learned_weight_update_counts':{'td0':td.scalar_weight_updates,'trace':trace.scalar_weight_updates},
            'transient_trace_entries':PARAMETERS,
            'checkpoint_bytes':{'td0':len(td.snapshot()),'trace':len(trace.snapshot())},
            'checkpoint_sha256':{'td0':sha256(td.snapshot()).hexdigest(),'trace':sha256(trace.snapshot()).hexdigest()}}
if __name__=='__main__':
    print(json.dumps(preflight(),indent=2,sort_keys=True,allow_nan=False))
