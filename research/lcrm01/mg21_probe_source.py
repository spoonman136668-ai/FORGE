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
