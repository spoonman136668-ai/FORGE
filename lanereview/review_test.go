package lanereview

import(
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/lanewitness"
 "github.com/spoonman136668-ai/forge/shadowbridge"
 "github.com/spoonman136668-ai/forge/shadowoutbox"
 "github.com/spoonman136668-ai/forge/watchdog"
)
func signObservation(t *testing.T,c lanewitness.Claim,k ed25519.PrivateKey)lanewitness.Signed{
 t.Helper();data,e:=json.Marshal(c);if e!=nil{t.Fatal(e)}
 return lanewitness.Signed{Claim:c,SignatureHex:hex.EncodeToString(ed25519.Sign(k,append([]byte("FORGE-EXISTING-LANE-WITNESS-V1\n"),data...)))}
}
func signFinding(t *testing.T,c Finding,k ed25519.PrivateKey)SignedFinding{
 t.Helper();data,e:=json.Marshal(c);if e!=nil{t.Fatal(e)}
 return SignedFinding{Finding:c,SignatureHex:hex.EncodeToString(ed25519.Sign(k,append([]byte(domain),data...)))}
}
func fixture(t *testing.T)([]lanewitness.Signed,[]lanewitness.Pinned,[]SignedFinding,[]ReviewerPin){
 t.Helper()
 observations:=[]lanewitness.Signed{};pins:=[]lanewitness.Pinned{}
 reviewers:=[]ReviewerPin{};review:=[]SignedFinding{}
 for i,lane:=range []string{"Wingless","Yggdrasil"}{
  witnessSeed:=sha256.Sum256([]byte("TEST ONLY observation key "+lane))
  reviewSeed:=sha256.Sum256([]byte("TEST ONLY independent reviewer key "+lane))
  wk:=ed25519.NewKeyFromSeed(witnessSeed[:]);rk:=ed25519.NewKeyFromSeed(reviewSeed[:])
  p:=lanewitness.Pinned{Lane:lane,ExistingLaneID:"existing-"+lane,ExistingQueueID:"queue-"+lane,
   SourceRepo:"spoonman136668-ai/"+lane,SourceCommitSHA:strings.Repeat(string(rune('a'+i)),40),
   OwnerID:"ckb-original-owner",OwnerEpoch:14,JournalHeadSHA256:strings.Repeat(string(rune('c'+i)),64),
   MinimumObservationSequence:5,PublicKey:wk.Public().(ed25519.PublicKey)}
  pins=append(pins,p)
  c:=lanewitness.Claim{Schema:lanewitness.Schema,ExistingLaneID:p.ExistingLaneID,
   ExistingQueueID:p.ExistingQueueID,SourceRepo:p.SourceRepo,
   SourceCommitSHA:p.SourceCommitSHA,OwnerID:p.OwnerID,ObservationSequence:5,
   ObservedAtUnix:1300,Observation:watchdog.Observation{Lane:lane,
   OriginalExperimentID:"original_"+lane,OwnerEpoch:14,JournalHeadSHA256:p.JournalHeadSHA256,
   Phase:watchdog.Orchestration,LastProgressUnix:900,FirstUseRisk:i==1}}
  observations=append(observations,signObservation(t,c,wk))
  reviewers=append(reviewers,ReviewerPin{Lane:lane,PublicKey:rk.Public().(ed25519.PublicKey),MinimumReviewSequence:2})
 }
 assessment,e:=lanewitness.AssessPair(1301,observations,pins);if e!=nil{t.Fatal(e)}
 for i,incident:=range assessment.Incidents{
  failure:=watchdog.FailureInfrastructure
  if i==1{failure=watchdog.FailureOriginalUnknown}
  finding:=Finding{Schema:Schema,Lane:incident.Lane,IncidentKey:watchdog.IncidentKey(incident),
   ObservationSHA256:assessment.Proofs[i].ObservationSHA256,Failure:failure,
   EvidenceSHA256:strings.Repeat("f",64),ReversiblePreFirstUseProven:i==0,
   RepairScope:"bounded_existing_repair",ReviewSequence:2}
  seed:=sha256.Sum256([]byte("TEST ONLY independent reviewer key "+incident.Lane))
  review=append(review,signFinding(t,finding,ed25519.NewKeyFromSeed(seed[:])))
 }
 return observations,pins,review,reviewers
}
func TestAttestedObservationsToNoReplayOutboxIntegration(t *testing.T){
 observations,pins,reviews,reviewers:=fixture(t)
 assessment,items,err:=AssessIndependent(1301,observations,pins,reviews,reviewers)
 if err!=nil||len(items)!=2{t.Fatal(err)}
 dir:=t.TempDir()
 var chain []watchdog.DurableIncident
 head:=strings.Repeat("0",64)
 for _,incident:=range assessment.Incidents{
  chain,err=watchdog.AppendIncidentChain(chain,incident,head)
  if err!=nil{t.Fatal(err)}
  head=chain[len(chain)-1].RecordSHA256
 }
 if err=watchdog.ExportIncidentChain(dir,chain);err!=nil{t.Fatal(err)}
 manifest,err:=watchdog.SealRecoveryManifest(dir,chain,items)
 if err!=nil||len(manifest.Repairs)!=1||len(manifest.Reconcile)!=1{
  t.Fatalf("repair and original reconciliation not separated: %v %v",manifest,err)
 }
 outbox:=filepath.Join(t.TempDir(),"outbox")
 ids,err:=shadowbridge.Stage(filepath.Join(dir,"shadow-recovery-"+manifest.ManifestSHA256+".json"),outbox,manifest,chain)
 if err!=nil||len(ids)!=1{t.Fatal(ids,err)}
 staged,err:=shadowoutbox.Load(outbox)
 if err!=nil||len(staged)!=1||staged[0].Lane!="Wingless"||staged[0].FirstUseRisk{
  t.Fatalf("first-use original leaked into repair outbox: %v %v",staged,err)
 }
}
func TestReviewedFactsMustBeIndependentlySignedAndComplete(t *testing.T){
 obs,pins,r,reviewers:=fixture(t)
 if _,_,err:=AssessIndependent(1301,obs,pins,r[:1],reviewers);err==nil{t.Fatal("missing negative outcome silently dropped")}
 forged:=append([]SignedFinding(nil),r...)
 forged[0].Finding.Failure=watchdog.FailureAuthority
 if _,_,err:=AssessIndependent(1301,obs,pins,forged,reviewers);err==nil{t.Fatal("tampered review accepted")}
 swapped:=append([]ReviewerPin(nil),reviewers...)
 swapped[0].PublicKey=pins[0].PublicKey
 if _,_,err:=AssessIndependent(1301,obs,pins,r,swapped);err==nil{t.Fatal("witness key reused as reviewer")}
}
