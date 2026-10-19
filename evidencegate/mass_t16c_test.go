package evidencegate
import (
 "crypto/sha256"
 "encoding/hex"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func TestMassT16CSourceHashIsNotScientificAcceptance(t *testing.T){
 root:=t.TempDir();p:=filepath.Join(root,"synthetic-original")
 raw:=[]byte("T16C NONPRODUCTION original fixture only; no actual source birth\n")
 if err:=os.WriteFile(p,raw,0600);err!=nil{t.Fatal(err)}
 digest:=sha256.Sum256(raw)
 m:=Manifest{Lane:"MassResearch",ExperimentID:"mass-t16c-synthetic-only",
  FrozenSHA256:strings.Repeat("a",64),OriginalRunID:"mass-fixture-not-original",
  OriginalSHA256:hex.EncodeToString(digest[:]),OriginalBytes:int64(len(raw)),
  Classification:"INCONCLUSIVE"}
 if err:=VerifyOriginal(m,p);err!=nil{t.Fatal(err)}
 m.OriginalSHA256=strings.Repeat("0",64)
 if err:=VerifyOriginal(m,p);err==nil{t.Fatal("wrong Mass source SHA accepted")}
 m.OriginalSHA256=hex.EncodeToString(digest[:]);m.Classification="ACCEPTED"
 if err:=VerifyOriginal(m,p);err==nil{t.Fatal("unsigned scientific acceptance category accepted")}
 m.Classification="INVALID";m.Lane="KTRADE"
 if err:=VerifyOriginal(m,p);err==nil{t.Fatal("KTRADE source conflated with Mass research")}
}
