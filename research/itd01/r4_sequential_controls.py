"""ITD-01 R4: three actual independently fitted public sequential controls.

1. Elman 8-state recurrent controller trained on public demonstrator actions
   via BPTT, fully public features and behavior cloning.
2. Empirically trained forward-event delay/feedback model with an explicitly
   hand-designed exhaustive planning prior (NOT unconstrained world model).
3. Explicit public action-trajectory memory with case-based policy retrieval.

All agents accept PUBLIC observation-derived features/history only.
"""
import collections
import hashlib
import math
import random
from public_dev import canonical
from r4_public_experience import N_ACT,N_INPUT


def softmax(z):
    m=max(z);p=[math.exp(v-m) for v in z];s=sum(p)
    return [q/s for q in p]


class RecurrentPolicy:
    name="trained_bptt_recurrent"
    def __init__(self, seed, width=8):
        self.width=width
        r=random.Random(seed)
        self.wx=[[r.uniform(-.09,.09) for _ in range(N_INPUT)] for _ in range(width)]
        self.wh=[[r.uniform(-.07,.07) for _ in range(width)] for _ in range(width)]
        self.b=[0.]*width
        self.wo=[[r.uniform(-.08,.08) for _ in range(width)] for _ in range(N_ACT)]
        self.bo=[0.]*N_ACT
        self.updates=0

    def init_state(self):
        return [0.]*self.width

    def _advance(self,x,h):
        return [math.tanh(self.b[i]+sum(a*b for a,b in zip(self.wx[i],x))+
                          sum(a*b for a,b in zip(self.wh[i],h)))
                for i in range(self.width)]

    def _probs(self,h):
        return softmax([self.bo[k]+sum(w*v for w,v in zip(self.wo[k],h))
                        for k in range(N_ACT)])

    def choose(self,x,history,state):
        next_h=self._advance(x,state)
        p=self._probs(next_h)
        # No privileged truth is provided. Only the interface time budget
        # enforces necessary terminal completion.
        if history.latest_observation["interaction_budget_remaining"]==0:
            return 9,next_h
        return max(range(N_ACT),key=lambda k:(p[k],-k)),next_h

    def train(self,data,epochs=3,rate=.055):
        for epoch in range(epochs):
            for rows in data:
                hs=[[0.]*self.width];xs=[];ps=[]
                for row in rows:
                    x=row["x"];new=self._advance(x,hs[-1])
                    xs.append(x);hs.append(new);ps.append(self._probs(new))
                g_x=[[0.]*N_INPUT for _ in range(self.width)]
                g_h=[[0.]*self.width for _ in range(self.width)]
                g_b=[0.]*self.width
                g_o=[[0.]*self.width for _ in range(N_ACT)]
                g_bo=[0.]*N_ACT
                dh=[0.]*self.width
                for t in range(len(rows)-1,-1,-1):
                    y=rows[t]["y"];p=ps[t];h=hs[t+1]
                    dlog=[a-float(j==y) for j,a in enumerate(p)]
                    for j in range(N_ACT):
                        g_bo[j]+=dlog[j]
                        for v in range(self.width):
                            g_o[j][v]+=dlog[j]*h[v]
                    back=[dh[v]+sum(self.wo[j][v]*dlog[j] for j in range(N_ACT))
                          for v in range(self.width)]
                    dz=[max(-4.,min(4.,back[v]*(1-h[v]**2)))
                        for v in range(self.width)]
                    dh=[sum(self.wh[v][q]*dz[v] for v in range(self.width))
                        for q in range(self.width)]
                    for v in range(self.width):
                        g_b[v]+=dz[v]
                        for j in range(N_INPUT):
                            g_x[v][j]+=dz[v]*xs[t][j]
                        for j in range(self.width):
                            g_h[v][j]+=dz[v]*hs[t][j]
                # Exact sequence BPTT, per-trajectory gradient clipping.
                norm=math.sqrt(sum(u*u for row in g_x+g_h+g_o for u in row)+
                               sum(v*v for v in g_b+g_bo))
                scale=rate/max(1.,norm/8.)
                for v in range(self.width):
                    self.b[v]-=scale*g_b[v]
                    for j in range(N_INPUT):self.wx[v][j]-=scale*g_x[v][j]
                    for j in range(self.width):self.wh[v][j]-=scale*g_h[v][j]
                for j in range(N_ACT):
                    self.bo[j]-=scale*g_bo[j]
                    for v in range(self.width):self.wo[j][v]-=scale*g_o[j][v]
                self.updates+=1

    def serialize(self):
        return {"class":self.name,"width":self.width,"wx":self.wx,"wh":self.wh,
                "b":self.b,"wo":self.wo,"bo":self.bo,"updates":self.updates}


