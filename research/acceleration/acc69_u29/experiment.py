"""ACC69 U29 topology-to-semantics source-bound leave-one-assignment-out screen."""
import hashlib,json,struct,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
REG=ROOT/"research/ac07_sourcefree/ac08_portfolio.py"
PRE=ROOT/"docs/research/ACC-69-U29-PREREG-20261030.md"
BLOB="5126c860771fb024ccfc14c3f7ee8925edf29787"
PRE_SHA="d2626f95fbe54a4e3cad46d66c42ea592c4cf44c"
SIZES=(4,6,8);ASSIGNMENTS=range(16);DOMAIN=b"forge-acc69-u29-label-v1"
def sha(x):return hashlib.sha256(x).hexdigest()
def blob(x):return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def custody():
    if blob(REG.read_bytes().replace(b"\r\n",b"\n"))!=BLOB:raise RuntimeError("ORIGINAL_U29_BLOB_DRIFT")
    if '"topology to semantic prediction"' not in REG.read_text():raise RuntimeError("U29_CLAIM_DRIFT")
    if "ACC-69 / U29" not in PRE.read_text():raise RuntimeError("FROZEN_PREREG_MISSING")
    return {"claim":"U29","registry_blob":BLOB,"prereg_commit":PRE_SHA}
def edges(n):
    if n not in SIZES:raise ValueError("unfrozen graph")
    return tuple((i,(i+1)%n) for i in range(n))
def labels(n,assignment):
    if n not in SIZES or assignment not in ASSIGNMENTS:raise ValueError("unfrozen roles")
    return tuple(hashlib.sha256(DOMAIN+struct.pack(">III",n,assignment,i)).digest()[0]%2 for i in range(n))
def majority(xs):
    if not xs:raise ValueError("empty train assignments")
    return int(sum(xs)>len(xs)/2)
def study():
    source=custody()
    cases=[];witness=[]
    for n in SIZES:
        all_labels={a:labels(n,a) for a in ASSIGNMENTS}
        topo=sha(json.dumps(edges(n),separators=(",",":")).encode())
        for index in range(n):
            if len(set(all_labels[a][index] for a in ASSIGNMENTS))>1:
                witness.append({"n":n,"edge_index":index,"topology_sha256":topo,
                    "zero_assig":next(a for a in ASSIGNMENTS if all_labels[a][index]==0),
                    "one_assig":next(a for a in ASSIGNMENTS if all_labels[a][index]==1)})
        for withheld in ASSIGNMENTS:
            train=[all_labels[a] for a in ASSIGNMENTS if a!=withheld]
            global_mode=majority([value for row in train for value in row])
            per_edge=tuple(majority([row[i] for row in train]) for i in range(n))
            truth=all_labels[withheld]
            global_pred=(global_mode,)*n
            baseline_pred=per_edge
            p=(sum(v for row in train for v in row)+1)/(len(train)*n+2)
            nll=-sum(__import__("math").log(p if v else 1-p) for v in truth)/n
            cases.append({"n":n,"withheld_assignment":withheld,"edges":n,
                "topology_sha256":topo,
                "withheld_labels_sha256":sha(bytes(truth)),
                "topology_only_prediction_sha256":sha(bytes(global_pred)),
                "per_edge_control_prediction_sha256":sha(bytes(baseline_pred)),
                "topology_only_correct":sum(x==y for x,y in zip(global_pred,truth)),
                "per_edge_control_correct":sum(x==y for x,y in zip(baseline_pred,truth)),
                "topology_only_nll":nll,
                "global_train_label_frequency":p})
    if len(cases)!=48 or not witness:raise RuntimeError("INCOMPLETE_OR_UNIDENTIFIABLE")
    total=sum(c["edges"] for c in cases)
    return {"schema":"forge.acc69.u29.topology-semantic-identifiability.v1",
        "identity":source,"protocol":{"sizes":list(SIZES),"assignments":16,
            "source":"public deterministic SHA256 role assignments",
            "train":"other 15 assignments, no heldout-label access",
            "topology_only":"global label frequency","control":"edge-index conditional majority",
            "oracle":"not used or scored","actual_language_model":False},
        "cases":cases,"contradictions":witness,
        "aggregate":{"tested_graph_assignments":48,"tested_edges":total,
            "topology_only_accuracy":sum(c["topology_only_correct"] for c in cases)/total,
            "per_edge_control_accuracy":sum(c["per_edge_control_correct"] for c in cases)/total,
            "topology_only_mean_nll":sum(c["topology_only_nll"]*c["edges"] for c in cases)/total},
        "classification":{"universal_topology_only_semantics":"U29_TOPOLOGY_ONLY_UNIVERSAL_SEMANTICS_NO_GO",
            "actual_semantic_model_advantage":"UNVERIFIED",
            "pretrained_LLM_speed":"UNVERIFIED",
            "scientific_first_use":"NOT_ESTABLISHED","scientific_acceptance":"NOT_GRANTED",
            "production_admission":"NOT_GRANTED"},
        "limits":"Independent arbitrary labels cannot be inferred from identical unlabeled graph structure. No statistical semantic learning beyond synthetic source or original model performance tested."}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--json",type=Path,required=True);args=p.parse_args()
    v=study();args.json.parent.mkdir(parents=True,exist_ok=True)
    args.json.write_bytes((json.dumps(v,sort_keys=True,indent=2)+"\n").encode())
    print("ACC69_U29_EXACT_MATRIX=PASS")
    print("ACC69_U29_VERDICT="+v["classification"]["universal_topology_only_semantics"])
