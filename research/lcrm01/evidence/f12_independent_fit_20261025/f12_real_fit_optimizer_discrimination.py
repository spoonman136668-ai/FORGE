#!/usr/bin/env python3
"""Read-only post-hoc Wingless F12 FIT grouped CV; never inspect DEV outcome.

Original third-party MiniGrid source physically executed all 3 candidate interventions.
All labels here are previously exposed FIT ONLY; not scientific first-use.
No hyperparameter selection from any held-out/protected source cohort.
"""
import zipfile,json,hashlib,os,time,resource,pickle,collections
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor,ExtraTreesRegressor,HistGradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

SRC=Path('/mnt/data/github-actions-artifact-12597057624.zip')
EXPECTED='f4f567cd7b456287a93ebf725b0b6c763bb1831e43499cdbf04d9221e8df72b5'
sha=hashlib.sha256(SRC.read_bytes()).hexdigest()
assert sha==EXPECTED, 'PROVIDER_OUTER_SHA_MISMATCH'
with zipfile.ZipFile(SRC) as z: d=json.loads(z.read('process-a.json'))
# Reference original source FIT only. NEVER inspect DEV original action rewards.
rows=d['FIT_true_original_source_matched_actions']
assert len(rows)==317 and len({x['seed'] for x in rows})==48
assert all(len(x['true_source_three_arm_interventions'])==3 for x in rows)
assert all(x['family']=='fourrooms' for x in rows)
assert sum(len(x['true_source_three_arm_interventions']) for x in rows)==951

def features(r,action,mode):
 s=r['six_public_before'];dx=s['GoalX']-s['X'];dy=s['GoalY']-s['Y'];direction=s['Direction']
 b=float(s['FrontBlocked']);
 # Original public pose/goal and selected action (never hidden map or future outcome).
 base=[float(s[k]) for k in ('X','Y','GoalX','GoalY')]+[float(dx),float(dy),abs(dx)+abs(dy),b]
 base += [float(direction==t) for t in range(4)]+[float(action==t) for t in range(3)]
 base += [float(direction==t and action==a) for t in range(4) for a in range(3)]
 base += [float(action==a)*v for a in range(3) for v in (dx,dy,b)]
 if mode in ('history','graph'):
  h=r['public_history_counts'];hist=r['witnessed_action_consequence_history']
  numeric=[float(h[k]) for k in ('failed_forward_actions','reentered_departed_cells','ticks_since_last_physical_move','unique_observed_cells')]
  numeric.append(float(len(hist)));numeric.append(float(sum(bool(e['physically_moved']) for e in hist)))
  numeric.extend(float(bool(hist) and hist[-1]['action']==i) for i in (0,1,2))
  base+=numeric+[float(action==a)*v for a in range(3) for v in numeric]
 if mode=='graph':
  seen=r['local_forward_edge_counts'];k=f"{s['X']},{s['Y']},{direction}"
  local=seen.get(k,[0,0])
  val=[float(len(seen)),float(sum(pair[0] for pair in seen.values())),float(sum(pair[1] for pair in seen.values())),float(local[0]),float(local[1])]
  base+=val+[float(action==a)*v for a in range(3) for v in val]
 return base

modes=['current','history','graph']
X={mode:np.asarray([features(r,a,mode) for r in rows for a in range(3)],dtype=float) for mode in modes}
y=np.asarray([r['true_source_three_arm_interventions'][str(a)]['discounted_true_source_return'] for r in rows for a in range(3)],dtype=float)
goal=np.asarray([r['true_source_three_arm_interventions'][str(a)]['goal_success'] for r in rows for a in range(3)],dtype=bool)
steps=np.asarray([r['true_source_three_arm_interventions'][str(a)]['actual_steps_after_intervention'] for r in rows for a in range(3)],dtype=int)
seed=np.asarray([int(r['seed']) for r in rows],dtype=int)
assert np.isfinite(y).all() and np.isfinite(X['graph']).all()
# Freeze seven mechanistically different comparisons with no posthoc model/hyperparameter changes.
models={
 'ridge_current':('current',lambda:make_pipeline(StandardScaler(),Ridge(alpha=10))),
 'ridge_history':('history',lambda:make_pipeline(StandardScaler(),Ridge(alpha=10))),
 'ridge_graph':('graph',lambda:make_pipeline(StandardScaler(),Ridge(alpha=10))),
 'rf_current':('current',lambda:RandomForestRegressor(n_estimators=80,min_samples_leaf=5,max_features=.9,n_jobs=1,random_state=17)),
 'rf_history':('history',lambda:RandomForestRegressor(n_estimators=80,min_samples_leaf=5,max_features=.9,n_jobs=1,random_state=17)),
 'extra_history':('history',lambda:ExtraTreesRegressor(n_estimators=80,min_samples_leaf=5,max_features=.9,n_jobs=1,random_state=17)),
 'hgb_history':('history',lambda:HistGradientBoostingRegressor(max_iter=80,max_leaf_nodes=12,min_samples_leaf=15,learning_rate=.05,l2_regularization=10,random_state=17))
}
methods=['constant_left','public_forward_if_clear']+list(models)
chosen={k:np.full(len(rows),-1,dtype=int) for k in methods};cpu={k:0 for k in methods};max_model_bytes={k:0 for k in methods}
seed_folds=(seed-171400)%6
for f in range(6):
 train=np.where(seed_folds!=f)[0];test=np.where(seed_folds==f)[0]
 assert len(set(seed[train])&set(seed[test]))==0
 chosen['constant_left'][test]=0
 chosen['public_forward_if_clear'][test]=[2 if not rows[i]['six_public_before']['FrontBlocked'] else 0 for i in test]
 train_rows=np.concatenate([np.asarray([3*i+a for a in range(3)]) for i in train]);test_rows=np.concatenate([np.asarray([3*i+a for a in range(3)]) for i in test]);
 for name,(mode,ctor) in models.items():
  t0=time.process_time_ns();model=ctor();model.fit(X[mode][train_rows],y[train_rows]);pred=model.predict(X[mode][test_rows]).reshape(-1,3)
  chosen[name][test]=np.argmax(pred,axis=1);cpu[name]+=(time.process_time_ns()-t0);max_model_bytes[name]=max(max_model_bytes[name],len(pickle.dumps(model,protocol=5)))
