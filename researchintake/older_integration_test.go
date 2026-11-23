package researchintake

import (
 "encoding/json"
 "os"
 "path/filepath"
 "testing"
)
func TestOlderSourceBackfill(t *testing.T) {
 dir:=filepath.Join("..","reference","research-intake")
 paths:=[]string{"20261014-initial-crosslane-pr-snapshot.json","20261014-recent-200-pr-source-backfill.json","20261014-older-180-pr-source-backfill.json"}
 var prior []byte
 for _,name:=range paths {
  b,err:=os.ReadFile(filepath.Join(dir,name));if err!=nil{t.Fatal(err)}
  result,err:=Ingest(b,prior);if err!=nil{t.Fatalf("%s: %v",name,err)}
  if result.ScientificAccepted||result.FirstUseCleared||result.AuthorityMutated||result.HistoricalCompletenessVerified{t.Fatal("source metadata became authority")}
  prior,err=json.Marshal(result);if err!=nil{t.Fatal(err)}
 }
 var report Report;if err:=json.Unmarshal(prior,&report);err!=nil{t.Fatal(err)}
 if report.WinglessRevisions!=192||report.YggdrasilRevisions!=186{t.Fatalf("older history missing: wingless=%d yggdrasil=%d",report.WinglessRevisions,report.YggdrasilRevisions)}
 stable,err:=os.ReadFile(filepath.Join(dir,paths[2]));if err!=nil{t.Fatal(err)}
 again,err:=Ingest(stable,prior);if err!=nil{t.Fatal(err)}
 same,_:=json.Marshal(again)
 if string(same)!=string(prior){t.Fatal("history replay not stable")}
}
