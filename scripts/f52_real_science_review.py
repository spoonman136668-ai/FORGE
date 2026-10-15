"""F52 read-only independent review of two genuine negative TRAIN studies.

Checks GitHub-pinned first-attempt artifact content, row scoring, family
nondegradation and public retention receipts. No original, replay, or live
Dream/Theta policy updates.
"""
import argparse, hashlib, json
from pathlib import Path

class Blocked(ValueError): pass
def require(ok, reason):
    if not ok: raise Blocked("F52_" + reason)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def unique(pairs):
    result = {}
    for k,v in pairs:
        require(k not in result, "DUPLICATE_JSON_KEY")
        result[k]=v
    return result
def read_json(path):
    raw=Path(path).read_bytes()
    require(0<len(raw)<=3000000, "JSON_SIZE")
    return json.loads(raw,object_pairs_hook=unique)
def load(directory, spec):
    directory=Path(directory)
    raw=(directory/"result.json").read_bytes()
    require(0<len(raw)<=3000000 and sha(raw)==spec["report_sha256"],
            "REPORT_SHA_DRIFT")
    digest=(directory/"sha256-manifest.txt").read_text().splitlines()
    require(len(digest)==2 and digest[0].split()==[sha(raw),"result.json"],
            "REPORT_MANIFEST")
    audit=(directory/"independent-audit.txt").read_bytes()
    require(digest[1].split()==[sha(audit),"independent-audit.txt"],
            "AUDIT_MANIFEST")
    require((directory/"SOURCE_SHA").read_text().strip()==spec["head"],
            "SOURCE_SHA_DRIFT")
    doc=json.loads(raw,object_pairs_hook=unique)
    require(doc.get("original_executed") is False and
            doc.get("source_independent_F3") is False and
            doc.get("accepted_ref_mutation") is False and
            doc.get("paid_api_calls")==0, "FALSE_SCIENTIFIC_AUTHORITY")
    return doc

