package optimizerstages

import (
 "bytes"
 "encoding/binary"
 "errors"
 "math"
 "strings"
 "testing"
)

func f89Fill(s string,n int)string{return strings.Repeat(s,n)}
func f89Frozen(lane string)FrozenSixPolicyTrial{
 source:="a"; pre:="1"; slate:="2"; family:="3";budget:="4"
 if lane=="Yggdrasil"{source="b";pre="a";slate="b";family="c";budget="d"}
 return FrozenSixPolicyTrial{
  Schema:F89FreezeSchema,Lane:lane,Epoch:1,OwnerSourceSHA:f89Fill(source,40),
  PreregistrationSHA256:f89Fill(pre,64),
  CandidateSlateSHA256:f89Fill(slate,64),
  SourceFamilySHA256:f89Fill(family,64),
  BudgetSHA256:f89Fill(budget,64),
  Controls:[4]string{f89Fill("5",64),f89Fill("6",64),f89Fill("7",64),f89Fill("8",64)},
  DreamPolicySHA256:f89Fill("9",64),
  ParetoPolicySHA256:f89Fill("f",64),
 }
}
func f89Raw(values ...uint64)*bytes.Reader{
 b:=make([]byte,8*len(values))
 for i,n:=range values{binary.BigEndian.PutUint64(b[8*i:],n)}
 return bytes.NewReader(b)
}

