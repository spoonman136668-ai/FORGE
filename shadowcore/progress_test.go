package shadowcore

import (
 "strings"
 "testing"
 "github.com/spoonman136668-ai/forge/researchstate"
)
func TestProgressDoesNotEquateCIOrSyntheticStateToScience(t *testing.T){
 j:=researchstate.New()
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  head,err:=researchstate.Head(j);if err!=nil{t.Fatal(err)}
  j,err=researchstate.Append(j,researchstate.Event{
   Lane:lane,ExperimentID:"existing_original",FrozenSHA256:strings.Repeat("a",64),
   To:researchstate.Proposed},head)
  if err!=nil{t.Fatal(err)}
 }
 r,err:=Measure(j);if err!=nil{t.Fatal(err)}
 if r.GenuineAutonomousCyclesVerified||r.Wingless.RecordedOriginals!=1||
  r.Yggdrasil.RecordedOriginals!=1||r.Wingless.ClassifiedOriginals!=0{
  t.Fatal("misleading progression report",r)
 }
 j.Entries[0].PreviousSHA256=strings.Repeat("f",64)
 if _,err:=Measure(j);err==nil{t.Fatal("tampered archive accepted")}
}
