package shadowpipeline

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/lanereview"
 "github.com/spoonman136668-ai/forge/lanewitness"
 "github.com/spoonman136668-ai/forge/watchdog"
)

const claimDomain="FORGE-EXISTING-LANE-WITNESS-V1\n"
const reviewDomain="FORGE-EXISTING-LANE-FAILURE-REVIEW-V1\n"
func signClaim(t *testing.T,c lanewitness.Claim,key ed25519.PrivateKey)lanewitness.Signed{
 t.Helper();raw,err:=json.Marshal(c);if err!=nil{t.Fatal(err)}
 sig:=ed25519.Sign(key,append([]byte(claimDomain),raw...))
 return lanewitness.Signed{Claim:c,SignatureHex:hex.EncodeToString(sig)}
}
func signReview(t *testing.T,r lanereview.Finding,key ed25519.PrivateKey)lanereview.SignedFinding{
 t.Helper();raw,err:=json.Marshal(r);if err!=nil{t.Fatal(err)}
 sig:=ed25519.Sign(key,append([]byte(reviewDomain),raw...))
 return lanereview.SignedFinding{Finding:r,SignatureHex:hex.EncodeToString(sig)}
}
func fixture(t *testing.T)Request{
 t.Helper()
 req:=Request{NowUnix:1301}
 reviewerKeys:=map[string]ed25519.PrivateKey{}
 for i,lane:=range []string{"Wingless","Yggdrasil"}{
  wseed:=sha256.Sum256([]byte("TEST ONLY watcher "+lane))
  rseed:=sha256.Sum256([]byte("TEST ONLY independent review "+lane))
  witnessKey:=ed25519.NewKeyFromSeed(wseed[:])
  reviewKey:=ed25519.NewKeyFromSeed(rseed[:]);reviewerKeys[lane]=reviewKey
  pin:=lanewitness.Pinned{Lane:lane,ExistingLaneID:"original-"+lane,
   ExistingQueueID:"old-queue-"+lane,
   SourceRepo:"spoonman136668-ai/"+lane,
   SourceCommitSHA:strings.Repeat(string(rune('a'+i)),40),
   OwnerID:"existing-ckb-authority",OwnerEpoch:21,
   JournalHeadSHA256:strings.Repeat(string(rune('c'+i)),64),
   MinimumObservationSequence:9,PublicKey:witnessKey.Public().(ed25519.PublicKey)}
  req.WitnessPins=append(req.WitnessPins,pin)
  req.ReviewerPins=append(req.ReviewerPins,lanereview.ReviewerPin{
   Lane:lane,PublicKey:reviewKey.Public().(ed25519.PublicKey),
   MinimumReviewSequence:8,
  })
  claim:=lanewitness.Claim{
   Schema:lanewitness.Schema,ExistingLaneID:pin.ExistingLaneID,
   ExistingQueueID:pin.ExistingQueueID,SourceRepo:pin.SourceRepo,
   SourceCommitSHA:pin.SourceCommitSHA,OwnerID:pin.OwnerID,
   ObservationSequence:9,ObservedAtUnix:1300,
   Observation:watchdog.Observation{Lane:lane,OriginalExperimentID:"original-"+lane,
    JournalHeadSHA256:pin.JournalHeadSHA256,OwnerEpoch:pin.OwnerEpoch,
    Phase:watchdog.Orchestration,LastProgressUnix:900,FirstUseRisk:i==1},
  }
  req.Witnesses=append(req.Witnesses,signClaim(t,claim,witnessKey))
 }
 assessed,err:=lanewitness.AssessPair(req.NowUnix,req.Witnesses,req.WitnessPins)
 if err!=nil{t.Fatal(err)}
 for index,incident:=range assessed.Incidents{
  kind:=watchdog.FailureQualification
  if incident.Lane=="Yggdrasil"{kind=watchdog.FailureOriginalUnknown}
  finding:=lanereview.Finding{Schema:lanereview.Schema,Lane:incident.Lane,
   IncidentKey:watchdog.IncidentKey(incident),ObservationSHA256:assessed.Proofs[index].ObservationSHA256,
   Failure:kind,EvidenceSHA256:strings.Repeat("d",64),
   ReversiblePreFirstUseProven:incident.Lane=="Wingless",
   RepairScope:"bounded_config_fix",ReviewSequence:8}
  req.Reviews=append(req.Reviews,signReview(t,finding,reviewerKeys[incident.Lane]))
 }
 return req
}
func TestFullSignedExistingLaneShadowHandoffAndRestart(t *testing.T){
 req:=fixture(t)
 root:=filepath.Join(t.TempDir(),FolderName)
 report,err:=Run(root,req)
 if err!=nil{t.Fatal(err)}
 if report.Schema!=ReportSchema||report.Mode!=mode||report.Incidents!=2||
  report.ReversibleRepairCandidates!=1||report.OriginalReconciliations!=1||
  report.ScientificSuccessorReviews!=0||report.VerifiedScientificCycles!=0||
  len(report.OutboxIDs)!=1{t.Fatalf("invalid operator report: %+v",report)}
 recovered,err:=Verify(root,req.WitnessPins,req.ReviewerPins)
 if err!=nil||!reflectReport(report,recovered){t.Fatalf("restart verification: %v",err)}
 if _,err=Run(root,req);err==nil{t.Fatal("replayed sealed batch")}
 otherPins:=append([]lanewitness.Pinned(nil),req.WitnessPins...)
 otherPins[0].SourceCommitSHA=strings.Repeat("f",40)
 if _,err=Verify(root,otherPins,req.ReviewerPins);err==nil{t.Fatal("re-pinned source accepted")}
}
func reflectReport(a,b Report)bool{
 aa,_:=json.Marshal(a);bb,_:=json.Marshal(b)
 return string(aa)==string(bb)
}
func TestForgedReviewerAndIncompleteBatchLeaveNoOutput(t *testing.T){
 cases:=map[string]func(*Request){
  "forged review":func(r *Request){r.Reviews[0].Finding.Failure=watchdog.FailureAuthority},
  "missing uncertain Yggdrasil":func(r *Request){r.Reviews=r.Reviews[:1]},
  "stale witness":func(r *Request){r.NowUnix=2000},
  "missing original":func(r *Request){r.Witnesses=r.Witnesses[:1]},
  "witness key used as reviewer":func(r *Request){r.ReviewerPins[0].PublicKey=r.WitnessPins[0].PublicKey},
 }
 for name,change:=range cases{t.Run(name,func(t *testing.T){
  req:=fixture(t);change(&req)
  root:=filepath.Join(t.TempDir(),FolderName)
  if _,err:=Run(root,req);err==nil{t.Fatal("bad evidence staged")}
  if _,err:=os.Stat(root);!os.IsNotExist(err){t.Fatal("wrote output before preflight")}
 })}
}
func TestProofOrManifestTamperingRejectedOnRecovery(t *testing.T){
 for _,fileName:=range []string{"witnessed-bundle.v1.json","shadow-report.v1.json"}{
  t.Run(fileName,func(t *testing.T){
   req:=fixture(t);root:=filepath.Join(t.TempDir(),FolderName)
   if _,err:=Run(root,req);err!=nil{t.Fatal(err)}
   p:=filepath.Join(root,fileName)
   original,err:=os.ReadFile(p);if err!=nil{t.Fatal(err)}
   if err=os.WriteFile(p,append(original,[]byte("{}")...),0600);err!=nil{t.Fatal(err)}
   if _,err=Verify(root,req.WitnessPins,req.ReviewerPins);err==nil{t.Fatal("tampered proof accepted")}
  })
 }
}
func TestNoSilentReplacementRoot(t *testing.T){
 req:=fixture(t)
 for _,root:=range []string{"relative/forge-shadow-recovery",filepath.Join(t.TempDir(),"wingless-new")}{
  if _,err:=Run(root,req);err==nil{t.Fatal("unapproved root allowed",root)}
 }
}

func TestSymlinkedShadowRootCannotEscapeCustody(t *testing.T){
 req:=fixture(t)
 base:=t.TempDir()
 target:=filepath.Join(base,"untrusted-target")
 if err:=os.Mkdir(target,0700);err!=nil{t.Fatal(err)}
 root:=filepath.Join(base,FolderName)
 if err:=os.Symlink(target,root);err!=nil{t.Skipf("symlink unavailable: %v",err)}
 if _,err:=Run(root,req);err==nil{t.Fatal("symlinked output root accepted")}
 if _,err:=Verify(root,req.WitnessPins,req.ReviewerPins);err==nil{t.Fatal("symlinked audit root accepted")}
}
