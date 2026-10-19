package sourcebirth

import (
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "strings"
 "testing"
)

func t16fRemoteFixture()(Signed,Pins,SignedRemoteReadback,IndependentReadbackPins,ed25519.PrivateKey){
 birth,sourcePins,_,_:=signed()
 remotePub,remotePriv:=kp("t16f-independent-remote-mock-NONPRODUCTION")
 o,err:=Verify(birth,sourcePins)
 if err!=nil{panic(err)}
 c:=RemoteReadbackClaim{
  Schema:RemoteReadbackSchema,Lane:birth.Statement.Lane,
  OriginalID:birth.Statement.OriginalID,BirthSHA256:o.BirthSHA256,
  StoreID:"external-store-stub",AuthorityEpoch:birth.Statement.AuthorityEpoch,
  BirthSequence:birth.Statement.BirthSequence,
  PriorHeadSHA256:strings.Repeat("a",64),
  CommittedHeadSHA256:strings.Repeat("b",64),
  CommittedRevision:22,ReadbackHeadSHA256:strings.Repeat("b",64),
  ReadbackRevision:23,
 }
 p:=IndependentReadbackPins{
  StoreID:c.StoreID,AuthorityEpoch:c.AuthorityEpoch,
  PriorHeadSHA256:c.PriorHeadSHA256,
  MinimumCommittedRevision:22,MinimumReadbackRevision:23,
  RemoteWitnessPublicKey:remotePub,
 }
 r:=SignedRemoteReadback{Claim:c}
 resignT16F(&r,remotePriv)
 return birth,sourcePins,r,p,remotePriv
}

func resignT16F(r *SignedRemoteReadback,key ed25519.PrivateKey){
 raw,_:=json.Marshal(r.Claim)
 r.SignatureHex=hex.EncodeToString(ed25519.Sign(key,
  append([]byte(RemoteReadbackDomain),raw...)))
}

func TestT16FThreeDistinctSyntheticSignaturesNeverAdmitRemoteFirstUse(t *testing.T){
 b,sp,r,p,_:=t16fRemoteFixture()
 o,err:=ReviewRemoteReadback(b,sp,r,p)
 if err!=nil||!o.SourceSignaturesVerified||
  !o.RemoteReceiptSignatureVerified||!o.ImmutableSourceAndClaimPinned||
  !o.ClaimedReadbackMatchesCommit{
  t.Fatalf("valid synthetic receipt not structurally verified: %+v %v",o,err)
 }
 if o.LiveRemoteReadbackWitnessed||o.OperationalSignerIndependenceVerified||
  o.GlobalLinearizableFirstUseProven||o.OriginalExecutionAuthorized||
  o.ScientificAccepted {t.Fatalf("synthetic source granted real authority: %+v",o)}
}

func TestT16FFailureMatrix(t *testing.T){
 cases:=map[string]func(*Signed,*Pins,*SignedRemoteReadback,*IndependentReadbackPins){
  "wrong-lane":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){r.Claim.Lane="Yggdrasil"},
  "wrong-original":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){r.Claim.OriginalID="consumed"},
  "wrong-birth-digest":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){r.Claim.BirthSHA256=strings.Repeat("f",64)},
  "wrong-store":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){r.Claim.StoreID="wrong-store"},
  "wrong-epoch":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){r.Claim.AuthorityEpoch++},
  "wrong-sequence":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){r.Claim.BirthSequence++},
  "wrong-previous-head":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){r.Claim.PriorHeadSHA256=strings.Repeat("f",64)},
  "reused-head":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){r.Claim.CommittedHeadSHA256=r.Claim.PriorHeadSHA256;r.Claim.ReadbackHeadSHA256=r.Claim.PriorHeadSHA256},
  "wrong-readback":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){r.Claim.ReadbackHeadSHA256=strings.Repeat("e",64)},
  "stale-commit":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){r.Claim.CommittedRevision=21},
  "stale-readback":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){r.Claim.ReadbackRevision=21},
  "wrong-key":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){pub,_:=kp("rogue");p.RemoteWitnessPublicKey=pub},
  "same-issuer-as-ledger":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){p.RemoteWitnessPublicKey=s.IssuerPublicKey},
  "same-witness-as-ledger":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){p.RemoteWitnessPublicKey=s.WitnessPublicKey},
  "wrong-source-commit":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){s.SourceCommitSHA=strings.Repeat("f",40)},
  "wrong-prereg":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){s.PreregSHA256=strings.Repeat("f",64)},
  "wrong-source-witness-signature":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){b.WitnessSignatureHex=strings.Repeat("0",128)},
  "tampered-remote-signature":func(b *Signed,s *Pins,r *SignedRemoteReadback,p *IndependentReadbackPins){r.SignatureHex=strings.Repeat("0",128)},
 }
 for name,mutate:=range cases{
  t.Run(name,func(t *testing.T){
   b,sp,r,p,_:=t16fRemoteFixture()
   mutate(&b,&sp,&r,&p)
   if _,err:=ReviewRemoteReadback(b,sp,r,p);err==nil{
    t.Fatal("T16F_UNTRUSTED_REMOTE_RECEIPT_ACCEPTED")
   }
  })
 }
}

func TestT16FSeparatelySignedTamperedLedgerClaimStillFailsSourcePins(t *testing.T){
 b,sp,r,p,priv:=t16fRemoteFixture()
 r.Claim.BirthSequence++
 resignT16F(&r,priv)
 if _,err:=ReviewRemoteReadback(b,sp,r,p);err==nil{
  t.Fatal("separately signed wrong first-use sequence admitted")
 }
}
func TestT16FValidClaimCannotProvePhysicalKeyOrLiveStore(t *testing.T){
 b,sp,r,p,priv:=t16fRemoteFixture()
 r.Claim.CommittedRevision=30
 r.Claim.ReadbackRevision=30
 p.MinimumCommittedRevision=30
 p.MinimumReadbackRevision=30
 resignT16F(&r,priv)
 o,err:=ReviewRemoteReadback(b,sp,r,p)
 if err!=nil{t.Fatal(err)}
 if o.LiveRemoteReadbackWitnessed||o.GlobalLinearizableFirstUseProven||
  o.OperationalSignerIndependenceVerified||o.OriginalExecutionAuthorized{
  t.Fatal("commit/readback matching claims are not authenticated operational deployment")
 }
}
