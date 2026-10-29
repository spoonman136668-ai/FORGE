"""MG29 exact frozen MG28 proposal proxy, source-only; no off-policy results.

The native Go and Python implement the same basis-point threshold/scan:
prior own selected original source events in mission+heading+front context;
count >=3, Laplace change >= .75 and >= .10 better than inherited action.
This proxy never executes candidate action or claims the native model chose it.
"""
from collections import defaultdict

def observed_context(p):
    if type(p) is not dict or set(p)!={"image","direction","mission"}:
        raise ValueError("MG29_NOT_SOURCE_PUBLIC")
    if type(p["mission"]) is not str or type(p["direction"]) is not int or p["direction"] not in range(4):
        raise ValueError("MG29_UNTRUSTED_MISSION_OR_HEADING")
    pic=p["image"]
    if type(pic) is not list or len(pic)!=7 or any(
        type(row) is not list or len(row)!=7 or any(
            type(v) is not list or len(v)!=3 or any(type(n)is not int or not 0<=n<=255 for n in v)
            for v in row) for row in pic):
        raise ValueError("MG29_UNTRUSTED_ORIGINAL_IMAGE")
    return (p["mission"],p["direction"],tuple(pic[3][5]))

class Prefix:
    def __init__(self):
        self.full=defaultdict(lambda:[{"n":0,"changed":0,"target":0,"door":0} for _ in range(7)])
        self.action=[{"n":0,"changed":0,"target":0,"door":0} for _ in range(7)]
        self.events=0
        self.task_relevant_events=0

    @staticmethod
    def score(stat):
        return 10000*(stat["changed"]+1)//(stat["n"]+2)

    @classmethod
    def proposal(cls,row,original):
        if type(original)is not int or original not in range(7) or len(row)!=7:
            raise ValueError("MG29_ORIGINAL_ACTION_INVALID")
        baseline=cls.score(row[original])
        best=None;high=0
        for action,item in enumerate(row):
            if item["n"]<3:
                continue
            score=cls.score(item)
            if score>=7500 and score>=baseline+1000 and score>high:
                best=action;high=score
        return (best if best is not None and best!=original else None)

    def before(self,before,original):
        key=observed_context(before)
        full=self.proposal(self.full[key],original)
        simple=self.proposal(self.action,original)
        evidence=self.full[key][full] if full is not None else None
        return {"full_proposal":full,"action_only_proposal":simple,
                "full_support":evidence["n"] if evidence else 0,
                "full_prior_task_effects":(evidence["target"]+evidence["door"]) if evidence else 0,
                "full_selected_score_bp":self.score(evidence) if evidence else None,
                "original_score_bp":self.score(self.full[key][original]),
                "action_only_score_bp":self.score(self.action[original])}

    def after(self,before,action,changed,target,door):
        if type(action)is not int or action not in range(7):
            raise ValueError("MG29_NOT_ORIGINAL_SELECTED_ACTION")
        if any(type(x)is not bool for x in (changed,target,door)):
            raise ValueError("MG29_NOT_SOURCE_OBSERVED_EFFECT")
        if (target or door) and not changed:
            raise ValueError("MG29_EFFECT_WITHOUT_SOURCE_PUBLIC_CHANGE")
        key=observed_context(before)
        for stat in (self.full[key][action],self.action[action]):
            stat["n"]+=1
            stat["changed"]+=int(changed)
            stat["target"]+=int(target)
            stat["door"]+=int(door)
        self.events+=1
        self.task_relevant_events+=int(target or door)
