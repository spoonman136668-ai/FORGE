// forge-rehearse runs a synthetic disk-backed integration of BOTH EXISTING
// lane names. It never imports real CKB custody or dispatches experiments.
package main

import (
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"
 "strings"

 "github.com/spoonman136668-ai/forge/researchstate"
 "github.com/spoonman136668-ai/forge/shadowcore"
)

// synthEvent creates TEST-ONLY evidence and is never used for real science.
func synthEvent(lane,id string,from,to researchstate.Phase)researchstate.Event {
 e:=researchstate.Event{Lane:lane,ExperimentID:id,FrozenSHA256:strings.Repeat("a",64),From:from,To:to,IrreversibleRisk:to==researchstate.Executing}
 if to==researchstate.Qualified||to==researchstate.Authorized||to==researchstate.Executing||to==researchstate.EvidenceSealed||to==researchstate.Classified||to==researchstate.SuccessorReady{
  e.EvidenceSHA256=strings.Repeat("b",64)
 }
 return e
}

func run(args []string)(shadowcore.RehearsalReport,error){
 f:=flag.NewFlagSet("forge-rehearse",flag.ContinueOnError)
 root:=f.String("new-dir","","brand-new synthetic output directory")
 accept:=f.Bool("synthetic-only",false,"mandatory synthetic test-only acknowledgement")
 if err:=f.Parse(args);err!=nil{return shadowcore.RehearsalReport{},err}
 if !*accept||*root==""||!filepath.IsAbs(*root)||f.NArg()!=0{return shadowcore.RehearsalReport{},errors.New("FORGE_SYNTHETIC_REHEARSAL_EXPLICIT_NEW_DIRECTORY_REQUIRED")}
 if filepath.Base(filepath.Clean(*root))!="forge-synthetic-rehearsal"{
  return shadowcore.RehearsalReport{},errors.New("FORGE_SYNTHETIC_DEDICATED_DIRECTORY_REQUIRED")
 }
 if err:=os.Mkdir(*root,0700);err!=nil{return shadowcore.RehearsalReport{},err}
 archive,err:=researchstate.OpenArchive(*root)
 if err!=nil{return shadowcore.RehearsalReport{},err}
 defer archive.Close()
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  parentPhases:=[]researchstate.Phase{researchstate.Proposed,researchstate.Preregistered,researchstate.Qualifying,researchstate.Qualified,researchstate.Authorized,researchstate.Executing,researchstate.EvidenceSealed,researchstate.Classified,researchstate.SuccessorReady}
  for _,trial:=range []struct{id string;phases []researchstate.Phase}{{"synthetic_parent",parentPhases},{"synthetic_child",parentPhases[:4]}}{
   previous:=researchstate.Phase("")
   for _,next:=range trial.phases{
    j,err:=researchstate.LoadArchive(*root);if err!=nil{return shadowcore.RehearsalReport{},err}
    head,err:=researchstate.Head(j);if err!=nil{return shadowcore.RehearsalReport{},err}
    if _,err=archive.Append(synthEvent(lane,trial.id,previous,next),head);err!=nil{return shadowcore.RehearsalReport{},fmt.Errorf("%s/%s: %w",lane,trial.id,err)}
    previous=next
   }
  }
 }
 // Simulated restart: close the old process lock and open afresh, then re-read
 // the complete immutable disk journal before evaluating the trace.
 if err:=archive.Close();err!=nil{return shadowcore.RehearsalReport{},err}
 archive,err=researchstate.OpenArchive(*root)
 if err!=nil{return shadowcore.RehearsalReport{},err}
 j,err:=researchstate.LoadArchive(*root);if err!=nil{return shadowcore.RehearsalReport{},err}
 return shadowcore.Rehearsal(j)
}
func main(){
 report,err:=run(os.Args[1:])
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 _=json.NewEncoder(os.Stdout).Encode(report)
}
