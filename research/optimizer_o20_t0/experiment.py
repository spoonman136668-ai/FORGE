#!/usr/bin/env python3
"""Prospectively frozen source-free bounded causal-query DEVELOPMENT. Not native/external."""
import json, math, random, time, hashlib, copy, statistics, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
T=24
FIT_N=240
DEV_N=96
COST=.1
FAMILY={
 'A':(-1.2,1.4,1.1,1.0),
 'B':(-.7,-1.2,1.3,1.4),
 'C':(-.9,1.0,-1.4,1.4),
 'D':(-.3,-1.1,-1.2,-.8),
}

def logistic(z):
    return 1/(1+math.exp(-max(-35,min(35,z))))

def features(x,prior_action,prior_observed):
    return (1.,float(x),float(prior_action==1),float(prior_observed) if prior_observed is not None else 0.,float(prior_observed is None))

def key(x,prior_action,prior_observed):
    return (int(x),int(prior_action==1), 2 if prior_observed is None else int(prior_observed))

class PublicSource:
    def __init__(self,family,seed):
        self.coeffs=FAMILY[family]
        self.public_random=random.Random(seed*97+13)
        self.hazard_random=random.Random(seed*109+59)
        self.hidden_previous_hazard=0
        self.previous_action=0
        self.n=0
    def public_context(self):
        return self.public_random.randrange(2)
    def sample_current_hazard(self,x):
        if self.n >= T:raise ValueError('EPISODE_OVER')
        b,c,a,h=self.coeffs
        probability=logistic(b+c*x+a*(self.previous_action==1)+h*self.hidden_previous_hazard)
        hazard=int(self.hazard_random.random()<probability)
        return hazard,probability
    def finish(self,hazard,action):
        if action not in (0,1):raise ValueError('ILLEGAL_MOTOR')
        reward=0 if action==0 else (-3 if hazard else 1)
        self.hidden_previous_hazard=int(hazard)
        self.previous_action=int(action)
        self.n+=1
        return reward

class FittedLogit:
    def __init__(self):
        self.w=[0.]*5
    def fit(self,rows):
        # Fixed 12 epochs, source-free FIT ONLY. Same global learner used in both arms.
        for epoch in range(12):
            for feat,y in rows:
                prob=logistic(sum(a*b for a,b in zip(self.w,feat)))
                self.w=[max(-8.,min(8.,w+.012*((y-prob)*f-.0005*w))) for w,f in zip(self.w,feat)]
    def predict(self,x,prior_action,prior_observed):
        v=features(x,prior_action,prior_observed)
        return logistic(sum(a*b for a,b in zip(self.w,v)))
    def reset_episode(self): pass
    def feedback(self,x,prior_action,prior_observed,label,prediction):pass
    def state(self):return {'kind':'FITTED_CONVENTIONAL_LOGISTIC','weights':self.w}

class FastSlow(FittedLogit):
    def __init__(self):
        super().__init__()
        self.bias=0.;self.local_feedback=0
    def reset_episode(self):
        self.bias=0.;self.local_feedback=0
    def predict(self,x,prior_action,prior_observed):
        v=features(x,prior_action,prior_observed)
        return logistic(sum(a*b for a,b in zip(self.w,v))+self.bias)
    def feedback(self,x,prior_action,prior_observed,label,prediction):
        # Trial-specific public actual source event changes only ephemeral inference state.
        self.bias=.8*self.bias+(.35*(label-prediction) if label is not None else 0.)
        if label is not None:self.local_feedback+=1
    def state(self):return {'kind':'ACTION_CONDITIONED_LOCAL_FAST_SLOW','weights':self.w,'inference_bias':self.bias,'local_feedback':self.local_feedback}

class ConditionalBeta:
    def __init__(self):self.count={};self.ep={}
    def fit(self,rows):
        for feat,y in rows:
            # features exactly store the same x,prev-action,prev-observed as explicit training inputs
            k=(int(feat[1]),int(feat[2]),2 if feat[4] else int(feat[3]))
            pair=self.count.setdefault(k,[0,0]);pair[y]+=1
    def reset_episode(self):self.ep={}
    def predict(self,x,prior_action,prior_observed):
        k=key(x,prior_action,prior_observed)
        a,b=self.count.get(k,(0,0));c,d=self.ep.get(k,(0,0))
        return (b+d+1)/(a+b+c+d+2)
    def feedback(self,x,prior_action,prior_observed,label,prediction):
        if label is not None:
            a=self.ep.setdefault(key(x,prior_action,prior_observed),[0,0]);a[label]+=1
    def state(self):return {'kind':'FULL_CONDITIONAL_BAYES_BETA','fit':sorted((str(k),v) for k,v in self.count.items()),'inference':sorted((str(k),v) for k,v in self.ep.items())}

