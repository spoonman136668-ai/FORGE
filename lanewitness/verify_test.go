package lanewitness

import(
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/watchdog"
)
func fixture(t *testing.T)([]Pinned,[]Signed,[]ed25519.PrivateKey){
 t.Helper()
 pins:=[]Pinned{}
 signed:=[]Signed{}
 keys:=[]ed25519.PrivateKey{}
 for i,lane:=range []string{"Wingless","Yggdrasil"}{
  seed:=sha256.Sum256([]byte("TEST ONLY lane witness "+lane))
  key:=ed25519.NewKeyFromSeed(seed[:]);keys=append(keys,key)
  p:=Pinned{Lane:lane,ExistingLaneID:"original-"+lane,ExistingQueueID:"old-queue-"+lane,
   SourceRepo:"spoonman136668-ai/"+lane,SourceCommitSHA:strings.Repeat(string(rune('a'+i)),40),
   OwnerID:"ckb-authoritative-owner",OwnerEpoch:13,JournalHeadSHA256:strings.Repeat(string(rune('c'+i)),64),
   MinimumObservationSequence:51,PublicKey:key.Public().(ed25519.PublicKey)}
  pins=append(pins,p)
  claim:=Claim{Schema:Schema,ExistingLaneID:p.ExistingLaneID,ExistingQueueID:p.ExistingQueueID,
   SourceRepo:p.SourceRepo,SourceCommitSHA:p.SourceCommitSHA,OwnerID:p.OwnerID,
   ObservationSequence:51,ObservedAtUnix:1300,
   Observation:watchdog.Observation{Lane:lane,OriginalExperimentID:"old_original_"+lane,
    JournalHeadSHA256:p.JournalHeadSHA256,OwnerEpoch:p.OwnerEpoch,
    Phase:watchdog.Orchestration,LastProgressUnix:900}}
  signed=append(signed,sign(t,claim,key))
 }
 return pins,signed,keys
}
func sign(t *testing.T,c Claim,k ed25519.PrivateKey)Signed{
 t.Helper();b,err:=json.Marshal(c);if err!=nil{t.Fatal(err)}
 return Signed{Claim:c,SignatureHex:hex.EncodeToString(ed25519.Sign(k,append([]byte(domain),b...)))}
}
func TestAttestedPairDiagnosesExistingLanes(t *testing.T){
 pins,docs,_:=fixture(t)
 result,err:=AssessPair(1301,[]Signed{docs[1],docs[0]},pins)
 if err!=nil{t.Fatal(err)}
 if result.Mode!="INACTIVE_SHADOW_VERIFIED_NO_AUTHORITY"||
  result.Wingless.Action!=watchdog.DiagnoseOrchestration||
  result.Yggdrasil.Action!=watchdog.DiagnoseOrchestration||
  len(result.Incidents)!=2||result.Proofs[0].Lane!="Wingless"||result.Proofs[1].Lane!="Yggdrasil"{
  t.Fatal("unverified or missing diagnoses",result)
 }
 if result.Proofs[0].ObservationSHA256==result.Proofs[1].ObservationSHA256{t.Fatal("cross lane witness collision")}
}
func TestAttestationDeniesSpoofAndStaleInputs(t *testing.T){
 origPins,origDocs,keys:=fixture(t)
 cases:=map[string]func(*[]Pinned,*[]Signed){
  "bad signature":func(_ *[]Pinned,d *[]Signed){(*d)[0].SignatureHex=strings.Repeat("0",128)},
  "source drift":func(_ *[]Pinned,d *[]Signed){(*d)[0].Claim.SourceCommitSHA=strings.Repeat("f",40)},
  "reissued queue":func(_ *[]Pinned,d *[]Signed){(*d)[0].Claim.ExistingQueueID="forge-replacement-queue"},
  "epoch":func(_ *[]Pinned,d *[]Signed){(*d)[0].Claim.Observation.OwnerEpoch++},
  "replayed sequence":func(p *[]Pinned,_ *[]Signed){(*p)[0].MinimumObservationSequence=52},
  "swapped keys":func(p *[]Pinned,_ *[]Signed){(*p)[0].PublicKey=(*p)[1].PublicKey},
  "self reported worker":func(_ *[]Pinned,d *[]Signed){(*d)[0].Claim.Observation.WorkerHeartbeatAuthenticated=true},
  "duplicate lane":func(_ *[]Pinned,d *[]Signed){(*d)[1]=(*d)[0]},
  "untrusted owner":func(_ *[]Pinned,d *[]Signed){(*d)[0].Claim.OwnerID="other"},
  "old observation":func(_ *[]Pinned,d *[]Signed){(*d)[0]=sign(t,func()Claim{c:=(*d)[0].Claim;c.ObservedAtUnix=900;return c}(),keys[0])},
  "future observation":func(_ *[]Pinned,d *[]Signed){(*d)[0]=sign(t,func()Claim{c:=(*d)[0].Claim;c.ObservedAtUnix=1302;return c}(),keys[0])},
 }
 for name,fn:=range cases{t.Run(name,func(t *testing.T){
  pins:=append([]Pinned(nil),origPins...)
  docs:=append([]Signed(nil),origDocs...)
  fn(&pins,&docs)
  if _,err:=AssessPair(1301,docs,pins);err==nil{t.Fatal("untrusted observation accepted")}
 })}
}
