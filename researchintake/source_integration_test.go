package researchintake

import (
 "encoding/json"
 "os"
 "path/filepath"
 "testing"
)

// This is a real-source offline integration check. Repository fixtures contain
// only publicly observable PR identities, never sealed cohort or result bytes.
func TestBundledCrossLaneSnapshotsCompose(t *testing.T){
 root:=filepath.Join("..","reference","research-intake")
 initial,err:=os.ReadFile(filepath.Join(root,"20261014-initial-crosslane-pr-snapshot.json"));if err!=nil{t.Fatal(err)}
 backfill,err:=os.ReadFile(filepath.Join(root,"20261014-recent-200-pr-source-backfill.json"));if err!=nil{t.Fatal(err)}
 p,err:=Ingest(initial,nil);if err!=nil{t.Fatalf("initial snapshot: %v",err)}
 if p.TotalRevisions!=24||p.WinglessRevisions!=12||p.YggdrasilRevisions!=12{t.Fatalf("unexpected initial lane counts: %+v",p)}
 frozen,_:=json.Marshal(p)
 q,err:=Ingest(backfill,frozen);if err!=nil{t.Fatalf("real backfill rejected: %v",err)}
 if q.TotalRevisions<200||q.WinglessRevisions<100||q.YggdrasilRevisions<100||q.TotalRevisions>224{t.Fatal("missing historical records")}
 if q.ScientificAccepted||q.FirstUseCleared||q.HistoricalCompletenessVerified||q.NewScientificOriginalsExecuted||q.AuthorityMutated{t.Fatal("historical metadata inflated to authority")}
 observed:=map[string]bool{}
 for _,r:=range q.Revisions{if r.PR==191&&r.Lane=="Wingless"||r.PR==185&&r.Lane=="Yggdrasil"{observed[r.Lane]=true}}
 if !observed["Wingless"]||!observed["Yggdrasil"]{t.Fatal("latest original scientific source missing")}
 stable,_:=json.Marshal(q)
 same,err:=Ingest(backfill,stable);if err!=nil||string(stable)!=string(mustJSON(same)){t.Fatal("backfill replay is not idempotent",err)}
}
func mustJSON(v any)[]byte{b,_:=json.Marshal(v);return b}