class ContextLaplace:
    def __init__(self):self.count={0:[0,0],1:[0,0]};self.ep={0:[0,0],1:[0,0]}
    def fit(self,rows):
        for feat,y in rows:self.count[int(feat[1])][y]+=1
    def reset_episode(self):self.ep={0:[0,0],1:[0,0]}
    def predict(self,x,prior_action,prior_observed):
        a,b=self.count[x];c,d=self.ep[x]
        return (b+d+1)/(a+b+c+d+2)
    def feedback(self,x,prior_action,prior_observed,label,prediction):
        if label is not None:self.ep[x][label]+=1
    def state(self):return {'kind':'CONTEXT_LAPLACE','fit':self.count,'inference':self.ep}

class StaticPrior:
    def fit(self,rows):pass
    def reset_episode(self):pass
    def predict(self,x,prior_action,prior_observed):return .5
    def feedback(self,x,prior_action,prior_observed,label,prediction):pass
    def state(self):return {'kind':'PUBLIC_NO_LEARNING_PRIOR','prior':.5}

class PrivilegedTrueFormula(StaticPrior):
    def predict_oracle(self,risk):return risk
    def state(self):return {'kind':'PRIVILEGED_TRUE_WORLD_LAW_UPPER_CONTROL'}

MODELS={'LOCAL_FAST_SLOW':FastSlow,'BAYES_BETA':ConditionalBeta,'CONVENTIONAL_LOGIT':FittedLogit,'CONTEXT_LAPLACE':ContextLaplace,'PERIODIC_BETA':ConditionalBeta,'PRIOR_50':StaticPrior,'PRIVILEGED_LAW':PrivilegedTrueFormula}

def build_fit():
    rows=[];receipt=[]
    for fam,base in (('A',100000),('B',200000)):
        for i in range(FIT_N):
            seed=base+i;env=PublicSource(fam,seed)
            prev_action=0;prev_observed=None
            for t in range(T):
                x=env.public_context()
                true_h,truth_p=env.sample_current_hazard(x)
                scan=t in (2,7,12,17)
                # Deterministic exploration; exact 4 true scanner reads per episode.
                action=int((t+seed)%3!=0)
                reward=env.finish(true_h,action)
                observed=true_h if scan or action==1 else None
                if observed is not None:rows.append((features(x,prev_action,prev_observed),observed))
                receipt.append((fam,seed,t,x,prev_action,prev_observed,int(scan),action,reward,observed))
                prev_action=action;prev_observed=observed
    return rows,receipt

def scan_policy(risk,t,query_count,mode):
    if mode=='PERIODIC_BETA':return t in (2,7,12,17)
    if query_count>=4:return False
    block=t//6
    if query_count>block:return False
    if t%6==5:return True
    # Fixed VOI threshold and deterministic behavior. No dev tuning.
    voi=(1-risk)-max(0,1-4*risk)-COST
    return voi>=.42

def execute_one(family,seed,name,fitted_model):
    m=copy.deepcopy(fitted_model);m.reset_episode()
    env=PublicSource(family,seed)
    prev_action=0;prev_observed=None
    bought=0;collisions=0;total=0.;data=[];inference_ns=0
    for t in range(T):
        x=env.public_context()
        true_h,source_risk=env.sample_current_hazard(x)
        start=time.process_time_ns()
        risk=source_risk if name=='PRIVILEGED_LAW' else m.predict(x,prev_action,prev_observed)
        if not 0<=risk<=1:raise ValueError('RISK_INVALID')
        scan=scan_policy(risk,t,bought,name)
        if scan:bought+=1
        observed_before_action=true_h if scan else None
        action=int(not observed_before_action) if scan else int(risk<.25)
        inference_ns+=time.process_time_ns()-start
        reward=env.finish(true_h,action)
        if action==1 and true_h:collisions+=1
        total+=reward-(COST if scan else 0.)
        observation=true_h if scan or action==1 else None
        m.feedback(x,prev_action,prev_observed,observation,risk)
        data.append((t,x,prev_action,prev_observed,round(risk,7),int(scan),action,round(reward,7),observation))
        prev_action=action;prev_observed=observation
    if bought!=4:raise ValueError('ACTUAL_INFORMATION_BUDGET_DRIFT_'+name+':'+str(bought))
    return {'reward':total,'collisions':collisions,'queries':bought,'inference_ns':inference_ns,'source_actions':T,'trace_sha256':hashlib.sha256(json.dumps(data,separators=(',',':')).encode()).hexdigest(),'memory_bytes':len(json.dumps(m.state(),sort_keys=True,separators=(',',':')).encode())}

