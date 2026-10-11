// forge-hosted-wake observes signed FSA pre-run intent after GitHub assigns
// a run ID. It cannot issue an intent/lease, dispatch, or execute science.
package main
import (
 "bytes"
 "encoding/json"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/hostedgrant"
 "github.com/spoonman136668-ai/forge/hostedwake"
)
func readJSON(path string,target any)error{
 if !filepath.IsAbs(path){return hostedwake.ErrDenied}
 info,err:=os.Lstat(path)
 if err!=nil||!info.Mode().IsRegular()||info.Size()<1||info.Size()>16384{return hostedwake.ErrDenied}
 b,err:=os.ReadFile(path)
 if err!=nil{return hostedwake.ErrDenied}
 d:=json.NewDecoder(bytes.NewReader(b))
 d.DisallowUnknownFields()
 if d.Decode(target)!=nil{return hostedwake.ErrDenied}
 var extra any
 if d.Decode(&extra)!=io.EOF{return hostedwake.ErrDenied}
 return nil
}
func run(args []string)error{
 f:=flag.NewFlagSet("wake",flag.ContinueOnError)
 intentPath:=f.String("intent","","externally signed FSA pre-run wake intent")
 intentSHA:=f.String("intent-sha","","external prewake SHA256 pin")
 intentKey:=f.String("intent-public-key","","independent FSA prewake signing public key")
 leaseKey:=f.String("lease-public-key","","separate independent FSA dispatch-lease signer")
 headKey:=f.String("head-public-key","","separate FSA archive-head public key")
 leasePath:=f.String("lease","","optional later signed FSA dispatch lease")
 leaseSHA:=f.String("lease-sha","","optional external dispatch lease SHA")
 grantReviewPath:=f.String("grant-review","","optional R9 verified grant review")
 output:=f.String("output","","exclusive-create non-executing observation")
 if f.Parse(args)!=nil||f.NArg()!=0{return hostedwake.ErrDenied}
 var signed hostedwake.SignedIntent
 if err:=readJSON(*intentPath,&signed);err!=nil{return err}
 ctx:=hostedwake.Context{
  Repository:os.Getenv("GITHUB_REPOSITORY"),
  Workflow:os.Getenv("FORGE_FSA_WORKFLOW"),
  SourceSHA:os.Getenv("GITHUB_SHA"),
  TreeSHA:os.Getenv("FORGE_SOURCE_TREE"),
  Lane:os.Getenv("FORGE_SCIENCE_LANE"),
  RunID:os.Getenv("GITHUB_RUN_ID"),
 }
 if os.Getenv("GITHUB_RUN_ATTEMPT")=="1"{ctx.Attempt=1}
 pin:=hostedwake.Pin{IntentSHA256:*intentSHA,
  IntentKeyHex:*intentKey,LeaseKeyHex:*leaseKey,
  FSAHeadKeyHex:*headKey}
 claim,observation,err:=hostedwake.ObserveWake(signed,pin,ctx)
 if err!=nil{return err}
 if *leasePath!=""||*leaseSHA!=""||*grantReviewPath!=""{
  if *leasePath==""||*leaseSHA==""||*grantReviewPath==""{return hostedwake.ErrDenied}
  var lease hostedwake.SignedLease
  if err:=readJSON(*leasePath,&lease);err!=nil{return err}
  var verifiedGrant hostedgrant.Review
  if err:=readJSON(*grantReviewPath,&verifiedGrant);err!=nil{return err}
  observation,err=hostedwake.VerifyLease(
   claim,observation,lease,*leaseSHA,pin,verifiedGrant)
  if err!=nil{return err}
 }
 if !filepath.IsAbs(*output){return hostedwake.ErrDenied}
 data,err:=json.MarshalIndent(observation,"","  ")
 if err!=nil||len(data)>16384{return hostedwake.ErrDenied}
 file,err:=os.OpenFile(*output,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return hostedwake.ErrDenied}
 if _,err=file.Write(append(data,'\n'));err!=nil{_ =file.Close();return hostedwake.ErrDenied}
 if file.Sync()!=nil{_ =file.Close();return hostedwake.ErrDenied}
 if file.Close()!=nil{return hostedwake.ErrDenied}
 fmt.Println("FORGE_HOSTED_PREWAKE=CRYPTOGRAPHICALLY_REVIEWED")
 fmt.Println("FORGE_SCIENTIFIC_EXECUTION=DISABLED")
 return nil
}
func main(){
 if err:=run(os.Args[1:]);err!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_PREWAKE_DENIED_NO_INDEPENDENT_FSA_INTENT")
  os.Exit(2)
 }
}
