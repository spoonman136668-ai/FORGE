// forge-shadow-recover is a fully INACTIVE, two-lane, externally witnessed
// recovery evidence pipeline. It cannot execute a repair or scientific work.
package main
import(
 "bytes"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "time"

 "github.com/spoonman136668-ai/forge/lanereview"
 "github.com/spoonman136668-ai/forge/lanewitness"
 "github.com/spoonman136668-ai/forge/shadowpipeline"
)
const inputSchema="forge.shadow.pipeline-input.v1"
type witnessPin struct{
 Lane string `json:"lane"`
 ExistingLaneID string `json:"existing_lane_id"`
 ExistingQueueID string `json:"existing_queue_id"`
 SourceRepo string `json:"source_repo"`
 SourceCommitSHA string `json:"source_commit_sha"`
 OwnerID string `json:"owner_id"`
 OwnerEpoch uint64 `json:"owner_epoch"`
 JournalHeadSHA256 string `json:"journal_head_sha256"`
 MinimumObservationSequence uint64 `json:"minimum_observation_sequence"`
 PublicKeyHex string `json:"public_key_hex"`
}
type reviewerPin struct{
 Lane string `json:"lane"`
 PublicKeyHex string `json:"public_key_hex"`
 MinimumReviewSequence uint64 `json:"minimum_review_sequence"`
}
type input struct{
 Schema string `json:"schema"`
 WitnessPins []witnessPin `json:"witness_pins"`
 Witnesses []lanewitness.Signed `json:"witnesses"`
 ReviewerPins []reviewerPin `json:"reviewer_pins"`
 Reviews []lanereview.SignedFinding `json:"reviews"`
}
func loadRequest(path string,now uint64)(shadowpipeline.Request,error){
 var zero shadowpipeline.Request
 if path==""||!filepath.IsAbs(path)||now==0{return zero,shadowpipeline.ErrUnsafe}
 info,err:=os.Lstat(path)
 if err!=nil||!info.Mode().IsRegular()||info.Size()==0||info.Size()>256<<10{return zero,shadowpipeline.ErrUnsafe}
 raw,err:=os.ReadFile(path)
 if err!=nil||len(raw)>256<<10{return zero,shadowpipeline.ErrUnsafe}
 decoder:=json.NewDecoder(bytes.NewReader(raw));decoder.DisallowUnknownFields()
 var src input
 if err:=decoder.Decode(&src);err!=nil||src.Schema!=inputSchema{return zero,shadowpipeline.ErrUnsafe}
 var extra any
 if !errors.Is(decoder.Decode(&extra),io.EOF)||len(src.WitnessPins)!=2||len(src.ReviewerPins)!=2{return zero,shadowpipeline.ErrUnsafe}
 result:=shadowpipeline.Request{NowUnix:now,Witnesses:src.Witnesses,Reviews:src.Reviews}
 for _,p:=range src.WitnessPins{
  key,err:=hex.DecodeString(p.PublicKeyHex)
  if err!=nil||len(key)!=ed25519.PublicKeySize{return zero,shadowpipeline.ErrUnsafe}
  result.WitnessPins=append(result.WitnessPins,lanewitness.Pinned{
   Lane:p.Lane,ExistingLaneID:p.ExistingLaneID,ExistingQueueID:p.ExistingQueueID,
   SourceRepo:p.SourceRepo,SourceCommitSHA:p.SourceCommitSHA,OwnerID:p.OwnerID,
   OwnerEpoch:p.OwnerEpoch,JournalHeadSHA256:p.JournalHeadSHA256,
   MinimumObservationSequence:p.MinimumObservationSequence,PublicKey:ed25519.PublicKey(key),
  })
 }
 for _,p:=range src.ReviewerPins{
  key,err:=hex.DecodeString(p.PublicKeyHex)
  if err!=nil||len(key)!=ed25519.PublicKeySize{return zero,shadowpipeline.ErrUnsafe}
  result.ReviewerPins=append(result.ReviewerPins,lanereview.ReviewerPin{
   Lane:p.Lane,PublicKey:ed25519.PublicKey(key),MinimumReviewSequence:p.MinimumReviewSequence,
  })
 }
 return result,nil
}
func run(args []string,out io.Writer,now uint64)error{
 f:=flag.NewFlagSet("forge-shadow-recover",flag.ContinueOnError)
 f.SetOutput(io.Discard)
 requestPath:=f.String("request","","absolute path of externally pinned, signed evidence bundle")
 root:=f.String("root","","NEW immutable forge-shadow-recovery directory")
 verify:=f.Bool("verify",false,"read-only restart verification; no writes")
 if err:=f.Parse(args);err!=nil||f.NArg()!=0{return shadowpipeline.ErrUnsafe}
 req,err:=loadRequest(*requestPath,now);if err!=nil{return err}
 var report shadowpipeline.Report
 if *verify{
  report,err=shadowpipeline.Verify(*root,req.WitnessPins,req.ReviewerPins)
 }else{
  report,err=shadowpipeline.Run(*root,req)
 }
 if err!=nil{return err}
 return json.NewEncoder(out).Encode(report)
}
func main(){
 t:=time.Now().Unix()
 if t<=0 {fmt.Fprintln(os.Stderr,"FORGE_SHADOW_RECOVERY_UNAVAILABLE");os.Exit(1)}
 if err:=run(os.Args[1:],os.Stdout,uint64(t));err!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_SHADOW_RECOVERY_FAIL_CLOSED")
  os.Exit(1)
 }
}
