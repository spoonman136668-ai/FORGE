// Read-only F5 authenticated cohort intake. Does NOT start a worker,
// freeze a prospective original, mint first-use, or confer science authority.
// All witness identity pins must come from an independent channel.
package main

import (
 "bytes"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"

 "github.com/spoonman136668-ai/forge/eligibility"
 "github.com/spoonman136668-ai/forge/f5custody"
)

const limit=1<<20
func canonicalRead[T any](path string)(T,error){
 var zero T
 if path==""{return zero,errors.New("MISSING_INPUT")}
 info,err:=os.Lstat(path)
 if err!=nil||!info.Mode().IsRegular()||info.Size()<2||info.Size()>limit{
  return zero,errors.New("INVALID_INPUT_FILE")
 }
 raw,err:=os.ReadFile(path)
 if err!=nil||len(raw)>limit{return zero,errors.New("INVALID_INPUT")}
 dec:=json.NewDecoder(bytes.NewReader(raw))
 dec.DisallowUnknownFields()
 var v T
 if err=dec.Decode(&v);err!=nil{return zero,errors.New("UNTRUSTED_JSON")}
 var extra any
 if err=dec.Decode(&extra);!errors.Is(err,io.EOF){return zero,errors.New("TRAILING_CONTENT")}
 canon,err:=json.Marshal(v)
 if err!=nil||!bytes.Equal(raw,append(canon,'\n')){
  return zero,errors.New("NOT_CANONICAL_OR_DUPLICATE_KEYS")
 }
 return v,nil
}
func audit(candidatePath,bundlePath string,pins f5custody.Pins)(f5custody.Report,error){
 c,err:=canonicalRead[eligibility.Frozen](candidatePath)
 if err!=nil{return f5custody.Report{Disposition:"BLOCKED",Reason:"CANDIDATE_NOT_FROZEN"},err}
 b,err:=canonicalRead[f5custody.Signed](bundlePath)
 if err!=nil{return f5custody.Report{Disposition:"BLOCKED",Reason:"SIGNED_ALL_LANE_BUNDLE_NOT_AVAILABLE"},err}
 return f5custody.Inspect(b,pins,c)
}
func main(){
 var candidate,bundle,pub,ledger string
 var revision,generation,winglessFloor,yggdrasilFloor uint64
 flag.StringVar(&candidate,"candidate","","externally frozen candidate JSON")
 flag.StringVar(&bundle,"bundle","","signed complete all-lane seed custody JSON")
 flag.StringVar(&pub,"custodian-public-key","","independent external Ed25519 public key (hex)")
 flag.StringVar(&ledger,"ledger-pin","","independently pinned complete ledger SHA256")
 flag.Uint64Var(&revision,"minimum-revision",0,"externally authenticated monotonic revision floor")
 flag.Uint64Var(&generation,"ledger-generation",0,"externally authenticated ledger generation")
 flag.Uint64Var(&winglessFloor,"wingless-high-water",0,"independently pinned Wingless high-water floor")
 flag.Uint64Var(&yggdrasilFloor,"yggdrasil-high-water",0,"independently pinned Yggdrasil high-water floor")
 flag.Parse()
 report,err:=audit(candidate,bundle,f5custody.Pins{
  CustodianPublicKeyHex:pub,LedgerSHA256:ledger,
  MinRevision:revision,ExpectedLedgerGeneration:generation,
  WinglessMinHighWater:winglessFloor,YggdrasilMinHighWater:yggdrasilFloor,
 })
 if err!=nil{
  fmt.Println("F5_CUSTODY=BLOCKED")
  fmt.Println("F5_SCIENTIFIC_EXECUTION=DENIED")
  fmt.Println("F5_FIRST_USE_CLAIMS=ZERO")
  os.Exit(2)
 }
 // Print only a non-authorizing classification. Never expose the raw
 // seed inventory, signer or saved candidate credentials in CI logs.
 fmt.Println("F5_CUSTODY="+report.Disposition)
 fmt.Println("F5_SCIENTIFIC_EXECUTION=DENIED")
 fmt.Println("F5_FIRST_USE_CLAIMS=ZERO")
}
