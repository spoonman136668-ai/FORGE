package sourcebirth
import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "strings"
 "testing"
)
func kp(label string)(ed25519.PublicKey,ed25519.PrivateKey){
 sum:=sha256.Sum256([]byte("NONPRODUCTION-TEST-ONLY:"+label))
 priv:=ed25519.NewKeyFromSeed(sum[:])
 return priv.Public().(ed25519.PublicKey),priv
}
func signed()(Signed,Pins,ed25519.PrivateKey,ed25519.PrivateKey){
 issuerPub,issuerPriv:=kp("issuer")
 witnessPub,witnessPriv:=kp("witness")
 b:=Statement{Schema:Schema,Lane:"Wingless",Repository:"spoonman136668-ai/Wingless",
 OriginalID:"W100",SourceCommitSHA:strings.Repeat("a",40),SourceTreeSHA:strings.Repeat("b",40),
 PreregSHA256:strings.Repeat("c",64),CohortSHA256:strings.Repeat("d",64),
 ArchiveSHA256:strings.Repeat("e",64),AuthorityEpoch:5,BirthSequence:10,
 WitnessRevision:12,FrozenUnix:100,BirthUnix:101}
 p:=Pins{Lane:b.Lane,OriginalID:b.OriginalID,SourceCommitSHA:b.SourceCommitSHA,
 SourceTreeSHA:b.SourceTreeSHA,PreregSHA256:b.PreregSHA256,CohortSHA256:b.CohortSHA256,
 ArchiveSHA256:b.ArchiveSHA256,AuthorityEpoch:b.AuthorityEpoch,MinBirthSequence:10,
 MinWitnessRevision:12,IssuerPublicKey:issuerPub,WitnessPublicKey:witnessPub}
 s:=Signed{Statement:b,IssuerSignatureHex:hex.EncodeToString(ed25519.Sign(issuerPriv,signedPayload(IssuerDomain,b))),
 WitnessSignatureHex:hex.EncodeToString(ed25519.Sign(witnessPriv,signedPayload(WitnessDomain,b)))}
 return s,p,issuerPriv,witnessPriv
}
func TestValidDualSignatureNeverGrantsAuthority(t *testing.T){
 s,p,_,_:=signed()
 o,err:=Verify(s,p)
 if err!=nil||!o.TwoSignaturesVerified||o.PhysicallyIndependent||o.PersistentFirstUseProven||
 o.ScientificExecutionAuthorized||o.CutoverAuthorized||
 o.BirthSequence!=10||o.WitnessRevision!=12||!validHex(o.BirthSHA256,64){
 t.Fatalf("unsafe birth observation: %+v %v",o,err)
 }
}
func TestExactSourceAndSignerNegativeCases(t *testing.T){
 cases:=map[string]func(*Signed,*Pins){
 "invalid-lane":func(s *Signed,p *Pins){s.Statement.Lane="KTRADE"},
 "cross-lane":func(s *Signed,p *Pins){p.Lane="Yggdrasil"},
 "original":func(s *Signed,p *Pins){p.OriginalID="W101"},
 "wrong-source":func(s *Signed,p *Pins){p.SourceCommitSHA=strings.Repeat("f",40)},
 "tree":func(s *Signed,p *Pins){p.SourceTreeSHA=strings.Repeat("f",40)},
 "prereg":func(s *Signed,p *Pins){p.PreregSHA256=strings.Repeat("f",64)},
 "cohort":func(s *Signed,p *Pins){p.CohortSHA256=strings.Repeat("f",64)},
 "archive":func(s *Signed,p *Pins){p.ArchiveSHA256=strings.Repeat("f",64)},
 "stale-epoch":func(s *Signed,p *Pins){p.AuthorityEpoch++},
 "stale-birth":func(s *Signed,p *Pins){p.MinBirthSequence++},
 "stale-witness":func(s *Signed,p *Pins){p.MinWitnessRevision++},
 "same-key":func(s *Signed,p *Pins){p.WitnessPublicKey=p.IssuerPublicKey},
 "missing-key":func(s *Signed,p *Pins){p.IssuerPublicKey=nil},
 "bad-issuer":func(s *Signed,p *Pins){s.IssuerSignatureHex=strings.Repeat("0",128)},
 "bad-witness":func(s *Signed,p *Pins){s.WitnessSignatureHex=strings.Repeat("0",128)},
 "false-frozen-order":func(s *Signed,p *Pins){s.Statement.BirthUnix=s.Statement.FrozenUnix},
 "unsigned-archive-drift":func(s *Signed,p *Pins){s.Statement.ArchiveSHA256=strings.Repeat("f",64)},
 }
 for name,fn:=range cases{
 t.Run(name,func(t *testing.T){
 s,p,_,_:=signed();fn(&s,&p)
 if _,err:=Verify(s,p);err==nil{t.Fatal("admitted untrusted source birth")}
 })
 }
}
func TestSignedWrongSourceStillRejectsOperatorPinnedIdentity(t *testing.T){
 s,p,issuer,witness:=signed()
 s.Statement.SourceCommitSHA=strings.Repeat("f",40)
 s.IssuerSignatureHex=hex.EncodeToString(ed25519.Sign(issuer,signedPayload(IssuerDomain,s.Statement)))
 s.WitnessSignatureHex=hex.EncodeToString(ed25519.Sign(witness,signedPayload(WitnessDomain,s.Statement)))
 if _,err:=Verify(s,p);err==nil{t.Fatal("separately signed wrong source bypassed independent pin")}
}
func TestRoleDomainSignaturesNotInterchangeable(t *testing.T){
 s,p,issuer,witness:=signed()
 s.IssuerSignatureHex=hex.EncodeToString(ed25519.Sign(issuer,signedPayload(WitnessDomain,s.Statement)))
 if _,err:=Verify(s,p);err==nil{t.Fatal("witness domain accepted as issuer")}
 s,p,_,_=signed()
 s.WitnessSignatureHex=hex.EncodeToString(ed25519.Sign(witness,signedPayload(IssuerDomain,s.Statement)))
 if _,err:=Verify(s,p);err==nil{t.Fatal("issuer domain accepted as witness")}
}