func TestF89EveryArmUniformExactAndNonAuthorizing(t *testing.T){
 f:=f89Frozen("Wingless")
 wantNames:=[]string{"control_1","control_2","control_3","control_4","dream_rsi","shinka_pareto"}
 for i:=uint64(0);i<6;i++{
  a,err:=PrepareF89Selection(f,f89Raw(i))
  if err!=nil{t.Fatal(err)}
  if a.ArmIndex!=int(i)||a.ArmName!=wantNames[i]||
    a.ExactArmPropensityNumerator!=1||a.ExactArmPropensityDenominator!=6||
    a.ExternallyWitnessedBeforeOutcome||a.OwnerFirstUseAuthenticated||
    a.CausalGainEstablished||a.PolicyPromotionAuthorized||
    a.ScientificOriginalDispatchAuthorized||a.IndependentRandomnessVerified||
    ValidateF89Prepared(f,a)!=nil{t.Fatalf("unsafe arm %d: %+v",i,a)}
  repeat,err:=PrepareF89Selection(f,f89Raw(i))
  if err!=nil||repeat!=a{t.Fatalf("nondeterministic arm %d: %+v %v",i,repeat,err)}
 }
}
func TestF89RejectionThresholdAndUntrustedRandomness(t *testing.T){
 f:=f89Frozen("Wingless")
 a,err:=PrepareF89Selection(f,f89Raw(math.MaxUint64,5))
 if err!=nil||a.ArmIndex!=5||a.RandomDrawHex!="0000000000000005"{
  t.Fatalf("biased-tail rejection failed %+v %v",a,err)
 }
 for _,v:=range []uint64{math.MaxUint64-3,math.MaxUint64-2,math.MaxUint64-1,math.MaxUint64}{
  if _,_,err:=f89Draw(f89Raw(v));!errors.Is(err,ErrF89){
   t.Fatalf("accepted biased draw %d",v)
  }
 }
 invalid:=make([]uint64,16)
 for i:=range invalid{invalid[i]=math.MaxUint64}
 if _,_,err:=f89Draw(f89Raw(invalid...));!errors.Is(err,ErrF89){t.Fatal("accepted exhaustion")}
 if _,err:=PrepareF89Selection(f,nil);!errors.Is(err,ErrF89){t.Fatal("missing draw allowed")}
 if _,err:=PrepareF89Selection(f,bytes.NewReader([]byte{1,2}));!errors.Is(err,ErrF89){t.Fatal("short entropy allowed")}
}
func TestF89RejectUnfrozenOrReusedPolicies(t *testing.T){
 f:=f89Frozen("Wingless")
 cases:=map[string]func(*FrozenSixPolicyTrial){
  "bad schema":func(p *FrozenSixPolicyTrial){p.Schema="legacy"},
  "invalid lane":func(p *FrozenSixPolicyTrial){p.Lane="Other"},
  "zero epoch":func(p *FrozenSixPolicyTrial){p.Epoch=0},
  "missing source":func(p *FrozenSixPolicyTrial){p.OwnerSourceSHA=""},
  "missing prereg":func(p *FrozenSixPolicyTrial){p.PreregistrationSHA256=""},
  "duplicate policy":func(p *FrozenSixPolicyTrial){p.Controls[2]=p.DreamPolicySHA256},
  "duplicate control":func(p *FrozenSixPolicyTrial){p.Controls[1]=p.Controls[0]},
  "policy reused as slate":func(p *FrozenSixPolicyTrial){p.DreamPolicySHA256=p.CandidateSlateSHA256},
  "source family reused":func(p *FrozenSixPolicyTrial){p.SourceFamilySHA256=p.BudgetSHA256},
 }
 for name,fn:=range cases{
  t.Run(name,func(t *testing.T){
   changed:=f;fn(&changed)
   if _,err:=PrepareF89Selection(changed,f89Raw(0));!errors.Is(err,ErrF89){
    t.Fatalf("unfrozen trial accepted: %v",err)
   }
  })
 }
}
func TestF89PreparedIdentityAndPermissionTamperingFailsClosed(t *testing.T){
 f:=f89Frozen("Wingless")
 a,err:=PrepareF89Selection(f,f89Raw(1))
 if err!=nil{t.Fatal(err)}
 changes:=map[string]func(*F89PreparedAssignment){
  "arm substitution":func(p *F89PreparedAssignment){p.ArmIndex=4},
  "chosen hash":func(p *F89PreparedAssignment){p.PolicySHA256=f.Controls[0]},
  "altered draw":func(p *F89PreparedAssignment){p.RandomDrawHex="ffffffffffffffff"},
  "altered digest":func(p *F89PreparedAssignment){p.AssignmentSHA256=f89Fill("0",64)},
  "rounded propensity":func(p *F89PreparedAssignment){p.ExactArmPropensityNumerator=1667;p.ExactArmPropensityDenominator=10000},
  "randomness asserted":func(p *F89PreparedAssignment){p.IndependentRandomnessVerified=true},
  "witness asserted":func(p *F89PreparedAssignment){p.ExternallyWitnessedBeforeOutcome=true},
  "firstuse asserted":func(p *F89PreparedAssignment){p.OwnerFirstUseAuthenticated=true},
  "gain asserted":func(p *F89PreparedAssignment){p.CausalGainEstablished=true},
  "promotion asserted":func(p *F89PreparedAssignment){p.PolicyPromotionAuthorized=true},
  "dispatch asserted":func(p *F89PreparedAssignment){p.ScientificOriginalDispatchAuthorized=true},
  "status altered":func(p *F89PreparedAssignment){p.Status="AUTHORIZED"},
 }
 for name,fn:=range changes{
  t.Run(name,func(t *testing.T){
   changed:=a;fn(&changed)
   if err:=ValidateF89Prepared(f,changed);!errors.Is(err,ErrF89){
    t.Fatalf("tampered record accepted: %v",err)
   }
  })
 }
 changed:=f;changed.Epoch=2
 if err:=ValidateF89Prepared(changed,a);!errors.Is(err,ErrF89){t.Fatal("freeze identity drift admitted")}
}
func TestF89DualLaneSeparationNoSharedOwnerOrDraw(t *testing.T){
 w,y:=f89Frozen("Wingless"),f89Frozen("Yggdrasil")
 wa,err:=PrepareF89Selection(w,f89Raw(0));if err!=nil{t.Fatal(err)}
 ya,err:=PrepareF89Selection(y,f89Raw(1));if err!=nil{t.Fatal(err)}
 if err:=ValidateF89Pair(w,wa,y,ya);err!=nil{t.Fatal(err)}
 if err:=ValidateF89Pair(y,ya,w,wa);!errors.Is(err,ErrF89){t.Fatal("swapped lane order permitted")}
 // Historical reuse is not a fresh randomized assignment even if designs
 // and other SHA identities differ.
 y2:=y;y2.OwnerSourceSHA=w.OwnerSourceSHA
 y2a,e:=PrepareF89Selection(y2,f89Raw(1));if e!=nil{t.Fatal(e)}
 if err:=ValidateF89Pair(w,wa,y2,y2a);!errors.Is(err,ErrF89){t.Fatal("cross-lane source reuse")}
 y2=y;y2.CandidateSlateSHA256=w.CandidateSlateSHA256
 y2a,e=PrepareF89Selection(y2,f89Raw(1));if e!=nil{t.Fatal(e)}
 if err:=ValidateF89Pair(w,wa,y2,y2a);!errors.Is(err,ErrF89){t.Fatal("cross-lane slate reuse")}
 ya,e=PrepareF89Selection(y,f89Raw(0));if e!=nil{t.Fatal(e)}
 if err:=ValidateF89Pair(w,wa,y,ya);!errors.Is(err,ErrF89){t.Fatal("cross-lane reused random draw")}
}
