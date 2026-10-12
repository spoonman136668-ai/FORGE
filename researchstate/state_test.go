package researchstate

import (
 "errors"
 "strings"
 "testing"
)
func add(t *testing.T,j Journal,e Event)Journal{
 t.Helper();h,err:=Head(j);if err!=nil{t.Fatal(err)}
 out,err:=Append(j,e,h);if err!=nil{t.Fatal(err)}
 return out
}
func TestLifecycleAndNoReplay(t *testing.T){
 frozen:=strings.Repeat("a",64);proof:=strings.Repeat("b",64)
 j:=New()
 transitions:=[]struct{from,to Phase;risk bool}{
  {"",Proposed,false},{Proposed,Preregistered,false},
  {Preregistered,Qualifying,false},{Qualifying,Qualified,false},
  {Qualified,Authorized,false},{Authorized,Executing,true},
  {Executing,EvidenceSealed,false},{EvidenceSealed,Classified,false},
  {Classified,SuccessorReady,false},
 }
 for _,x:=range transitions{
  e:=Event{Lane:"Wingless",ExperimentID:"w1",FrozenSHA256:frozen,From:x.from,To:x.to,IrreversibleRisk:x.risk}
  if x.to==Executing||x.to==Qualified||x.to==Authorized||x.to==EvidenceSealed||x.to==Classified||x.to==SuccessorReady{e.EvidenceSHA256=proof}
  j=add(t,j,e)
 }
 p,ok,err:=Status(j,"Wingless","w1");if err!=nil||!ok||p!=SuccessorReady{t.Fatal(p,ok,err)}
 h,_:=Head(j)
 for _,e:=range []Event{
  {Lane:"Wingless",ExperimentID:"w1",FrozenSHA256:frozen,From:Authorized,To:Executing,IrreversibleRisk:true,EvidenceSHA256:proof},
  {Lane:"Wingless",ExperimentID:"w1",FrozenSHA256:frozen,From:SuccessorReady,To:Executing,IrreversibleRisk:true,EvidenceSHA256:proof},
 }{if _,err:=Append(j,e,h);!errors.Is(err,ErrBlocked){t.Fatal("replay accepted",err)}}
 if _,err:=Append(j,Event{Lane:"Yggdrasil",ExperimentID:"y1",FrozenSHA256:frozen,To:Proposed},strings.Repeat("f",64));!errors.Is(err,ErrBlocked){t.Fatal("stale head accepted")}
 j.Entries[1].FrozenSHA256=strings.Repeat("f",64)
 if Verify(j)==nil{t.Fatal("tampered journal accepted")}
}
func TestUnknownDispatchQuarantinedNoRetry(t *testing.T){
 frozen:=strings.Repeat("c",64);proof:=strings.Repeat("d",64);j:=New()
 for _,x:=range []struct{from,to Phase;risk bool}{
  {"",Proposed,false},{Proposed,Preregistered,false},
  {Preregistered,Qualifying,false},{Qualifying,Qualified,false},
  {Qualified,Authorized,false},{Authorized,Quarantined,true},
 }{
  e:=Event{Lane:"Yggdrasil",ExperimentID:"y2",FrozenSHA256:frozen,From:x.from,To:x.to,IrreversibleRisk:x.risk}
  if x.to==Qualified||x.to==Authorized||x.to==Quarantined{e.EvidenceSHA256=proof}
  j=add(t,j,e)
 }
 h,_:=Head(j)
 if _,err:=Append(j,Event{Lane:"Yggdrasil",ExperimentID:"y2",FrozenSHA256:frozen,From:Quarantined,To:Executing,IrreversibleRisk:true,EvidenceSHA256:proof},h);!errors.Is(err,ErrBlocked){t.Fatal("quarantined consumed opportunity retried")}
}
func TestIndependentLanesAndClassification(t *testing.T){
 j:=New()
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  j=add(t,j,Event{Lane:lane,ExperimentID:"trial",FrozenSHA256:strings.Repeat("1",64),To:Proposed})
 }
 if len(j.Entries)!=2{t.Fatal("lane collision")}
 if Verify(j)!=nil{t.Fatal("cross lane replay failed")}
}
