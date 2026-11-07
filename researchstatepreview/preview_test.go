package researchstatepreview

import (
 "encoding/json"
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/researchstate"
)
func fixture(t *testing.T)(researchstate.Journal,string){
 t.Helper();j:=researchstate.New()
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  h,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
  j,err=researchstate.Append(j,researchstate.Event{
   Lane:lane,ExperimentID:"original",FrozenSHA256:strings.Repeat("a",64),
   To:researchstate.Proposed,
  },h)
  if err!=nil{t.Fatal(err)}
 }
 h,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
 return j,h
}
func event(id,protocol string,from,to Phase)Event{
 return Event{Lane:"Hybrid",ExperimentID:id,ProtocolSHA256:protocol,From:from,To:to}
}
func TestThreeLaneViewRetainsExactV1AndSafeHybridProgression(t *testing.T){
 j,h:=fixture(t)
 before,_:=json.Marshal(j)
 p,err:=Build(j,h,nil)
 if err!=nil||len(p.Legacy)!=2||p.Legacy[0].Lane!="Wingless"||
  p.Legacy[1].Lane!="Yggdrasil"||p.LegacyCount!=2||
  p.ExecutionAuthorized||p.FirstUseAuthenticated||p.ScientificAccepted{
  t.Fatal("legacy projection unsafe",err,p)
 }
 pin:=strings.Repeat("c",64)
 for _,s:=range []struct{from,to Phase}{
  {"",Observed},{Observed,ProtocolFrozen},{ProtocolFrozen,EngineeringChecked},
 }{
  p,err=Advance(j,h,p,event("G7-S24",pin,s.from,s.to))
  if err!=nil{t.Fatal(err)}
 }
 rebuilt,err:=Build(j,h,p.Hybrid)
 if err!=nil||rebuilt.HybridHeadSHA256!=p.HybridHeadSHA256{t.Fatal("failed to replay unchanged source",err)}
 after,_:=json.Marshal(j)
 if string(before)!=string(after){t.Fatal("legacy journal mutated")}
 actual,_:=researchstate.Head(j)
 if actual!=h{t.Fatal("legacy head changed")}
}
func TestThirdLaneNeverReplaysOrElevatesAuthority(t *testing.T){
 j,h:=fixture(t);p,err:=Build(j,h,nil)
 if err!=nil{t.Fatal(err)}
 pin:=strings.Repeat("c",64)
 bad:=[]Event{
  event("x",pin,"",EngineeringChecked),
  event("x",pin,"",Blocked),
  event("x",pin,Observed,ProtocolFrozen),
  {Lane:"Wingless",ExperimentID:"x",ProtocolSHA256:pin,To:Observed},
  event("x","invalid","",Observed),
 }
 for _,e:=range bad{
  if _,err:=Advance(j,h,p,e);err==nil{t.Fatal("unsafe transition",e)}
 }
 p,err=Advance(j,h,p,event("x",pin,"",Observed));if err!=nil{t.Fatal(err)}
 if _,err:=Advance(j,h,p,event("x",pin,"",Observed));err==nil{t.Fatal("duplicate start")}
 if _,err:=Advance(j,h,p,event("x",strings.Repeat("d",64),Observed,ProtocolFrozen));err==nil{t.Fatal("protocol drift")}
 p,err=Advance(j,h,p,event("x",pin,Observed,Blocked));if err!=nil{t.Fatal(err)}
 if _,err:=Advance(j,h,p,event("x",pin,Blocked,ProtocolFrozen));err==nil{t.Fatal("post-block replay")}
}
func TestProspectiveViewRejectsHistoricalOrShadowTampering(t *testing.T){
 j,h:=fixture(t)
 p,err:=Build(j,h,nil);if err!=nil{t.Fatal(err)}
 p,err=Advance(j,h,p,event("G7-S25",strings.Repeat("c",64),"",Observed));if err!=nil{t.Fatal(err)}
 elevated:=p;elevated.ExecutionAuthorized=true
 if _,err:=Advance(j,h,elevated,event("second",strings.Repeat("c",64),"",Observed));err==nil{t.Fatal("forged execution")}
 elevated=p;elevated.Legacy=append([]LegacyRecord{},p.Legacy...)
 elevated.Legacy[0].Phase=researchstate.Authorized
 if _,err:=Advance(j,h,elevated,event("second",strings.Repeat("c",64),"",Observed));err==nil{t.Fatal("forged old lane")}
 tampered:=append([]Event{},p.Hybrid...)
 tampered[0].ProtocolSHA256=strings.Repeat("f",64)
 if _,err:=Build(j,h,tampered);err==nil{t.Fatal("altered shadow chain")}
 if _,err:=Build(j,strings.Repeat("f",64),p.Hybrid);err==nil{t.Fatal("stale v1 anchor")}
 j.Entries[0].FrozenSHA256=strings.Repeat("f",64)
 if _,err:=Build(j,h,p.Hybrid);err==nil{t.Fatal("modified old journal accepted")}
}
func TestV1StillRefusesHybridAndEmptyV1IsValid(t *testing.T){
 j:=researchstate.New();h,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
 p,err:=Build(j,h,nil)
 if err!=nil||len(p.Legacy)!=0||p.HybridHeadSHA256=="" {t.Fatal("empty view failed",err)}
 if _,err:=researchstate.Append(j,researchstate.Event{
  Lane:"Hybrid",ExperimentID:"G7-S24",FrozenSHA256:strings.Repeat("a",64),
  To:researchstate.Proposed,
 },h);err==nil{t.Fatal("v1 accepted a third lane")}
}
