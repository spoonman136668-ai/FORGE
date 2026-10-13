// Research candidate portfolio handoff. Advisory only: no research dispatch,
// acceptance, source mutation, credential use or scientific first-use operation.
package main

import (
    "encoding/json"
    "errors"
    "fmt"
    "os"
    "path/filepath"

    "github.com/spoonman136668-ai/forge/evoportfolio"
)

var pins=map[string]string{
    "wingless":"88661c123beecb204326ec2f187ecc777e68cb01d5035a0aa533d0a5414a281b",
    "yggdrasil":"45a4bcad9cd8b019da4bcb675e84218c7301cad63df6fd6133b2a1e1a98db967",
}
type result struct {
    Schema string `json:"schema"`
    Decisions []evoportfolio.Decision `json:"decisions"`
    ScientificAccepted bool `json:"scientific_accepted"`
    DispatchAuthorized bool `json:"dispatch_authorized"`
    AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}
func build(dir string)(result,error){
    out:=result{Schema:"forge.research.lane-advisory.v1",Decisions:make([]evoportfolio.Decision,0,2)}
    for _,lane:=range []string{"wingless","yggdrasil"}{
        raw,err:=os.ReadFile(filepath.Join(dir,lane+".json"))
        if err!=nil{return result{},err}
        var frozen evoportfolio.Frozen
        if err=json.Unmarshal(raw,&frozen);err!=nil{return result{},err}
        decision,err:=evoportfolio.Select(frozen,pins[lane])
        if err!=nil{return result{},fmt.Errorf("%s selection refused: %w",lane,err)}
        if decision.ScientificAccepted||decision.DispatchAuthorized||decision.AcceptedRefMutation||
           len(decision.Finalists)==0 {
            return result{},errors.New("RESEARCH_SELECTION_AUTHORITY_BOUNDARY")
        }
        out.Decisions=append(out.Decisions,decision)
    }
    return out,nil
}
func main(){
    out,err:=build("cmd/research-portfolio-select")
    if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
    if err=json.NewEncoder(os.Stdout).Encode(out);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
}
