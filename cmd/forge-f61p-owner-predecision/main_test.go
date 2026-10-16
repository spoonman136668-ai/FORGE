package main

import (
 "bytes"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/optimizerbridge"
)
func testF61PArgs(t *testing.T,root string)([]string,string){
 t.Helper()
 f,err:=optimizerbridge.FreezeF58();if err!=nil{t.Fatal(err)}
 ready,err:=optimizerbridge.ReadinessF58(f);if err!=nil{t.Fatal(err)}
 n:=optimizerbridge.F59PolicyNomination{
  Lane:"Wingless",FrozenControlRegistrySHA256:ready.FrozenControlRegistrySHA256,
  DreamPolicySHA256:strings.Repeat("1",64),DreamOptimizerLineageSHA256:strings.Repeat("2",64),
  DreamTrainingHistorySHA256:strings.Repeat("3",64),DreamValidationHistorySHA256:strings.Repeat("4",64),
  ParetoPolicySHA256:strings.Repeat("5",64),ParetoFrozenPortfolioSHA256:strings.Repeat("6",64),
  ParetoLineageSHA256:strings.Repeat("7",64),OwnerPreregistrationSHA256:strings.Repeat("8",64),
  PredecisionOwnerSourceSHA:strings.Repeat("a",40),
  IndependentExternalTrustReceiptSHA256:strings.Repeat("9",64),
 }
 path:=filepath.Join(root,"synthetic-nomination.json")
 raw,_:=json.Marshal(n)
 if err:=os.WriteFile(path,raw,0600);err!=nil{t.Fatal(err)}
 out:=filepath.Join(root,"unwitnessed.json")
 args:=[]string{"--nomination",path,
  "--public-slate-sha256",strings.Repeat("d",64),
  "--public-family-sha256",strings.Repeat("e",64),
  "--budget-commitment-sha256",strings.Repeat("f",64),
  "--out",out}
 return args,out
}
func TestF61PLocalUtilityDoesNotClaimIndependentlyWitnessedOwnerApproval(t *testing.T){
 root:=t.TempDir()
 args,out:=testF61PArgs(t,root)
 if err:=run(args);err!=nil{t.Fatal(err)}
 b,err:=os.ReadFile(out);if err!=nil{t.Fatal(err)}
 var a optimizerbridge.F61PilotAssignment
 if err:=json.Unmarshal(b,&a);err!=nil{t.Fatal(err)}
 if a.GenuineScientificOriginalAuthorized||a.AtomicFirstUseClaimConsumed||
  a.ExternallyWitnessedPredecisionRegistration||a.PolicyAcceptedOrPromoted||
  a.LoggedPropensityNumerator!=1||a.LoggedPropensityDenominator!=6||
  !strings.Contains(a.Status,"UNWITNESSED"){
  t.Fatalf("fake owner authority: %+v",a)
 }
 if err:=run(args);!errors.Is(err,errNotAuthorized){t.Fatal("repeated local output accepted")}
 after,_:=os.ReadFile(out)
 if !bytes.Equal(b,after){t.Fatal("existing file overwritten")}
}
func TestF61PLocalUtilityFailsClosedWithoutAuthenticNomination(t *testing.T){
 root:=t.TempDir()
 args,out:=testF61PArgs(t,root)
 cases:=[][]string{
  nil,
  {"--nomination","relative.json","--out",out},
  {"--nomination",out,"--out",out},
 }
 for _,a:=range cases{if err:=run(a);!errors.Is(err,errNotAuthorized){t.Fatalf("invalid invocation accepted: %v",a)}}
 raw,err:=os.ReadFile(args[1]);if err!=nil{t.Fatal(err)}
 link:=filepath.Join(root,"nomination-link.json")
 if err:=os.Symlink(args[1],link);err!=nil{t.Fatal(err)}
 altered:=append([]string(nil),args...)
 altered[1]=link
 if err:=run(altered);!errors.Is(err,errNotAuthorized){t.Fatal("symlink accepted")}
 if err:=os.WriteFile(args[1],append(raw,[]byte("\n{}")...),0600);err!=nil{t.Fatal(err)}
 if err:=run(args);!errors.Is(err,errNotAuthorized){t.Fatal("trailing unsigned nomination accepted")}
 if _,err:=os.Stat(out);!os.IsNotExist(err){t.Fatalf("unsafe output created: %v",err)}
}
