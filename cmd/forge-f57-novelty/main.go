// Command forge-f57-novelty materializes two content-addressed UNTESTED
// structural mechanism proposals from already frozen FIT-only owner evidence.
// It never executes research, promotes a policy or contacts a model provider.
package main
import (
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "github.com/spoonman136668-ai/forge/optimizerbridge"
)
func run(input,output string)error{
 if input==""||output==""||input==output{return errors.New("separate frozen input and output paths required")}
 f,err:=os.Open(input);if err!=nil{return err}
 defer f.Close()
 dec:=json.NewDecoder(io.LimitReader(f,65537))
 dec.DisallowUnknownFields()
 var studies []optimizerbridge.F57StructuralInput
 if err=dec.Decode(&studies);err!=nil{return err}
 var extra any
 if err=dec.Decode(&extra);err!=io.EOF{return fmt.Errorf("trailing or invalid JSON: %v",err)}
 report,err:=optimizerbridge.PrepareF57Novelty(studies)
 if err!=nil{return err}
 gate,err:=optimizerbridge.AssessActivation(nil,nil,report.Proposals,nil)
 if err!=nil||gate.DreamPareto!="WAITING_AUTHENTIC_PROSPECTIVE_COMPARISON"||
  gate.ThetaEvolve!="WAITING_INDEPENDENTLY_ACCEPTED_NEW_RESULTS"||
  gate.PromptbreederAndGenEnv!="BOUNDED_UNTESTED_NOVELTY_PROPOSALS_READY"||
  gate.ScientificOriginalDispatchAuthorized||gate.ControllerCutoverAuthorized||
  gate.AcceptedRefMutation{
  return errors.New("proposal was incorrectly treated as scientific authorization")
 }
 raw,err:=json.MarshalIndent(report,"","  ");if err!=nil{return err}
 return os.WriteFile(output,append(raw,'\n'),0644)
}
func main(){
 input:=flag.String("evidence","","frozen exact-source FIT input")
 output:=flag.String("out","","new advisory-only JSON output")
 flag.Parse()
 if flag.NArg()!=0{fmt.Fprintln(os.Stderr,"unexpected arguments");os.Exit(2)}
 if err:=run(*input,*output);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
}
