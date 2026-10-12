package attemptjournal
import("os";"path/filepath";"strings";"testing")
func fixture()Record{return Record{Schema:Schema,Lane:"Wingless",ExperimentID:"original",OriginalRunID:"original_1",FrozenSHA256:strings.Repeat("a",64),IntentSHA256:strings.Repeat("b",64),OwnerEpoch:5,WorkerID:"worker",ReceiptSHA256:strings.Repeat("c",64),State:"ORIGINAL_RISK_RECORDED"}}
func TestWriteOnceNoOriginalReplay(t *testing.T){
 dir:=t.TempDir();r:=fixture()
 if err:=WriteOnce(dir,r);err!=nil{t.Fatal(err)}
 if _,err:=Read(dir,r);err!=nil{t.Fatal(err)}
 if err:=WriteOnce(dir,r);err==nil{t.Fatal("duplicate original attempt admitted")}
 old:=r;r.OwnerEpoch++
 if _,err:=Read(dir,r);err==nil{t.Fatal("stale ownership accepted")}
 r=old;r.Lane="Yggdrasil"
 if _,err:=Read(dir,r);err==nil{t.Fatal("cross-lane original accepted")}
}
func TestTornRecordAndUnprovisionedRootFailClosed(t *testing.T){
 dir:=t.TempDir();r:=fixture()
 if err:=WriteOnce(filepath.Join(dir,"absent"),r);err==nil{t.Fatal("provisioned missing directory")}
 if err:=WriteOnce(dir,r);err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(filepath.Join(dir,filename(r)),[]byte("{torn"),0600);err!=nil{t.Fatal(err)}
 if _,err:=Read(dir,r);err==nil{t.Fatal("torn durable original accepted")}
 if err:=WriteOnce(dir,r);err==nil{t.Fatal("torn original overwritten")}
}
