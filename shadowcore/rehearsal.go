package shadowcore

import (
 "fmt"
 "github.com/spoonman136668-ai/forge/researchstate"
)

// RehearsalReport describes simulated lifecycle coverage, not scientific results.
type RehearsalReport struct {
 Mode string `json:"mode"`
 CompleteExistingLanes int `json:"complete_existing_lanes"`
 SimulatedSuccessorCycles int `json:"simulated_successor_cycles"`
 RealScientificCycles int `json:"real_scientific_cycles"`
 HeadSHA256 string `json:"head_sha256"`
}
// Rehearsal inspects a deterministic, prebuilt synthetic lifecycle journal.
// It cannot issue starts, invent original evidence, or claim live acceptance.
func Rehearsal(j researchstate.Journal)(RehearsalReport,error){
 snapshot,err:=Observe(j);if err!=nil{return RehearsalReport{},err}
 r:=RehearsalReport{Mode:"SYNTHETIC_OFFLINE_ONLY",HeadSHA256:snapshot.JournalHeadSHA256}
 for _,lane:=range [][]State{snapshot.Wingless,snapshot.Yggdrasil}{
  hasReady,hasQualifiedChild:=false,false
  for _,state:=range lane{
   if state.Phase==researchstate.SuccessorReady{hasReady=true}
   if state.Phase==researchstate.Qualified{hasQualifiedChild=true}
  }
  if !hasReady||!hasQualifiedChild{return RehearsalReport{},fmt.Errorf("%w: missing parent successor transition or qualified child",ErrUnsafe)}
  r.CompleteExistingLanes++
  r.SimulatedSuccessorCycles++
 }
 return r,nil
}
