"""MG21 authentic original action/probe feedback; engineering only."""
from mg17_original_family_source_qual import public,digest

def probe(gym,family,role,seed,cap,model,adapter,fit_count):
 env=gym.make(family)
 events=[]
 try:
  if env.action_space.n!=7:raise ValueError("MG21_ACTION_SPACE")
  raw,_=env.reset(seed=seed)
  first=public(raw);before=first
  if role.startswith("go_"):
   if model.request("begin_episode").get("updates",0)!=fit_count:
    raise ValueError("MG21_GO_FIT_NOT_RETAINED")
  elif role.startswith("ygg_"):
   adapter.reset_public(before)
   model.start_session(adapter,"mg21-probe:"+family,live=True)
   if model.samples!=fit_count:raise ValueError("MG21_YGG_FIT_NOT_RETAINED")
  elif role.startswith("tabular_") and model.samples!=fit_count:
   raise ValueError("MG21_CONTROL_FIT_NOT_RETAINED")
  for index in range(1,cap+1):
   if role.startswith("go_"):
    chosen=model.request("choose",before=before)
    action,status=chosen.get("action"),chosen.get("status")
   elif role.startswith("ygg_"):
    chosen=model.choose(before)
    if chosen["external_fallback"]:raise ValueError("MG21_YGG_EXTERNAL_ACTION")
    action,status=chosen["action"],chosen["status"]
   elif role.startswith("tabular_"):action,status=model.choose(before)
   else:action,status=model.randrange(7),"UNASSISTED_ORIGINAL_RANDOM"
   if type(action)is not int or action not in range(7) or not status:
    raise ValueError("MG21_UNSELECTED_ORIGINAL_ACTION")
   if role.startswith("go_"):
    model.request("commit",before=before,action=action)
   elif role.startswith("ygg_") and adapter.submit(action)!=action:
    raise ValueError("MG21_NATIVE_ACTION_REMAP")
   raw_next,reward,term,trunc,_=env.step(action)
   after=public(raw_next);reward=float(reward)
   if after["mission"]!=first["mission"]:
    raise ValueError("MG21_ORIGINAL_SOURCE_MISSION_DRIFT")
   done=bool(term or trunc)
   if role.startswith("go_"):
    ack=model.request("feedback",before=before,action=action,
         after=after,reward=reward,terminal=done)
    count=ack.get("updates",0)
   elif role.startswith("ygg_"):
    adapter.complete(after,reward,bool(term),bool(trunc))
    model.learn_selected(adapter,before,after);count=model.samples
   elif role.startswith("tabular_"):
    model.learn(before,action,after,reward,done);count=model.samples
   else:count=None
   if role!="random" and count!=fit_count+index:
    raise ValueError("MG21_SELECTED_SOURCE_COUNT_DRIFT")
   events.append({"index":index,"before":before,"action":action,
         "status":status,"after":after,"reward":reward,
         "terminated":bool(term),"truncated":bool(trunc),
         "native_updates":count})
   before=after
   if done:break
  return {"family":family,"role":role,"seed":seed,
          "mission":first["mission"],"start_sha256":digest(first),
          "fit_samples":fit_count,"probe_steps":len(events),
          "positive_rewards":sum(e["reward"]>0 for e in events),
          "terminated":events[-1]["terminated"],
          "truncated":events[-1]["truncated"],
          "distinct_public":len({digest(first)}|{digest(e["after"]) for e in events}),
          "events":events,"trace_sha256":digest(events)}
 finally:
  env.close()