def run():
    started=time.process_time_ns()
    rows,training_trace=build_fit()
    models={}
    for name,cls in MODELS.items():
        o=cls();o.fit(rows);models[name]=o
    rows_hash=hashlib.sha256(json.dumps(training_trace,separators=(',',':')).encode()).hexdigest()
    result={'schema':'optimizer.itd02.o20-t0.sourcefree.trainonly.v1','protocol_SHA256':hashlib.sha256((HERE/'PREREG.md').read_bytes()).hexdigest(),
            'source_original_external':False,'original_ENV_reset_step_count':0,'original_source_roles_consumed':0,'native_original_Yggdrasil':False,
            'fit_episodes_total':2*FIT_N,'fit_recorded_public_labeled_samples':len(rows),'fit_stream_sha256':rows_hash,
            'query_allocation_exactly_four':True,'families':{},'model_global_parameter_bytes':{},'full_process_CPU_seconds':None}
    for name,m in models.items():result['model_global_parameter_bytes'][name]=len(json.dumps(m.state(),sort_keys=True,separators=(',',':')).encode())
    for fam,base in (('C',300000),('D',400000)):
        tab={}
        for name in MODELS:
            episodes=[execute_one(fam,base+i,name,models[name]) for i in range(DEV_N)]
            tab[name]={'mean_net_reward_per_step':round(sum(e['reward'] for e in episodes)/(DEV_N*T),7),
                       'total_collisions':sum(e['collisions'] for e in episodes),
                       'total_queries':sum(e['queries'] for e in episodes),
                       'total_source_actions':sum(e['source_actions'] for e in episodes),
                       'mean_inference_CPU_ns_per_step':round(sum(e['inference_ns'] for e in episodes)/(DEV_N*T)),
                       'max_checkpoint_bytes':max(e['memory_bytes'] for e in episodes),
                       'traces_digest':hashlib.sha256(''.join(e['trace_sha256'] for e in episodes).encode()).hexdigest()}
        best=max(tab[m]['mean_net_reward_per_step'] for m in ('BAYES_BETA','CONVENTIONAL_LOGIT','CONTEXT_LAPLACE','PERIODIC_BETA'))
        native=tab['LOCAL_FAST_SLOW']['mean_net_reward_per_step']
        tab['gate']={'better_than_best_fully_trained_conventional_by_at_least_0.1':native>=best+.1,
                     'match_all_actual_purchased_queries':len({tab[k]['total_queries'] for k in MODELS})==1,
                     'candidate_vs_best_conventional':round(native-best,7)}
        result['families'][fam]=tab
    result['go']=all(result['families'][fam]['gate']['better_than_best_fully_trained_conventional_by_at_least_0.1'] for fam in ('C','D'))
    result['disposition']='O20_T0_SOURCE_FREE_CANDIDATE_NOT_ORIGINAL' if result['go'] else 'O20_T0_SOURCE_FREE_NATIVE_ADVANTAGE_NO_GO'
    result['full_process_CPU_seconds']=round((time.process_time_ns()-started)/1e9,5)
    return result

if __name__=='__main__':
    x=run();(HERE/'RESULT.json').write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'disposition':x['disposition'],'fit_labeled':x['fit_recorded_public_labeled_samples'],
                      'families':{fam:{name:{k:v for k,v in data.items() if k in ('mean_net_reward_per_step','total_queries','total_collisions')} for name,data in f.items() if name in MODELS} for fam,f in x['families'].items()}},sort_keys=True,indent=2))
