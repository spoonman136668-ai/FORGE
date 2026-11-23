// forge-dreamrsi evaluates independently pinned, attestor-signed randomized
// FORGE decision histories. It cannot schedule, start or admit experiments.
package main

import (
 "bytes"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/dreamrsi"
)
func readJSON(path string,v any)error{
 if !filepath.IsAbs(path){return dreamrsi.ErrEvidence}
 info,err:=os.Lstat(path)
 if err!=nil||!info.Mode().IsRegular()||info.Size()==0||info.Size()>8<<20{
  return dreamrsi.ErrEvidence
 }
 b,err:=os.ReadFile(path);if err!=nil{return dreamrsi.ErrEvidence}
 d:=json.NewDecoder(bytes.NewReader(b));d.DisallowUnknownFields()
 if err=d.Decode(v);err!=nil{return dreamrsi.ErrEvidence}
 var extra any
 if err=d.Decode(&extra);err!=io.EOF{return dreamrsi.ErrEvidence}
 return nil
}
func writeJSONOnce(path string,v any)error{
 if !filepath.IsAbs(path){return dreamrsi.ErrFrozen}
 b,err:=json.MarshalIndent(v,"","  ")
 if err!=nil||len(b)>8<<20{return dreamrsi.ErrFrozen}
 f,err:=os.OpenFile(path,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return err}
 if _,err=f.Write(append(b,'\n'));err!=nil{_ = f.Close();return err}
 if err=f.Sync();err!=nil{_ = f.Close();return err}
 return f.Close()
}
func execute(trainFile,validationFile,pubKey,trainSHA,validationSHA,specFile,specSHA,lineageDir,resultFile string)error{
 var a,b dreamrsi.Envelope
 var spec dreamrsi.FrozenSpec
 if err:=readJSON(trainFile,&a);err!=nil{return err}
 if err:=readJSON(validationFile,&b);err!=nil{return err}
 if err:=readJSON(specFile,&spec);err!=nil{return err}
 train,err:=dreamrsi.VerifyEnvelope(a,dreamrsi.TrustPin{
  ExpectedHistorySHA256:trainSHA,IndependentEd25519PublicKeyHex:pubKey,
 })
 if err!=nil{return err}
 validation,err:=dreamrsi.VerifyEnvelope(b,dreamrsi.TrustPin{
  ExpectedHistorySHA256:validationSHA,IndependentEd25519PublicKeyHex:pubKey,
 })
 if err!=nil{return err}
 result,err:=dreamrsi.Optimize(train,validation,spec,specSHA)
 if err!=nil{return err}
 if err=dreamrsi.ValidateOptimization(result);err!=nil{return err}
 if lineageDir!=""{
  if err=dreamrsi.PersistLineage(lineageDir,result.Records,result.Lane);err!=nil{return err}
 }
 if resultFile==""{return errors.New("FORGE_DREAMRSI_EXPLICIT_OUTPUT_PATH_REQUIRED")}
 if err=writeJSONOnce(resultFile,result);err!=nil{return err}
 // The visible report is a policy proposal, not evidence of improvement.
 fmt.Printf("FORGE_DREAMRSI_READONLY_OPTIMIZATION=PASS lane=%s policies=%d evaluations=%d replay_decisions=%d candidate=%s prospective_only=%t improvement_claim=false dispatch=false\n",
  result.Lane,len(result.Records),result.EvaluationsUsed,result.DecisionReplaysUsed,
  result.SelectedPolicySHA256,result.QualifiedForProspectiveTest)
 return nil
}
func main(){
 train:=flag.String("train","","absolute path to signed training history")
 validation:=flag.String("validation","","absolute path to signed validation history")
 pub:=flag.String("attestor-public-key","","independently trusted Ed25519 public key hex")
 ts:=flag.String("train-sha","","externally pinned training history SHA256")
 vs:=flag.String("validation-sha","","externally pinned validation history SHA256")
 spec:=flag.String("spec","","absolute path to frozen optimization spec")
 ss:=flag.String("spec-sha","","independently pinned frozen optimization spec SHA256")
 lineage:=flag.String("lineage-dir","","optional exclusive local history journal directory")
 output:=flag.String("output","","new immutable report filename")
 flag.Parse()
 if flag.NArg()!=0{fmt.Fprintln(os.Stderr,"FORGE_DREAMRSI_ARGS_INVALID");os.Exit(2)}
 if err:=execute(*train,*validation,*pub,*ts,*vs,*spec,*ss,*lineage,*output);err!=nil{
  // No evidence bytes, private paths, or credential details in public logs.
  fmt.Fprintln(os.Stderr,"FORGE_DREAMRSI_FAIL_CLOSED")
  os.Exit(2)
 }
}
