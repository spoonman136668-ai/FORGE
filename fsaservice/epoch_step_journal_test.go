package fsaservice

import (
 "context"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/fsaepochstore"
 "github.com/spoonman136668-ai/forge/workerfence"
 "github.com/spoonman136668-ai/forge/workerlease"
)

type epochClock struct{value uint64}
func(c epochClock)NowUnix(context.Context)(uint64,error){return c.value,nil}
type epochSigner struct{key ed25519.PrivateKey}
func(s epochSigner)Sign(_ context.Context,message []byte)([]byte,error){
 return ed25519.Sign(s.key,message),nil
}
func TestDurableEpochStepJournalWithDualMutualTLSAndRevocation(t *testing.T){
 f:=newGateFixture(t,false)
 adminPub,adminPrivate:=testKey(t)
 receiptPub,receiptPrivate:=testKey(t)
 pin:=fsaepochstore.Pin{ArchiveID:f.anchor.ArchiveID,AuthoritySequence:f.anchor.Sequence,
  AuthorityHeadSHA256:f.anchor.HeadSHA256,OwnerID:"FORGE_SYNTHETIC_OWNER_A",
  OwnerEpoch:f.anchor.AuthorityEpoch,TransferPublicKey:adminPub,
  StepReceiptPublicKey:receiptPub}
 root:=filepath.Join(t.TempDir(),fsaepochstore.FolderName)
 stamp:=epochClock{value:1000}
 signer:=epochSigner{key:receiptPrivate}
 store,err:=fsaepochstore.Provision(root,pin,stamp,signer)
 if err!=nil{t.Fatal(err)}
 lease:=workerlease.Lease{Lane:"Wingless",ExperimentID:"original_test_a",
  IntentSHA256:strings.Repeat("c",64),OwnerID:pin.OwnerID,OwnerEpoch:pin.OwnerEpoch,
  WorkerID:"FORGE_WORKER_A",LeaseSequence:1,ExpiresAtUnix:2000}
 ctx:=context.Background()
 read:=func(l workerlease.Lease,step string)(workerfence.StepObservation,error){
  return workerfence.InspectStep(ctx,f.remote,f.anchor,l,1000,step,
   strings.Repeat("d",64),store,receiptPub)
 }
 observed,err:=read(lease,strings.Repeat("e",64))
 if err!=nil||!observed.ConsumptionObserved||
  observed.ScientificExecutionAuthorized||observed.WorkerDispatchAuthorized{
  t.Fatal("witnessed synthetic step did not fail closed",observed,err)
 }
 if _,err:=read(lease,strings.Repeat("e",64));!errors.Is(err,workerfence.ErrStepIndeterminate){
  t.Fatal("exact signed step replayed",err)
 }
 transition:=fsaepochstore.SignedTransfer{Schema:fsaepochstore.TransferSchema,
  ArchiveID:pin.ArchiveID,FromOwnerID:pin.OwnerID,FromEpoch:pin.OwnerEpoch,
  ToOwnerID:"FORGE_SYNTHETIC_OWNER_B",ToEpoch:pin.OwnerEpoch+1,
  NonceSHA256:strings.Repeat("f",64)}
 raw,err:=json.Marshal(transition);if err!=nil{t.Fatal(err)}
 transition.SignatureHex=hex.EncodeToString(ed25519.Sign(adminPrivate,
  append([]byte(fsaepochstore.TransferDomain),raw...)))
 if err:=store.TransferOwner(ctx,transition);err!=nil{t.Fatal(err)}
 lease.LeaseSequence=2
 if _,err:=read(lease,strings.Repeat("f",64));!errors.Is(err,workerfence.ErrStepIndeterminate){
  t.Fatal("revoked epoch consumed new step",err)
 }
 // A newly transferred owner still cannot start until the independent
 // remote FSA and signed witness also advance to the new epoch.
 lease.OwnerID="FORGE_SYNTHETIC_OWNER_B"
 lease.OwnerEpoch++
 if _,err:=read(lease,strings.Repeat("f",64));!errors.Is(err,workerfence.ErrStepBlocked){
  t.Fatal("local transfer bypassed independent mTLS epoch",err)
 }
 recoveredPin:=pin
 recoveredPin.MinimumOrdinal=2
 restarted,err:=fsaepochstore.Open(root,recoveredPin,stamp,signer)
 if err!=nil{t.Fatal("local ordinal/revocation verification failed",err)}
 snapshot,err:=restarted.Read(ctx)
 if err!=nil||snapshot.OwnerID!="FORGE_SYNTHETIC_OWNER_B"||
  snapshot.OwnerEpoch!=pin.OwnerEpoch+1||snapshot.Ordinal!=2{
  t.Fatal("signed epoch transition lost on local restart",snapshot,err)
 }
}
