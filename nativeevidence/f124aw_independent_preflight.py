"""F124-AW independently authenticate original FIT/SREEN selection without DEV."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
import f124aw_first_ygg_dev_evidence as ev
def main():
    p=argparse.ArgumentParser()
    for k in ("av","o","t","an","ao","ap","aq","ar",
              "as_train","as_dev","at","output"):
        p.add_argument("--"+k,required=True)
    x=p.parse_args();out=Path(x.output)
    ev.need(out.parent.is_dir() and not out.exists(),"NO_PREFLIGHT_OVERWRITE")
    refs=[getattr(x,k) for k in ("o","t","an","ao","ap","aq",
                                "ar","as_train","as_dev","at")]
    base,delta=ev.preflight(x.av,refs)
    d={"schema":"forge.research.f124aw.independent-before-first-dev-preflight.v1",
       "frozen_selection":ev.LOCKED,
       "original_AV_original_raw_sha256":ev.ORIGINAL_AV_SHA,
       "prospective_DEV_range":[4300100,4300123],
       "original_donor_Ygg_weights":base,
       "original_donor_Ygg_delta":delta,
       "original_7_active_9_retained":True,
       "DEV_cases_created":0,"DEV_consumed":False,
       "Wingless_DEV_cases_created":0,"protected_first_use":False,
       "optimizer_promotion":False}
    raw=json.dumps(d,sort_keys=True,indent=2).encode()+b"\n"
    with out.open("xb") as f:f.write(raw)
    print("F124AW_PREFLIGHT_SHA256="+hashlib.sha256(raw).hexdigest())
    print("F124AW_SELECTED_CONFIG_AUTHENTIC=PASS")
    print("F124AW_DEV_GENERATED=false")
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as exc:
        print("F124AW_PREFLIGHT_FAIL_CLOSED:"+str(exc),file=sys.stderr)
        sys.exit(1)