class PredictiveTransitionPlanner:
    """Learn delayed PUBLIC outcome statistics; script-only search planner.

    This is an *informed structured comparator*, not learned end-to-end planning
    or a discovered causal hypothesis class. The experiment must disclose
    its handcrafted action search and public event-type interpreter.
    """
    name="trained_public_transition_structured_planner"
    def __init__(self):
        self.delays={0:collections.Counter(),1:collections.Counter()}
        self.partial_counts=collections.Counter()
        self.delay_fit={0:2,1:3}
        self.updates=0

    def init_state(self):
        return {"phase":"start","candidate":0,"source":None,"target":None,
                "wait":0,"need_second":False,"family":None}

    def train(self,data):
        for rows in data:
            for row in rows:
                x=row["x"];family=int(x[22]>.5)
                if x[23]>.5 and sum(x[8:16])>.5:
                    lag=max(1,int(round(x[20]*4)))
                    self.delays[family][lag]+=1
                    if sum(x[12:16])>.5:self.partial_counts[family]+=1
                    self.updates+=1
        for family in (0,1):
            if self.delays[family]:
                self.delay_fit[family]=self.delays[family].most_common(1)[0][0]

    def choose(self,x,history,state):
        family=int(x[22]>.5)
        delay=self.delay_fit[family]
        phase=state["phase"]
        if phase=="start":
            state["candidate"]=0
            state["phase"]="wait_source"
            state["wait"]=0
            return 0,state
        if phase=="next_source":
            if state["candidate"]>=4:
                return 9,state
            state["phase"]="wait_source";state["wait"]=0
            return state["candidate"],state
        if phase in ("wait_source","wait_second","wait_target"):
            if state["wait"]<delay:
                state["wait"]+=1
                return 8,state
            if phase=="wait_target":
                state["phase"]="commit"
                return 9,state
            # Only public event fields, retained in history.
            if phase=="wait_source" and (history.public_ready or history.public_partial):
                target=history.public_ready or history.public_partial
                state["target"]=history.names.index(target)
                state["source"]=state["candidate"]
                if history.public_partial:
                    state["phase"]="wait_second";state["wait"]=0
                    return state["source"],state
                state["phase"]="wait_target";state["wait"]=0
                return state["target"],state
            if phase=="wait_second" and history.public_ready:
                state["phase"]="wait_target";state["wait"]=0
                return state["target"],state
            if phase=="wait_second":
                state["phase"]="commit"
                return 9,state
            state["phase"]="undo"
            return state["candidate"]+4,state
        if phase=="undo":
            state["candidate"]+=1
            state["phase"]="next_source"
            return self.choose(x,history,state)
        return 9,state

    def serialize(self):
        return {"class":self.name,"delay_fit":self.delay_fit,
                "observed_delay_counts":{str(k):dict(v) for k,v in self.delays.items()},
                "partial_counts":dict(self.partial_counts),"updates":self.updates}


class ExplicitTrajectoryMemory:
    """Public temporal case-memory trained on action-labeled histories."""
    name="trained_explicit_trajectory_memory"
    def __init__(self):
        self.counts={} # mapped public context -> voted next public action
        self.updates=0

    def init_state(self):
        return None

    def train(self,data):
        for rows in data:
            for row in rows:
                key=tuple(row["key"])
                # key is a tuple of tuples + ints + public value
                if key not in self.counts:self.counts[key]=[0]*N_ACT
                self.counts[key][row["y"]]+=1
                self.updates+=1

    def choose(self,x,history,state):
        key=history.memory_key()
        cases=self.counts.get(key)
        if cases is None:
            # Nearest public action and observed event memory case.
            best=None;best_cost=1e99
            for other,votes in self.counts.items():
                if other[-1]!=key[-1]:continue
                cost=sum(abs(a-b) for a,b in zip(key[0],other[0]))
                cost+=sum(abs(a-b) for a,b in zip(key[1],other[1]))
                cost+=abs(key[2]-other[2])*1.5
                cost+=2.0*(key[3]!=other[3])+2.0*(key[4]!=other[4])
                if cost<best_cost:
                    best_cost=cost;best=votes
            cases=best
        if cases is None:return 9,state
        if history.latest_observation["interaction_budget_remaining"]==0:
            return 9,state
        return max(range(N_ACT),key=lambda j:(cases[j],-j)),state

    def serialize(self):
        # Preserve all learned action votes, no training episode hidden labels.
        return {"class":self.name,"cases":[[list(k[0]),list(k[1]),k[2],k[3],k[4],
                k[5],votes] for k,votes in sorted(self.counts.items())],
                "updates":self.updates}


def model_sha(model):
    return hashlib.sha256(canonical(model.serialize())).hexdigest()


def model_bytes(model):
    return len(canonical(model.serialize()))
