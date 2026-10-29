"""MG24 authentic original MiniGrid selected action and consequence episode.

Separate original world for each native/conventional/random arm. No private
grid/inventory, no evaluator-provided navigation, original source mission intact.
All experiments here are exposed development, NOT sealed first-use science.
"""
from __future__ import annotations
import base64,hashlib,math,random,time
import psutil

from mg17_original_family_source_qual import public,digest
from mg18_native_mission_boundary_audit import WingBridge
from mg23_independent_public_credit import Conventional,selected_target
from research.native.itd02.mg19.original_mission_cells import OriginalMissionAdapter
from research.native.itd02.mg19.genuine_mission_cells import MissionCells
from research.native.itd02.mg23.selected_target_cells import TargetCreditCells

ROLES=("wingless_MG23","wingless_MG19","yggdrasil_MG23","yggdrasil_MG19",
       "conventional_full","conventional_no_target","conventional_no_delayed",
       "conventional_no_both","unassisted_original_random")

def instantiate(role,prior,go23,go19,family,seed):
 if role.startswith("wingless_"):
  actor=WingBridge(go23 if role=="wingless_MG23" else go19)
  if prior is not None:
   reply=actor.request("load",state=base64.b64encode(prior).decode("ascii"))
   if actor.snapshot()!=prior:
    raise ValueError("MG24_GO_COLD_SOURCE_STATE_DRIFT")
  return actor,None,reply.get("updates",0) if prior is not None else 0
 if role.startswith("yggdrasil_"):
  cls=TargetCreditCells if role=="yggdrasil_MG23" else MissionCells
  actor=cls() if prior is None else cls.restore(prior)
  adapter=OriginalMissionAdapter()
  return actor,adapter,actor.samples
 if role.startswith("conventional_"):
  flags={"conventional_full":(True,True),"conventional_no_target":(False,True),
         "conventional_no_delayed":(True,False),"conventional_no_both":(False,False)}
  actor=Conventional(*flags[role]) if prior is None else Conventional.restore(prior)
  if (actor.target,actor.delayed)!=flags[role]:
   raise ValueError("MG24_CONVENTIONAL_ABLATION_FLAG_DRIFT")
  return actor,None,actor.samples
 if role=="unassisted_original_random":
  if prior is not None:raise ValueError("MG24_RANDOM_MUST_NOT_INHERIT_MEMORY")
  return random.Random("MG24-unassisted-original:"+family+":"+str(seed)),None,0
 raise ValueError("MG24_UNREGISTERED_NATIVE_OR_CONTROL")

def select(role,actor,before):
 if role.startswith("wingless_"):
  proposal=actor.request("choose",before=before)
  choice,status=proposal.get("action"),proposal.get("status")
 elif role.startswith("yggdrasil_"):
  proposal=actor.choose(before)
  if proposal.get("external_fallback") is not False:
   raise ValueError("MG24_YGG_EXTERNAL_ACTION")
  choice,status=proposal.get("action"),proposal.get("status")
 elif role.startswith("conventional_"):
  choice,status=actor.choose(before)
 else:
  choice=actor.randrange(7)
  status="SOURCE_UNASSISTED_RANDOM_ACTION"
 if type(choice)is not int or choice not in range(7) or type(status)is not str or not status:
  raise ValueError("MG24_EXTERNAL_OR_INVALID_NATIVE_POLICY_ACTION")
 return choice,status

def front_door_unlock(before,action,after):
 if action!=5 or before["direction"]!=after["direction"]:return False
 b=before["image"][3][5];a=after["image"][3][5]
 return b[0]==4 and a[0]==4 and b[1]==a[1] and b[2]==2 and a[2]==0