def score_rows(lane, spec, doc):
    is_w = lane == "Wingless"
    n=128 if is_w else 64
    schema=("wingless.f52.public-law-model-averaging.trainonly.v1" if is_w
        else "yggdrasil.f52.bridge-aware-neutral-tags.trainonly.v1")
    stage=("TRAIN_ONLY_UNSEEN_CONTEXT_OPERATOR_LAWS_NOT_ORIGINAL" if is_w
        else "TRAIN_ONLY_UNSEEN_DISTRACTOR_GRAPH_TOPOLOGY_NOT_ORIGINAL")
    require(doc.get("schema")==schema and doc.get("stage")==stage,
            "SCHEMA_STAGE")
    require(doc.get("cases")==n and len(doc.get("rows",[]))==n,
            "COHORT_COUNT")
    require(doc.get("original_seeds_NOT_RESERVED")==spec["future_original_NOT_CONSUMED"],
            "ORIGINAL_IDENTITY")
    require(set(doc.get("diagnostic_families",[]))==set(spec["heldout_families"]),
            "HELDOUT_FAMILIES")
    rows=doc["rows"];scores=doc["scores"]
    arms=set(scores);oracle=("private_sign_oracle_unfair" if is_w
                           else "private_future_question_oracle_unfair")
    candidate=("public_bayesian_law_posterior" if is_w
               else "learned_bridge_retention")
    require(candidate in arms and oracle in arms and len(arms)>5,
            "ARM_IDENTITY")
    seen=set()
    for row in rows:
        key=(row["seed"],row["family"],row["length"]) if is_w else (
            row["seed"],row["family"])
        require(key not in seen and row["family"] in spec["heldout_families"],
                "DUPLICATE_OR_FAMILY")
        seen.add(key)
        if is_w:
            require(561100<=row["seed"]<561116 and
                    row["length"] in (3,5,6,8) and
                    set(row["answers"])==arms and
                    row["answers"][oracle]==row["truth"] and
                    len(row["public"])==4,
                    "W_SOURCE_ROW")
        else:
            require(571100<=row["seed"]<571116 and
                    set(row["results"])==arms and
                    len(row["public_events"])==64 and
                    set(row["retained_indices"])==arms-{oracle} and
                    row["results"][oracle]==1,
                    "Y_SOURCE_ROW")
            question=row["question"]
            for arm, indices in row["retained_indices"].items():
                require(len(indices)==12 and
                        len(set(indices))==12 and
                        all(type(i)==int and 0<=i<64 for i in indices),
                        "Y_MEMORY_RECEIPTS")
                held=[row["public_events"][i] for i in indices]
                at=question["start"]
                reached=True
                for role,direction in question["chain"]:
                    opts=[v for v in held if v[1]==role and
                          (v[0] if direction==1 else v[2])==at]
                    if len(opts)!=1:
                        reached=False;break
                    at=opts[0][2] if direction==1 else opts[0][0]
                require(int(reached and at==question["answer"])==
                        row["results"][arm],"Y_PATH_RECOUNT")
    def value(row,arm):
        return int(row["answers"][arm]==row["truth"]) if is_w else int(row["results"][arm])
    counted={a:sum(value(r,a) for r in rows) for a in arms}
    for arm in arms:
        require(counted[arm]==scores[arm]["correct"] and
                scores[arm]["total"]==n and
                abs(scores[arm]["accuracy"]-counted[arm]/n)<1e-12,
                "SCORE_RECOUNT")
    families={}
    for family in spec["heldout_families"]:
        subset=[r for r in rows if r["family"]==family]
        require(len(subset)==n//4,"FAMILY_BALANCE")
        families[str(family)]={a:sum(value(r,a) for r in subset) for a in arms}
    require(families==doc["by_family"], "BY_FAMILY_RECOUNT")
    fair=arms-{candidate,oracle}
    strongest=max(counted[a] for a in fair)
    gain=(counted[candidate]-strongest)/n
    family_guard=all(families[str(f)][candidate]>=
        max(families[str(f)][a] for a in fair) for f in spec["heldout_families"])
    qualified=gain>=spec["predeclared_gain_pp"]/100 and family_guard
    require(abs(doc["candidate_gain"]-gain)<1e-12 and
            doc["per_family_nondegradation"]==family_guard and
            doc["frozen_gate_met"]==qualified and
            doc["verdict"]==spec["source_report"] and not qualified,
            "FROZEN_THRESHOLD")
    require(counted[candidate]==(106 if is_w else 5) and
            strongest==(99 if is_w else 8), "EXPECTED_AUTHENTIC_OUTCOME")
    return dict(lane=lane,attempt=1,run_id=spec["run"],
        report_sha256=spec["report_sha256"],records=n,
        candidate_correct=counted[candidate],strongest_fair_correct=strongest,
        gain_percentage_points=round(gain*100,6),
        all_family_results=families,nondegradation=family_guard,
        science_verdict="TRAIN_ONLY_NEGATIVE",
        eligible_for_scientific_promotion=False,
        next_hypothesis=("GENERALIZE_PUBLIC_RELATION_LAW_INFERENCE_ACROSS_FAMILY_1006_WITH_PREDECLARED_STABILITY_CONTROLS"
            if is_w else
            "LEARN_TO_PRESERVE_MULTI_STEP_GRAPH_CONNECTIVITY_UNDER_NOVEL_STAR_DISTRACTORS_AND_EQUAL_MEMORY"))
def review(root, manifest):
    root=Path(root)
    require(manifest.get("schema")=="forge.f52.authentic-science-source-manifest.v1"
        and set(manifest["science"])=={"Wingless","Yggdrasil"},
        "MANIFEST_IDENTITY")
    outcomes=[]
    for lane,spec in manifest["science"].items():
        doc=load(root/lane,spec)
        outcomes.append(score_rows(lane,spec,doc))
    require(all(x["science_verdict"]=="TRAIN_ONLY_NEGATIVE" for x in outcomes),
        "UNQUALIFIED_ACCEPTANCE")
    return dict(schema="forge.f52.two-real-train-negatives-f53-advisory.v1",
        source_pins=manifest["science"],outcomes=outcomes,
        separate_engineering_failures=manifest["separate_failures"],
        independently_recounted_real_train_experiments=2,
        primary_originals_executed=0,science_accepted=False,
        dream_rsi_policy_improvement_proven=False,
        theta_evolve_promotion_authorized=False,
        new_scientific_dispatch_authorized=False,
        automatic_f53_hypotheses_prepared=True)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    manifest=read_json(a.manifest)
    Path(a.out).write_text(json.dumps(review(a.root,manifest),
        sort_keys=True,separators=(",",":"))+"\n")
if __name__=="__main__":main()
