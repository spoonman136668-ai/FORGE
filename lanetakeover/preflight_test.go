package lanetakeover

import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "strings"
 "testing"
)
func digest(s string)string{h:=sha256.Sum256([]byte(s));return hex.EncodeToString(h[:])}
func fixture(t *testing.T)(Plan,[]SignedCustody,ed25519.PrivateKey){
 t.Helper()
 seed:=sha256.Sum256([]byte("TEST ONLY existing-lane custody, not operational trust"))
 priv:=ed25519.NewKeyFromSeed(seed[:]);pub:=priv.Public().(ed25519.PublicKey)
 mk:=func(lane,repo,sha,queue,id string)SignedCustody{
  c:=Custody{Schema:Schema,Lane:lane,SourceRepo:repo,SourceCommitSHA:sha,
   ExistingQueueID:queue,ExistingLaneID:id,LegacyAuthorityID:"CKB-RESEARCH",
   LegacyJournalHeadSHA256:digest(lane+"-journal"),
   LegacyConsumedLedgerSHA256:digest(lane+"-cohorts"),
   LegacyFrozenWorkSHA256:digest(lane+"-frozen"),
   LastLegacyOwnerReleaseSHA256:digest(lane+"-release"),
   ObservationSequence:17}
  return sign(t,c,priv)
 }
 w:=mk("Wingless","spoonman136668-ai/Wingless",strings.Repeat("a",40),"existing-w-queue","original-wingless")
 y:=mk("Yggdrasil","spoonman136668-ai/Yggdrasil",strings.Repeat("b",40),"existing-y-queue","original-yggdrasil")
 e:=func(c Custody)ExpectedLane{
  return ExpectedLane{Lane:c.Lane,SourceRepo:c.SourceRepo,SourceCommitSHA:c.SourceCommitSHA,
   ExistingQueueID:c.ExistingQueueID,ExistingLaneID:c.ExistingLaneID,LegacyAuthorityID:c.LegacyAuthorityID}
 }
 return Plan{TrustedCollectorKey:pub,Wingless:e(w.Custody),Yggdrasil:e(y.Custody),
  MinimumObservationSequence:17},[]SignedCustody{w,y},priv
}
func sign(t *testing.T,c Custody,k ed25519.PrivateKey)SignedCustody{
 t.Helper();b,err:=json.Marshal(c);if err!=nil{t.Fatal(err)}
 return SignedCustody{Custody:c,SignatureHex:hex.EncodeToString(ed25519.Sign(k,append([]byte(domain),b...)))}
}
func TestExistingLanesReadOnlyPreflight(t *testing.T){
 p,v,_:=fixture(t)
 a,e:=Preflight(p,v);if e!=nil{t.Fatal(e)}
 b,e:=Preflight(p,[]SignedCustody{v[1],v[0]});if e!=nil||a!=b{t.Fatal("input ordering changes result",e)}
 if len(IdentityKeys())!=2{t.Fatal("unexpected lane creation")}
}
func TestFailClosedAgainstUnsafeTakeover(t *testing.T){
 base,v,priv:=fixture(t)
 cases:=map[string]func(*Plan,[]SignedCustody){
  "missing lane":func(_ *Plan,v []SignedCustody){v[1]=v[0]},
  "tampered SHA":func(_ *Plan,v []SignedCustody){v[0].Custody.SourceCommitSHA=strings.Repeat("c",40)},
  "active old lease":func(_ *Plan,v []SignedCustody){v[0]=sign(t,func()Custody{c:=v[0].Custody;c.ActiveLeaseCount=1;return c}(),priv)},
  "unresolved dispatch":func(_ *Plan,v []SignedCustody){v[1]=sign(t,func()Custody{c:=v[1].Custody;c.UncertainDispatchCount=1;return c}(),priv)},
  "missing release":func(_ *Plan,v []SignedCustody){v[0]=sign(t,func()Custody{c:=v[0].Custody;c.LastLegacyOwnerReleaseSHA256="";return c}(),priv)},
  "stale attestation":func(_ *Plan,v []SignedCustody){v[1]=sign(t,func()Custody{c:=v[1].Custody;c.ObservationSequence=16;return c}(),priv)},
  "new queue":func(_ *Plan,v []SignedCustody){v[0]=sign(t,func()Custody{c:=v[0].Custody;c.ExistingQueueID="forge-new-queue";return c}(),priv)},
  "shared queue":func(p *Plan,v []SignedCustody){p.Yggdrasil.ExistingQueueID=p.Wingless.ExistingQueueID},
  "false repo":func(_ *Plan,v []SignedCustody){v[0]=sign(t,func()Custody{c:=v[0].Custody;c.SourceRepo="wrong/repo";return c}(),priv)},
  "invalid key":func(p *Plan,_ []SignedCustody){p.TrustedCollectorKey=make([]byte,32)},
  "cross lane digest":func(_ *Plan,v []SignedCustody){v[1]=sign(t,func()Custody{c:=v[1].Custody;c.LegacyConsumedLedgerSHA256=v[0].Custody.LegacyConsumedLedgerSHA256;return c}(),priv)},
 }
 for name,fn:=range cases{t.Run(name,func(t *testing.T){
  p:=base;rows:=append([]SignedCustody(nil),v...);fn(&p,rows)
  _,err:=Preflight(p,rows);if !errors.Is(err,ErrBlocked){t.Fatalf("wanted fail closed, got %v",err)}
 })}
 if _,err:=Preflight(base,v[:1]);!errors.Is(err,ErrBlocked){t.Fatal("accepted partial takeover")}
 if _,err:=Preflight(base,append(v,v[0]));!errors.Is(err,ErrBlocked){t.Fatal("accepted new lane")}
}
