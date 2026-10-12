package evidencegate
import(
 "crypto/sha256"
 "encoding/hex"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func TestPreserveNegativeAndRejectTamperedOriginal(t *testing.T){
 root:=t.TempDir()
 path:=filepath.Join(root,"original.bin")
 original:=[]byte("NEGATIVE SCIENTIFIC RESULT: original bytes unchanged")
 if err:=os.WriteFile(path,original,0600);err!=nil{t.Fatal(err)}
 d:=sha256.Sum256(original)
 m:=Manifest{Lane:"Yggdrasil",ExperimentID:"existing_y_trial",
  FrozenSHA256:strings.Repeat("a",64),OriginalRunID:"legacy_original_17",
  OriginalSHA256:hex.EncodeToString(d[:]),OriginalBytes:int64(len(original)),
  Classification:"NEGATIVE"}
 if err:=VerifyOriginal(m,path);err!=nil{t.Fatal(err)}
 m.Classification="INCONCLUSIVE";if err:=VerifyOriginal(m,path);err!=nil{t.Fatal(err)}
 m.Classification="SUPPORTED";if err:=VerifyOriginal(m,path);err==nil{t.Fatal("unrecognized classification accepted")}
 m.Classification="NEGATIVE"
 if err:=os.WriteFile(path,[]byte("altered"),0600);err!=nil{t.Fatal(err)}
 if err:=VerifyOriginal(m,path);err==nil{t.Fatal("tampered raw original accepted")}
}
func TestEmptyAndOversizeDenied(t *testing.T){
 m:=Manifest{Lane:"Wingless",ExperimentID:"existing_w",FrozenSHA256:strings.Repeat("b",64),
  OriginalRunID:"prior",OriginalSHA256:strings.Repeat("c",64),OriginalBytes:MaxOriginalBytes+1,Classification:"INVALID"}
 if err:=VerifyOriginal(m,"none");err==nil{t.Fatal("oversize admitted")}
 m.OriginalBytes=0
 if err:=VerifyOriginal(m,"none");err==nil{t.Fatal("empty admitted")}
}
