package cyclecontroller

import (
 "context"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/workerreconcile"
)

func TestControllerReverifiesOriginalSignatureAfterChildExited(t *testing.T){
 source:=filepath.Join(t.TempDir(),"forge-synthetic-controller")
 _,worker,sha:=runTwo(t,source)
 for _,kind:=range []string{"start signature","terminal signature","declared signer","attempt first use","deleted signer"}{
  t.Run(kind,func(t *testing.T){
   root:=filepath.Join(t.TempDir(),"forge-synthetic-controller")
   copySyntheticSnapshot(t,source,root)
   lane:=filepath.Join(root,"generation-0002","forge-synthetic-processes","wingless")
   folder:=filepath.Join(lane,"forge-synthetic-worker")
   files,err:=os.ReadDir(folder);if err!=nil{t.Fatal(err)}
   var startPath,endPath,attemptPath string
   for _,f:=range files{
    n:=f.Name()
    switch {
    case strings.HasPrefix(n,"start-"):startPath=filepath.Join(folder,n)
    case strings.HasPrefix(n,"terminal-"):endPath=filepath.Join(folder,n)
    default:attemptPath=filepath.Join(folder,n)
    }
   }
   if startPath==""||endPath==""||attemptPath==""{t.Fatal("missing child receipts")}
   if kind=="deleted signer"{
    if err:=os.Remove(filepath.Join(lane,"worker-observation.json"));err!=nil{t.Fatal(err)}
   }else if kind=="declared signer"{
    p:=filepath.Join(lane,"worker-observation.json")
    var witness workerReply
    if _,err:=readCanonical(p,&witness);err!=nil{t.Fatal(err)}
    witness.PublicKeyHex=strings.Repeat("f",64)
    b,_:=canonical(witness)
    if err:=os.WriteFile(p,b,0600);err!=nil{t.Fatal(err)}
   }else if kind=="attempt first use"{
    data,err:=os.ReadFile(attemptPath);if err!=nil{t.Fatal(err)}
    data=[]byte(strings.Replace(string(data),"ORIGINAL_RISK_RECORDED","TERMINAL_RECONCILED",1))
    if err:=os.WriteFile(attemptPath,data,0600);err!=nil{t.Fatal(err)}
   }else{
    path:=startPath
    if kind=="terminal signature"{path=endPath}
    var record workerreconcile.Signed
    if _,err:=readCanonical(path,&record);err!=nil{t.Fatal(err)}
    record.SignatureHex=strings.Repeat("0",128)
    data,_:=canonical(record)
    if err:=os.WriteFile(path,data,0600);err!=nil{t.Fatal(err)}
   }
   // Independently verifying the STARTED/TERMINAL signatures must reject
   // even though filenames and byte counts appear to be complete.
   base:=filepath.Join(root,"generation-0002","forge-synthetic-processes","wingless","forge-synthetic-worker")
   if _,err:=verifyNativeReceipts(base,"Wingless");!errors.Is(err,ErrQuarantine){
    t.Fatalf("unsafe worker identity accepted: %v",err)
   }
   if _,err:=Run(context.Background(),worker,sha,strings.Repeat("e",64),root,2,2);
    !errors.Is(err,ErrQuarantine){t.Fatalf("tampered completed custody resumed: %v",err)}
   if _,err:=os.Lstat(filepath.Join(root,"controller.active"));err!=nil{
    t.Fatal("missing fail-closed sticky lock",err)
   }
  })
 }
}
func TestControllerIndependentWorkerWitnessAndSignedReceipts(t *testing.T){
 source:=filepath.Join(t.TempDir(),"forge-synthetic-controller")
 _,_,_ = runTwo(t,source)
 for _,lane:=range []string{"wingless","yggdrasil"}{
  dir:=filepath.Join(source,"generation-0001","forge-synthetic-processes",lane)
  raw,err:=os.ReadFile(filepath.Join(dir,"worker-observation.json"))
  if err!=nil{t.Fatal(err)}
  var reply workerReply
  if err:=json.Unmarshal(raw,&reply);err!=nil||reply.PublicKeyHex==""{
   t.Fatal("native worker public witness missing",err)
  }
  if _,err:=verifyNativeReceipts(filepath.Join(dir,"forge-synthetic-worker"),strings.ToUpper(lane[:1])+lane[1:]);err!=nil{
   t.Fatalf("real child signature did not verify from independent journal readback: %v",err)
  }
 }
}
