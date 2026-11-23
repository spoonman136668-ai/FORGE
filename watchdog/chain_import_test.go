package watchdog

import (
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func TestIncidentArchiveRoundTripAndCorruption(t *testing.T){
 dir:=t.TempDir()
 a:=Incident{Lane:"Wingless",OriginalExperimentID:"original_w",JournalHeadSHA256:strings.Repeat("a",64),OwnerEpoch:9,Action:DiagnoseOrchestration}
 chain,err:=AppendIncidentChain(nil,a,zeroHead);if err!=nil{t.Fatal(err)}
 if err:=ExportIncidentChain(dir,chain);err!=nil{t.Fatal(err)}
 restored,head,err:=ImportIncidentChain(dir)
 if err!=nil||len(restored)!=1||head!=chain[0].RecordSHA256{t.Fatal(err,head)}
 if err:=ExportIncidentChain(dir,chain);err==nil{t.Fatal("archive overwritten")}
 path:=filepath.Join(dir,"shadow-chain.v1.json")
 content,err:=os.ReadFile(path);if err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(path,append(content,[]byte("{}")...),0600);err!=nil{t.Fatal(err)}
 if _,_,err:=ImportIncidentChain(dir);err==nil{t.Fatal("trailing records accepted")}
}
func TestIncidentArchiveRejectsMissingAndNil(t *testing.T){
 if _,_,err:=ImportIncidentChain(t.TempDir());err==nil{t.Fatal("missing archive accepted")}
}
