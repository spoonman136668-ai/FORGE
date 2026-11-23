package fsaservice

// RSH-03 exercises the ACTUAL FORGE remote client over two independent test
// mutual-TLS listeners, rather than feeding a forged ReadonlyFSA into RSH-02.
// Test keys/stores have no relevance to live FSA deployment or scientific work.
import (
 "context"
 "crypto/ed25519"
 "crypto/tls"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/researchfeed"
)

func rsh03SixLaneIndex(t *testing.T)[]byte{
 t.Helper()
 ids:=[]struct{lane,repo,path string}{
  {"Wingless","spoonman136668-ai/Wingless","research/synthetic.json"},
  {"Yggdrasil","spoonman136668-ai/Yggdrasil","research/synthetic.json"},
  {"BIO","spoonman136668-ai/FORGE","research/synthetic.json"},
  {"Optimizer Work","spoonman136668-ai/FORGE","research/synthetic.json"},
  {"Mass Research","spoonman136668-ai/FORGE","research/synthetic.json"},
  {"Language Research","spoonman136668-ai/FORGE","research/synthetic.json"},
 }
 c:=make([]researchfeed.Candidate,0,len(ids))
 for _,v:=range ids{
  c=append(c,researchfeed.Candidate{
   Lane:v.lane,ResearchID:"RSH03_SYNTHETIC",SourceRepo:v.repo,
   SourceCommit:strings.Repeat("d",40),SourcePath:v.path,
   EvidenceState:"SOURCE_POINTER_ONLY",Outcome:"UNCLASSIFIED",
  })
 }
 raw,err:=json.Marshal(researchfeed.Input{Schema:researchfeed.Schema,Candidates:c})
 if err!=nil{t.Fatal(err)}
 return raw
}