def episode(gym,family,seed,role,cap,prior,go23,go19,entry):
 actor,adapter,initial_count=instantiate(role,prior,go23,go19,family,seed)
 env=gym.make(family)
 wall0=time.perf_counter();cpu0=time.process_time()
 native_cpu_start=None;native_rss_max=None
 if role.startswith("wingless_"):
  proc=psutil.Process(actor.proc.pid)
  ct=proc.cpu_times();native_cpu_start=ct.user+ct.system
 try:
  if getattr(env.action_space,"n",None)!=7 or gym.spec(family).entry_point!=entry:
   raise ValueError("MG24_UNAUTHENTICATED_ORIGINAL_ACTION_SPACE")
  obs,_=env.reset(seed=seed)
  start=public(obs)
  if role.startswith("wingless_"):
   if actor.request("begin_episode").get("updates",0)!=initial_count:
    raise ValueError("MG24_SOURCE_PARENT_GO_EPISODE_RESET")
  elif adapter is not None:
   adapter.reset_public(start)
   actor.start_session(adapter,"mg24-prospective-dev:"+family+":"+str(seed),live=True)
   if actor.samples!=initial_count:raise ValueError("MG24_SOURCE_PARENT_YGG_RESET")
  elif role.startswith("conventional_"):
   actor.begin_episode()
  first_sha=digest(start)
  data=[];prior_view=start;pickup_at=[];door_at=[];goal_at=[]
  for index in range(1,cap+1):
   before=public(obs)
   if before["mission"]!=start["mission"] or before!=prior_view:
    raise ValueError("MG24_SELECTED_SOURCE_EVENT_CHAIN_INVALID")
   action,status=select(role,actor,before)
   if role.startswith("wingless_"):
    actor.request("commit",before=before,action=action)
   elif adapter is not None:
    if adapter.submit(action)!=action:raise ValueError("MG24_NATIVE_ACTION_REMAP")
   elif role.startswith("conventional_"):
    if actor.submit(before,action)!=action:raise ValueError("MG24_CONTROL_ACTION_REMAP")
   nxt,reward,term,trunc,_=env.step(action)
   after=public(nxt)
   value=float(reward)
   if (after["mission"]!=start["mission"] or type(term)is not bool or
       type(trunc)is not bool or not math.isfinite(value)):
    raise ValueError("MG24_FARAMA_SOURCE_MISSION_OR_CONSEQUENCE_INVALID")
   done=term or trunc
   if role.startswith("wingless_"):
    count=actor.request("feedback",before=before,action=action,after=after,
                         reward=value,terminal=done).get("updates")
   elif adapter is not None:
    adapter.complete(after,value,term,trunc)
    actor.learn_selected(adapter,before,after)
    count=actor.samples
   elif role.startswith("conventional_"):
    actor.learn(before,action,after,value,done,selected=True)
    count=actor.samples
   else: count=None
   if role!="unassisted_original_random" and count!=initial_count+index:
    raise ValueError("MG24_SELECTED_SOURCE_SAMPLE_COUNT_DRIFT")
   target=selected_target(before,action,after)
   door=front_door_unlock(before,action,after)
   if target:pickup_at.append(index)
   if door:door_at.append(index)
   if value>0 and term:goal_at.append(index)
   data.append({"index":index,"action":action,"policy":status,"before":before,
                "after":after,"reward":value,"terminated":term,"truncated":trunc,
                "before_sha256":digest(before),"after_sha256":digest(after),
                "public_mission_target_pickup":target,"public_locked_door_open":door,
                "selected_source_count":count})
   if role.startswith("wingless_") and index%16==0:
    try:
     native_rss_max=max(native_rss_max or 0,proc.memory_info().rss)
    except psutil.NoSuchProcess as e:raise ValueError("MG24_GO_PROCESS_LOST") from e
   obs=nxt;prior_view=after
   if done:break
  if not data:raise ValueError("MG24_SOURCE_NO_ACTIONS")
  if role.startswith("wingless_"):
   checkpoint=actor.snapshot()
   restored=WingBridge(go23 if role=="wingless_MG23" else go19)
   try:
    ack=restored.request("load",state=base64.b64encode(checkpoint).decode("ascii"))
    if ack.get("updates",0)!=initial_count+len(data) or restored.snapshot()!=checkpoint:
     raise ValueError("MG24_GO_SOURCE_COLD_REPLAY_MISMATCH")
   finally:restored.close()
  elif adapter is not None:
   checkpoint=actor.checkpoint()
   cls=TargetCreditCells if role=="yggdrasil_MG23" else MissionCells
   if cls.restore(checkpoint).checkpoint()!=checkpoint:
    raise ValueError("MG24_YGG_SOURCE_COLD_REPLAY_MISMATCH")
  elif role.startswith("conventional_"):
   checkpoint=actor.snapshot()
   if Conventional.restore(checkpoint).snapshot()!=checkpoint:
    raise ValueError("MG24_CONVENTIONAL_ABLATION_COLD_REPLAY_MISMATCH")
  else:checkpoint=None
  go_cpu=None
  if role.startswith("wingless_"):
   ct=proc.cpu_times();go_cpu=round(ct.user+ct.system-native_cpu_start,6)
   native_rss_max=max(native_rss_max or 0,proc.memory_info().rss)
  metrics={"role":role,"family":family,"seed_exposed":seed,
           "python_cpu_seconds":round(time.process_time()-cpu0,6),
           "parent_wall_seconds":round(time.perf_counter()-wall0,6),
           "go_child_cpu_seconds":go_cpu,"go_child_sampled_max_rss_bytes":native_rss_max,
           "checkpoint_bytes":0 if checkpoint is None else len(checkpoint)}
  result={"family":family,"dev_seed_exposed":seed,"role":role,
          "original_start_sha256":first_sha,"original_mission":start["mission"],
          "selected_actions":len(data),"prior_selected_source_samples":initial_count,
          "selected_source_samples_after":None if checkpoint is None else initial_count+len(data),
          "original_terminal_goal_reward_count":len(goal_at),
          "selected_public_target_pickup_count":len(pickup_at),
          "selected_public_locked_door_open_count":len(door_at),
          "observed_public_pickup_then_door_then_terminal_reward":any(p<d<g for p in pickup_at for d in door_at for g in goal_at),
          "observed_public_changes":sum(e["before_sha256"]!=e["after_sha256"] for e in data),
          "positive_reward_total":sum(e["reward"] for e in data if e["reward"]>0),
          "terminated":data[-1]["terminated"],"truncated":data[-1]["truncated"],
          "checkpoint_sha256":None if checkpoint is None else hashlib.sha256(checkpoint).hexdigest(),
          "selected_source_events_sha256":digest(data),"selected_source_events":data}
  return result,metrics,checkpoint
 finally:
  env.close()
  if role.startswith("wingless_"):actor.close()