assert all(np.all(z>=0) for z in chosen.values())
outcomes={};oracle=y.reshape(-1,3).max(axis=1)
for method,a in chosen.items():
 ind=3*np.arange(len(rows))+a
 reward=y[ind];regret=oracle-reward
 outcomes[method]={'chosen_reward_mean':float(np.mean(reward)),'oracle_regret_mean':float(np.mean(regret)),'goals':int(goal[ind].sum()),'mean_steps':float(np.mean(steps[ind])),'action_hist':np.bincount(a,minlength=3).tolist(),'model_cpu_seconds':round(cpu[method]/1e9,3),'max_serialized_model_bytes':max_model_bytes[method],'different_from_left':int((a!=0).sum()),'mean_regret_by_world_seed':{str(s):float(np.mean(regret[seed==s])) for s in sorted(set(seed))}}
# Preplanned regret gap vs current-state standard conventional baseline, 48 seed-level paired differences.
reference='ridge_current';comparisons={}
ref=np.asarray([outcomes[reference]['mean_regret_by_world_seed'][str(s)] for s in sorted(set(seed))]);
for method in methods:
 if method==reference:continue
 oth=np.asarray([outcomes[method]['mean_regret_by_world_seed'][str(s)] for s in sorted(set(seed))]);diff=ref-oth
 comparisons[method]={'paired_mean_improvement_seed_level':float(diff.mean()),'n_seed_positive':int((diff>1e-12).sum()),'n_seed_negative':int((diff< -1e-12).sum()),'n_seed_equal':int((abs(diff)<=1e-12).sum())}
# Advisory Pareto only: equal-world sampled reward up, action count down, serialized fit artifact down; unlike CPU model comparisons are not whole-system CPU.
pareto=[]
for k,v in outcomes.items():
 if not any((w['chosen_reward_mean']>=v['chosen_reward_mean'] and w['mean_steps']<=v['mean_steps'] and w['max_serialized_model_bytes']<=v['max_serialized_model_bytes'] and (w['chosen_reward_mean']>v['chosen_reward_mean']+1e-12 or w['mean_steps']<v['mean_steps']-1e-12 or w['max_serialized_model_bytes']<v['max_serialized_model_bytes'])) for other,w in outcomes.items() if other!=k):pareto.append(k)
report={'kind':'INDEPENDENT_POSTHOC_PUBLIC_FIT_EXPLORATORY_NOT_PROSPECTIVE', 'original_archive_sha256':sha,'n_source_world_seed_clusters':48,'n_original_public_fit_anchors':317,'n_physically_intervened_actual_source_action_choices':951,'outer_fit_world_seed_folds':6,'protected_or_dev_outcomes_used':False,'original_source_new_steps':0,'mechanism_optimizers_available_advisory':['Dream-RSI','ShinkaEvolve','ThetaEvolve','Pareto','Promptbreeder','DGM','GenEnv','hypothesis_discrimination','content_addressed_reuse'], 'source_actions':{'0':'turn-left','1':'turn-right','2':'forward'},'outcomes':outcomes,'paired_seed_level_differences':comparisons,'pareto_advisory':pareto,'scientific_go':False}
out=Path('/mnt/data/f12_fit_grouped_exploratory_result.json');out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
print('original_hash',sha,'n_FIT',len(rows),'n_seeds',len(set(seed)))
for k in methods:
 z=outcomes[k];print(k, 'reward',round(z['chosen_reward_mean'],6),'regret',round(z['oracle_regret_mean'],6),'success',z['goals'],'steps',round(z['mean_steps'],3),'chosen',z['action_hist'],'bytes',z['max_serialized_model_bytes'],'fitcpu',z['model_cpu_seconds'])
print('pareto',pareto)
print('pairs',{k:{kk:round(vv,6) if isinstance(vv,float) else vv for kk,vv in v.items()} for k,v in comparisons.items()})
print('report',out)
