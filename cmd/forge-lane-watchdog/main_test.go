package main

import(
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/lanewitness"
 "github.com/spoonman136668-ai/forge/watchdog"
)
func writeJSON(t *testing.T,path string,v any){
 t.Helper();b,err:=json.Marshal(v);if err!=nil{t.Fatal(err)}
 if err:=os.WriteFile(path,append(b,'\n'),0600);err!=nil{t.Fatal(err)}
}
func TestFullReadOnlyWitnessedWatchdog(t *testing.T){
 dir:=t.TempDir()
 pinsPath,claimsPath:=filepath.Join(dir,"pins.json"),filepath.Join(dir,"claims.json")
 now:=uint64(10000)
 pins:=[]pinFile{}
 claims:=[]lanewitness.Signed{}
 for i,lane:=range []string{"Wingless","Yggdrasil"}{
  seed:=sha256.Sum256([]byte("TEST ONLY cli witness "+lane));private:=ed25519.NewKeyFromSeed(seed[:])
  pin:=pinFile{Lane:lane,ExistingLaneID:"original-"+lane,
   ExistingQueueID:"original-queue-"+lane,SourceRepo:"spoonman136668-ai/"+lane,
   SourceCommitSHA:strings.Repeat(string(rune('a'+i)),40),
   OwnerID:"original-ckb-authority",OwnerEpoch:7,
   JournalHeadSHA256:strings.Repeat(string(rune('c'+i)),64),
   MinimumObservationSequence:2,
   PublicKeyHex:hex.EncodeToString(private.Public().(ed25519.PublicKey))}
  pins=append(pins,pin)
  claim:=lanewitness.Claim{Schema:lanewitness.Schema,
   ExistingLaneID:pin.ExistingLaneID,ExistingQueueID:pin.ExistingQueueID,
   SourceRepo:pin.SourceRepo,SourceCommitSHA:pin.SourceCommitSHA,OwnerID:pin.OwnerID,
   ObservationSequence:2,ObservedAtUnix:now,
   Observation:watchdog.Observation{Lane:lane,OriginalExperimentID:"old-original-"+lane,
    JournalHeadSHA256:pin.JournalHeadSHA256,OwnerEpoch:7,
    Phase:watchdog.Orchestration,LastProgressUnix:9000}}
  data,err:=json.Marshal(claim);if err!=nil{t.Fatal(err)}
  sig:=ed25519.Sign(private,append([]byte("FORGE-EXISTING-LANE-WITNESS-V1\n"),data...))
  claims=append(claims,lanewitness.Signed{Claim:claim,SignatureHex:hex.EncodeToString(sig)})
 }
 writeJSON(t,pinsPath,pins);writeJSON(t,claimsPath,claims)
 var out bytes.Buffer
 if err:=run([]string{"--pinned",pinsPath,"--claims",claimsPath},&out,now);err!=nil{t.Fatal(err)}
 if !bytes.Contains(out.Bytes(),[]byte("INACTIVE_SHADOW_VERIFIED_NO_AUTHORITY"))||
  !bytes.Contains(out.Bytes(),[]byte("DIAGNOSE_RECOVERABLE_STALL")){t.Fatal(out.String())}
 claims[0].Claim.OwnerID="forged"
 writeJSON(t,claimsPath,claims)
 out.Reset()
 if err:=run([]string{"--pinned",pinsPath,"--claims",claimsPath},&out,now);err==nil||out.Len()>0{
  t.Fatalf("tampered claim produced diagnosis: %s",out.String())
 }
}
func TestMissingOrUnsafeInputRejected(t *testing.T){
 var out bytes.Buffer
 if err:=run(nil,&out,10000);err==nil{t.Fatal("missing pins")}
 if err:=readBounded("relative.json",&[]pinFile{});err==nil{t.Fatal("relative input accepted")}
 dir:=t.TempDir();path:=filepath.Join(dir,"pins.json")
 if err:=os.WriteFile(path,[]byte("{}\n{}"),0600);err!=nil{t.Fatal(err)}
 if err:=readBounded(path,&[]pinFile{});err==nil{t.Fatal("trailing JSON accepted")}
}
