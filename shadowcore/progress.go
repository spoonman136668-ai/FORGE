package shadowcore

import (
 "github.com/spoonman136668-ai/forge/researchstate"
)

// Progress distinguishes a fully authenticated lifecycle trace from an
// operationally successful CI job. This observer never fabricates cycles.
type Progress struct {
 Lane string `json:"lane"`
 RecordedOriginals uint64 `json:"recorded_originals"`
 ClassifiedOriginals uint64 `json:"classified_originals"`
 SuccessorReadyOriginals uint64 `json:"successor_ready_originals"`
 IndeterminateOriginals uint64 `json:"indeterminate_originals"`
}
type ProgressReport struct {
 Mode string `json:"mode"`
 JournalHeadSHA256 string `json:"journal_head_sha256"`
 Wingless Progress `json:"wingless"`
 Yggdrasil Progress `json:"yggdrasil"`
 GenuineAutonomousCyclesVerified bool `json:"genuine_autonomous_cycles_verified"`
}
// Measure examines the exact head-verified archived trace. Even a synthetic
// Classified/SuccessorReady transition does NOT count as a witnessed genuine
// autonomous scientific cycle, which requires original worker receipts,
// immutable raw evidence and independent scientific review.
func Measure(j researchstate.Journal)(ProgressReport,error){
 snapshot,err:=Observe(j)
 if err!=nil{return ProgressReport{},err}
 r:=ProgressReport{Mode:snapshot.Mode,JournalHeadSHA256:snapshot.JournalHeadSHA256,
  Wingless:Progress{Lane:"Wingless"},Yggdrasil:Progress{Lane:"Yggdrasil"}}
 count:=func(dst *Progress,states []State){
  for _,s:=range states{
   dst.RecordedOriginals++
   switch s.Phase {
   case researchstate.Classified:
    dst.ClassifiedOriginals++
   case researchstate.SuccessorReady:
    dst.ClassifiedOriginals++
    dst.SuccessorReadyOriginals++
   case researchstate.Authorized,researchstate.Executing,researchstate.Quarantined:
    dst.IndeterminateOriginals++
   }
  }
 }
 count(&r.Wingless,snapshot.Wingless)
 count(&r.Yggdrasil,snapshot.Yggdrasil)
 return r,nil
}
