"""Q21 pure evaluation API; no standalone runner or source generation.

CKB-plane-controlled qualification must independently admit inputs and run this
function; importing this module performs no FIT, DEV, held or original work.
"""
from __future__ import annotations
import hashlib
import json
import math
import time
import tracemalloc

import sourcefree as p
import models as m

ARM_NAMES = ('FULL_CURRENT_COUNTS', 'TRAINED_CURRENT_LOGISTIC',
             'LAGGED_PUBLIC_COUNTS', 'TRAINED_2_STATE_ACTION_RNN',
             'TRAINED_4_STATE_ACTION_RNN', 'UNSUPERVISED_2_STATE_ACTION_HMM',
             'UNSUPERVISED_4_STATE_ACTION_HMM')
MEMORYLESS = ARM_NAMES[:2]
HISTORY = ARM_NAMES[2:]


def digest_public(rows):
    payload=json.dumps(p.public_rows(rows),sort_keys=True,separators=(',',':'))
    return hashlib.sha256(payload.encode()).hexdigest()


def check_role_bound_rows(by_role, family):
    """Reject extras, private fields, unexpected families and role-size drift."""
    p.require(type(by_role) is dict and set(by_role)==set(p.ROLES), 'ROLE_SET_DRIFT')
    out={}
    for role in ('FIT_TRAIN','FIT_VALID','DEV'):
        rows=p.public_rows(by_role[role])
        p.require(len(rows)==p.ROLE_COUNTS[role], 'ROLE_EPISODE_COUNT_DRIFT')
        p.require(all(r[0]==family and len(r[1])==33 and len(r[2])==32 for r in rows),
                  'FAMILY_OR_EPISODE_LENGTH_DRIFT')
        out[role]=rows
    hashes={role:digest_public(rows) for role,rows in out.items()}
    p.require(len(set(hashes.values()))==3,'ROLE_COHORT_COLLISION')
    # An exact repeated episode across roles is contamination even if aggregate hashes differ.
    sets={role:{digest_public([r]) for r in rows} for role,rows in out.items()}
    p.require(not (sets['FIT_TRAIN'] & sets['FIT_VALID'] or
                   sets['FIT_TRAIN'] & sets['DEV'] or
                   sets['FIT_VALID'] & sets['DEV']), 'CROSS_ROLE_EPISODE_REUSE')
    return out,hashes


def fit_counts_timed(rows, history):
    start=time.process_time()
    tracemalloc.start()
    table=p.fit_counts(rows,history)
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    serialized=json.dumps([[list(k),list(v)] for k,v in sorted(table.items())],
                          separators=(',',':')).encode()
    return table,{'fit_valid_cpu_s':time.process_time()-start,
                  'tracemalloc_peak_bytes':peak,'checkpoint_bytes':len(serialized),
                  'checkpoint_sha256':hashlib.sha256(serialized).hexdigest(),
                  'rss_peak_bytes':None,'rss_qualification':'NATIVE_PEAK_RSS_PENDING',
                  'selected_epoch':None,'selected_restart':None}


def score_predictions(rows, predictor):
    start=time.process_time()
    losses=[]
    false_positives=0
    for row in rows:
        forecast=predictor(row)
        losses.append(p.nll(row,forecast))
        for t,pair in enumerate(forecast):
            for j,predicted in enumerate(pair):
                false_positives+=int(predicted>=.5 and row[1][t+1][j]==0)
    p.require(all(math.isfinite(x) for x in losses),'NONFINITE_DEVELOPMENT_LOSS')
    return {'episode_nll':losses,'mean_nll':sum(losses)/len(losses),
            'ordinary_bit_false_positive_count':false_positives,
            'dev_inference_cpu_s':time.process_time()-start}


def evaluate_one_family(by_role,family,doc):
    """Development evaluation only. Caller must already have CKB admission."""
    p.require(family in p.FAMILIES,'UNKNOWN_EVALUATION_FAMILY')
    p.require(doc['schema']==p.SCHEMA,'PROTOCOL_DRIFT')
    rows,hashes=check_role_bound_rows(by_role,family)
    fit,val,dev=(rows[x] for x in ('FIT_TRAIN','FIT_VALID','DEV'))
    arms={}
    for name,history in ((ARM_NAMES[0],False),(ARM_NAMES[2],True)):
        table,cost=fit_counts_timed(fit,history)
        fn=lambda row,model=table,h=history:p.forecast_counts(model,row,h)
        arms[name]={'result':score_predictions(dev,fn),'fit_cost':cost}
    for name in (m.MODEL_NAMES[0],m.MODEL_NAMES[1],m.MODEL_NAMES[2]):
        model,cost=m.fit_gradient(name,fit,val)
        cost['checkpoint_sha256']=m.checkpoint_sha(model)
        arms[name]={'result':score_predictions(dev,lambda r,x=model:m.model_predict(x,r)),
                    'fit_cost':cost}
    for hidden,name in ((2,m.MODEL_NAMES[3]),(4,m.MODEL_NAMES[4])):
        model,cost=m.fit_hmm(hidden,fit,val)
        cost['checkpoint_sha256']=m.checkpoint_sha(model)
        arms[name]={'result':score_predictions(dev,lambda r,x=model:m.model_predict(x,r)),
                    'fit_cost':cost}
    p.require(set(arms)==set(ARM_NAMES),'EMPIRICAL_ARM_MISSING')
    best_current=min(MEMORYLESS,key=lambda name:arms[name]['result']['mean_nll'])
    best_history=min(HISTORY,key=lambda name:arms[name]['result']['mean_nll'])
    oracle=score_predictions(dev,lambda row:p.marginalized_public_oracle(row,doc))
    gains=m.paired_episode_bootstrap(
        arms[best_current]['result']['episode_nll'],
        arms[best_history]['result']['episode_nll'],family)
    return {'family':family,'role_sha256':hashes,'arm_results':arms,
            'best_current':best_current,'best_history':best_history,
            'gain':gains,'privileged_oracle_nll':oracle['mean_nll'],
            'oracle_is_not_matched_comparator':True,
            'public_oracle_headroom':arms[best_current]['result']['mean_nll']-oracle['mean_nll'],
            'native_peak_rss_qualified':False,
            'protected_scientific_first_use':False}


def preliminary_decision(by_family,doc):
    p.require(set(by_family)==set(p.FAMILIES),'ALL_FAMILIES_REQUIRED')
    d=doc['frozen_dev_decision']
    real=[]
    for family in p.FAMILIES[:2]:
        result=by_family[family]
        g=result['gain']
        real.append(g['gain_nats_per_bit'] >= d['history_gain_min_nats_per_bit_each_real_family']
                    and g['lower_95'] >= d['history_gain_95pct_bootstrap_lower_bound_each_real_family_min']
                    and result['public_oracle_headroom'] >=
                        d['public_oracle_headroom_vs_best_memoryless_min_nats_each_real_family'])
    null_gain=by_family[p.FAMILIES[2]]['gain']['gain_nats_per_bit']
    descriptive=all(real) and null_gain<=d['null_family_max_apparent_history_gain_nats']
    return {'q21_development_thresholds_met':descriptive,
            'native_windows_linux_crosscheck':'NOT_VERIFIED',
            'peak_rss_and_full_resource_accounting':'NOT_VERIFIED',
            'full_integration_regression':'NOT_RUN',
            'ckb_scientific_acceptance':'NOT_AUTHORIZED',
            'gate_status':'REQUIRES_NATIVE_CKB_QUALIFICATION',
            'per_real_family_meets_thresholds':real,
            'null_gain_nats_per_bit':null_gain}
