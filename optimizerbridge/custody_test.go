package optimizerbridge

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "reflect"
 "testing"
)

func makePinnedExport(t *testing.T)(SignedExport,ExternalTrust,[2][]byte,[]LanePins,ed25519.PrivateKey){
 t.Helper()
 w,wp:=fixture(t,"Wingless")
 y,yp:=fixture(t,"Yggdrasil")
 wr,_:=json.Marshal(w);yr,_:=json.Marshal(y)
 raw:=[2][]byte{wr,yr}
 birthW:=shaHex([]byte("independent-wingless-source-birth"))
 birthY:=shaHex([]byte("independent-yggdrasil-source-birth"))
 ledgerW:=shaHex([]byte("external-wingless-consumed-first-use-ledger"))
 ledgerY:=shaHex([]byte("external-yggdrasil-consumed-first-use-ledger"))
 m:=ExportManifest{Schema:ExportSchema,Provider:"CLOUDFLARE_EXISTING",
  StoreID:"pre-existing-cloudflare-store",Revision:23,
  Objects:[]EvidenceObject{
   {Lane:"Wingless",ObjectKey:"wingless/immutable/w-history",EvidenceSHA256:shaHex(wr),
    FirstUseLedgerSHA256:ledgerW,FirstUseHighWater:25,SourceBirthLedgerSHA256:birthW},
   {Lane:"Yggdrasil",ObjectKey:"yggdrasil/immutable/y-history",EvidenceSHA256:shaHex(yr),
    FirstUseLedgerSHA256:ledgerY,FirstUseHighWater:19,SourceBirthLedgerSHA256:birthY},
  },
 }
 seed:=sha256.Sum256([]byte("TEST_ONLY_INDEPENDENT_CUSTODIAN"))
 priv:=ed25519.NewKeyFromSeed(seed[:])
 trust:=ExternalTrust{
  StoreID:m.StoreID,MinimumRevision:23,
  CustodianEd25519PublicKeyHex:hex.EncodeToString(priv.Public().(ed25519.PublicKey)),
  WinglessFirstUseLedgerSHA256:ledgerW,WinglessFirstUseHighWater:25,
  WinglessSourceBirthLedgerSHA256:birthW,
  YggdrasilFirstUseLedgerSHA256:ledgerY,YggdrasilFirstUseHighWater:19,
  YggdrasilSourceBirthLedgerSHA256:birthY,
 }
 e:=SignedExport{Manifest:m}
 resign(&e,&trust,priv)
 return e,trust,raw,[]LanePins{wp,yp},priv
}
func resign(e *SignedExport,t *ExternalTrust,k ed25519.PrivateKey){
 b,_:=json.Marshal(e.Manifest)
 t.ManifestSHA256=shaHex(b)
 e.SignatureHex=hex.EncodeToString(ed25519.Sign(k,append([]byte(ExportDomain),b...)))
}
func TestPinnedExportSyntheticOnlyNoAuthority(t *testing.T){
 e,trust,raw,pins,_:=makePinnedExport(t)
 a,err:=EvaluatePinnedExport(e,trust,raw,pins)
 if err!=nil{t.Fatal(err)}
 b,err:=EvaluatePinnedExport(e,trust,raw,pins)
 if err!=nil||!reflect.DeepEqual(a,b){t.Fatal("nondeterministic attested replay",err)}
 if !a.SourceDigestAndCustodySignatureVerified||a.RemoteReadOperationallyWitnessed||
  a.CompleteFirstUseReconciliationVerified||a.ScientificImprovementEstablished||
  a.DispatchAuthorized||a.ScientificAccepted||a.Shadow.ScienceOriginalsExecuted!=0||
  len(a.Shadow.Lanes)!=2||a.Shadow.FirstUseConsumed{
  t.Fatalf("export promoted unproven custody/authority: %+v",a)
 }
}
func TestPinnedExportRejectsBadTrustAndEvidence(t *testing.T){
 cases:=[]struct{
  name string
  change func(*SignedExport,*ExternalTrust,*[2][]byte,*[]LanePins,ed25519.PrivateKey)
 }{
  {"no key",func(e *SignedExport,t *ExternalTrust,r *[2][]byte,p *[]LanePins,k ed25519.PrivateKey){t.CustodianEd25519PublicKeyHex=""}},
  {"self generated anchor",func(e *SignedExport,t *ExternalTrust,r *[2][]byte,p *[]LanePins,k ed25519.PrivateKey){t.ManifestSHA256=shaHex([]byte("self"))}},
  {"bad signature",func(e *SignedExport,t *ExternalTrust,r *[2][]byte,p *[]LanePins,k ed25519.PrivateKey){e.SignatureHex=hex.EncodeToString(make([]byte,64))}},
  {"tamper export evidence",func(e *SignedExport,t *ExternalTrust,r *[2][]byte,p *[]LanePins,k ed25519.PrivateKey){(*r)[0]=append(append([]byte(nil),(*r)[0]...),10)}},
  {"swap project payload",func(e *SignedExport,t *ExternalTrust,r *[2][]byte,p *[]LanePins,k ed25519.PrivateKey){(*r)[0],(*r)[1]=(*r)[1],(*r)[0]}},
  {"rollback revision",func(e *SignedExport,t *ExternalTrust,r *[2][]byte,p *[]LanePins,k ed25519.PrivateKey){e.Manifest.Revision=22;resign(e,t,k)}},
  {"incorrect first-use anchor",func(e *SignedExport,t *ExternalTrust,r *[2][]byte,p *[]LanePins,k ed25519.PrivateKey){t.WinglessFirstUseHighWater=24}},
  {"untrusted source birth",func(e *SignedExport,t *ExternalTrust,r *[2][]byte,p *[]LanePins,k ed25519.PrivateKey){t.YggdrasilSourceBirthLedgerSHA256=shaHex([]byte("unrelated"))}},
  {"reused storage key",func(e *SignedExport,t *ExternalTrust,r *[2][]byte,p *[]LanePins,k ed25519.PrivateKey){e.Manifest.Objects[1].ObjectKey=e.Manifest.Objects[0].ObjectKey;resign(e,t,k)}},
  {"bad path",func(e *SignedExport,t *ExternalTrust,r *[2][]byte,p *[]LanePins,k ed25519.PrivateKey){e.Manifest.Objects[0].ObjectKey="../secrets";resign(e,t,k)}},
  {"relabel object",func(e *SignedExport,t *ExternalTrust,r *[2][]byte,p *[]LanePins,k ed25519.PrivateKey){e.Manifest.Objects[0].Lane="Yggdrasil";resign(e,t,k)}},
  {"signature key reused as history signer",func(e *SignedExport,t *ExternalTrust,r *[2][]byte,p *[]LanePins,k ed25519.PrivateKey){t.CustodianEd25519PublicKeyHex=(*p)[0].IndependentEd25519PublicKeyHex}},
  {"source pin mismatch",func(e *SignedExport,t *ExternalTrust,r *[2][]byte,p *[]LanePins,k ed25519.PrivateKey){(*p)[1].DreamTrainSHA256=shaHex([]byte("forged"))}},
  {"no independent first-use high water",func(e *SignedExport,t *ExternalTrust,r *[2][]byte,p *[]LanePins,k ed25519.PrivateKey){e.Manifest.Objects[1].FirstUseHighWater=0;resign(e,t,k);t.YggdrasilFirstUseHighWater=0}},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   e,trust,raw,pins,key:=makePinnedExport(t)
   tc.change(&e,&trust,&raw,&pins,key)
   got,err:=EvaluatePinnedExport(e,trust,raw,pins)
   if err==nil||!reflect.DeepEqual(got,ExportReview{}){
    t.Fatalf("accepted corrupted provenance: %+v err=%v",got,err)
   }
  })
 }
}
