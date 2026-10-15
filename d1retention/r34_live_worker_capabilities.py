"""R34: inspect REAL current deployed Cloudflare Worker capability, read-only.

Do not infer signer custody, atomic original claims or authorization merely
from a binding name. Zero secrets, tokens, or worker source are emitted.
"""
import json,os,sys
import install_remote as c

def scan(api):
    account=api.account
    script=c.SCRIPT
    ds=api.call("accounts/"+account+"/workers/scripts/"+script+"/deployments")
    versions=ds.get("deployments",[{}])[0].get("versions",[]) if isinstance(ds,dict) else []
    serving=[v for v in versions if isinstance(v,dict) and v.get("percentage",0)>0]
    if len(serving)!=1 or serving[0].get("percentage")!=100:
        raise RuntimeError("R34_SINGLE_SERVING_VERSION_REQUIRED")
    version=serving[0].get("version_id")
    info=api.call("accounts/"+account+"/workers/scripts/"+script+"/versions/"+version)
    bindings=info.get("resources",{}).get("bindings",[]) if isinstance(info,dict) else []
    if not isinstance(bindings,list) or len(bindings)>64:raise RuntimeError("R34_BOUNDING_FAILED")
    kinds={}
    for binding in bindings:
        if not isinstance(binding,dict) or not isinstance(binding.get("type"),str):
            raise RuntimeError("R34_BAD_BINDING_METADATA")
        kind=binding["type"]
        kinds[kind]=kinds.get(kind,0)+1
    if kinds.get("d1",0)!=1:raise RuntimeError("R34_EXISTING_D1_BOUND_IDENTITY_CHANGED")
    return {
     "schema":"forge.r34.existing-worker-runtime-binding-observation.v1",
     "exact_single_live_version":True,
     "d1_bindings":kinds.get("d1",0),
     "durable_object_bindings":sum(v for k,v in kinds.items() if "durable_object" in k),
     "service_bindings":sum(v for k,v in kinds.items() if "service" in k),
     "binding_types_observed":len(kinds),
     "independently_deployed_owner_signer_verified":False,
     "monotonic_first_use_cas_end_to_end_verified":False,
     "scientific_execution_authorized":False,
     "read_only":True,
    }

def main():
    api=c.Cloudflare(os.environ.get("CLOUDFLARE_ACCOUNT_ID",""),
                     os.environ.get("CLOUDFLARE_API_TOKEN",""))
    output=scan(api)
    print(json.dumps(output,sort_keys=True,separators=(",",":")))
if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("R34_LIVE_WORKER_INSPECTION_BLOCKED:"+type(exc).__name__,file=sys.stderr)
        raise SystemExit(1)