func TestRSH03SixLaneReadOnlyAuthenticatedDualTLSWitness(t *testing.T){
 primaryPub,_:=testKey(t)
 witnessPub,witnessKey:=testKey(t)
 pin:=fsaremote.Pin{
  ArchiveID:strings.Repeat("a",64),KeyID:"FORGE_RSH03_TEST_ONLY",
  PublicKey:primaryPub,AuthorityEpoch:41,BindingSHA256:strings.Repeat("b",64),
  WitnessPublicKey:witnessPub,MinimumRevision:3,
 }
 owner:=researchfeed.TrustedPin{
  ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,
  PublicKey:append(ed25519.PublicKey(nil),pin.PublicKey...),
  Epoch:pin.AuthorityEpoch,MinimumSequence:2,BindingSHA256:pin.BindingSHA256,
 }
 head:=fsahead.Anchor{
  ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,PublicKey:pin.PublicKey,
  AuthorityEpoch:pin.AuthorityEpoch,Sequence:2,HeadSHA256:strings.Repeat("c",64),
 }
 witnessHead:=fsaremote.WitnessHead{
  Schema:fsaremote.WitnessSchema,Domain:fsaremote.WitnessDomain,
  ArchiveID:pin.ArchiveID,KeyID:pin.KeyID,AuthorityEpoch:pin.AuthorityEpoch,
  BindingSHA256:pin.BindingSHA256,Sequence:head.Sequence,
  HeadSHA256:head.HeadSHA256,Revision:3,
 }
 payload,err:=json.Marshal(witnessHead);if err!=nil{t.Fatal(err)}
 signature:=hex.EncodeToString(ed25519.Sign(witnessKey,
  append([]byte("FORGE-FSA-INDEPENDENT-HIGHWATER-V1\n"),payload...)))
 aStore:=&staticAuthority{anchor:head,digest:pin.BindingSHA256,active:true}
 wStore:=&staticWitness{signed:fsaremote.SignedWitness{Head:witnessHead,SignatureHex:signature}}
 ca,caKey,roots:=testCA(t)
 clientCert,clientSPKI:=certFor(t,ca,caKey,true)
 authorityCert,authoritySPKI:=certFor(t,ca,caKey,false)
 witnessCert,witnessSPKI:=certFor(t,ca,caKey,false)
 ah,err:=AuthorityHandler(pin,clientSPKI,aStore);if err!=nil{t.Fatal(err)}
 wh,err:=WitnessHandler(pin,clientSPKI,wStore);if err!=nil{t.Fatal(err)}
 aServer:=testService(t,ah,authorityCert,roots)
 wServer:=testService(t,wh,witnessCert,roots)
 ap:=fsaremote.Peer{BaseURL:aServer.URL,Roots:roots,Certificate:clientCert,
  ServerSPKISHA256:authoritySPKI}
 wp:=fsaremote.Peer{BaseURL:wServer.URL,Roots:roots,Certificate:clientCert,
  ServerSPKISHA256:witnessSPKI}
 reader,err:=researchfeed.NewVerifiedRemoteFSA(ap,wp,pin,owner)
 if err!=nil{t.Fatal("dual verified reader not created",err)}
 if _,ok:=reader.(interface{CompareAndSwap(context.Context,fsahead.Anchor,fsahead.Anchor)(bool,error)});ok{
  t.Fatal("read-only FSA leaked CAS method")
 }
 raw:=rsh03SixLaneIndex(t)
 result,err:=researchfeed.ObserveFSA(context.Background(),raw,reader,owner)
 if err!=nil{t.Fatal("real TLS witnessed read-only observation failed",err)}
 if !result.AdvisoryOnly||!result.ArchiveBindingObserved||
  result.OriginalBytesAuthenticated||result.FirstUseAuthorized||
  result.ScientificAccepted||result.DispatchAuthorized||
  result.AnchorSequence!=2||result.AnchorHeadSHA256!=head.HeadSHA256||
  len(result.ResearchLanes)!=6||
  result.IntakeSHA256!=hex.EncodeToString(sha256Hash(raw)){
  t.Fatalf("scientific authority claimed from an observation: %#v",result)
 }
 // A forged witness cannot satisfy the same dual service reader.
 wStore.signed.SignatureHex=strings.Repeat("0",128)
 if _,err:=researchfeed.ObserveFSA(context.Background(),raw,reader,owner);err==nil{
  t.Fatal("forged witness accepted")
 }
 wStore.signed.SignatureHex=signature
 aStore.digest=strings.Repeat("e",64)
 if _,err:=researchfeed.ObserveFSA(context.Background(),raw,reader,owner);err==nil{
  t.Fatal("unbound physical archive accepted")
 }
 aStore.digest=pin.BindingSHA256
 wrongOwner:=owner;wrongOwner.PublicKey=ed25519.PublicKey(strings.Repeat("x",32))
 if _,err:=researchfeed.NewVerifiedRemoteFSA(ap,wp,pin,wrongOwner);err==nil{
  t.Fatal("mismatched external operator trust pin accepted")
 }
 wrongPeer:=ap;wrongPeer.ServerSPKISHA256=strings.Repeat("0",64)
 invalid,err:=researchfeed.NewVerifiedRemoteFSA(wrongPeer,wp,pin,owner)
 if err!=nil{t.Fatal("valid-shape wrong server pin must fail at TLS",err)}
 if _,err:=researchfeed.ObserveFSA(context.Background(),raw,invalid,owner);err==nil{
  t.Fatal("wrong authority server SPKI allowed observation")
 }
 absentClient:=ap;absentClient.Certificate=tls.Certificate{}
 if _,err:=researchfeed.NewVerifiedRemoteFSA(absentClient,wp,pin,owner);err==nil{
  t.Fatal("anonymous client provisioned")
 }
 sharedPeer:=wp;sharedPeer.BaseURL=ap.BaseURL
 if _,err:=researchfeed.NewVerifiedRemoteFSA(ap,sharedPeer,pin,owner);err==nil{
  t.Fatal("shared authority/witness origin accepted")
 }
 stale:=pin;stale.MinimumRevision=0
 if _,err:=researchfeed.NewVerifiedRemoteFSA(ap,wp,stale,owner);err==nil{
  t.Fatal("missing independently pinned witness revision accepted")
 }
}

// Test exact input digest without reading any real research evidence.
func sha256Hash(data []byte)[]byte{d:=sha256.Sum256(data);return d[:]}
