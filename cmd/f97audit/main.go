// f97audit is an opt-in, read-only CLI for *already revealed* third-party
// candidate tests. It requires a claimed pinned signer and preregistration
// identity; it cannot establish external ownership or scientific first-use.
package main

import (
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"

 "github.com/spoonman136668-ai/forge/noveltyeval"
)

func run(args []string)error{
 flags:=flag.NewFlagSet("f97audit",flag.ContinueOnError)
 flags.SetOutput(os.Stderr)
 candidate:=flags.String("candidate","","path to REVEALED candidate cohort JSON")
 pinPath:=flags.String("pin","","path to separately supplied source pin JSON")
 signature:=flags.String("signature","","source signature hex (public)")
 f96Path:=flags.String("f96","noveltyeval/f96_cases.json","path to baseline source data")
 output:=flags.String("output","","write source-only JSON report to file")
 if flags.Parse(args)!=nil||len(flags.Args())>0||
  *candidate==""||*pinPath==""||*signature==""||*output==""{
  return errors.New("F97_REVEALED_SOURCE_ONLY_ARGUMENTS_REQUIRED")
 }
 if *candidate==*output||*pinPath==*output||*f96Path==*output{
  return errors.New("F97_CANNOT_OVERWRITE_EVIDENCE_INPUT")
 }
 original,err:=os.ReadFile(*f96Path);if err!=nil{return err}
 external,err:=os.ReadFile(*candidate);if err!=nil{return err}
 pinRaw,err:=os.ReadFile(*pinPath);if err!=nil{return err}
 var pin noveltyeval.F97SuppliedPins
 if err:=json.Unmarshal(pinRaw,&pin);err!=nil{return err}
 result,review,err:=noveltyeval.EvaluateF97RevealedSourceOnly(
  original,external,pin,*signature)
 if err!=nil{return err}
 envelope:=struct{
  Schema string `json:"schema"`
  Review noveltyeval.F97IntakeReview `json:"review"`
  Results noveltyeval.Report `json:"results"`
 }{"forge.optimizer.f97.readonly-revealed-source-output.v1",review,result}
 raw,err:=json.MarshalIndent(envelope,"","  ")
 if err!=nil{return err}
 raw=append(raw,'\n')
 // Never write to an existing file; no archive/accepted refs are mutated.
 fd,err:=os.OpenFile(*output,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
 if err!=nil{return err}
 defer fd.Close()
 if _,err:=fd.Write(raw);err!=nil{return err}
 fmt.Println("F97_REVEALED_SOURCE_ONLY_REPORT_WRITTEN")
 fmt.Println("F97_SCIENTIFIC_ACCEPTANCE=NOT_ESTABLISHED")
 return nil
}
func main(){
 if err:=run(os.Args[1:]);err!=nil{
  fmt.Fprintln(os.Stderr,"F97_INTAKE_DENIED:",err)
  os.Exit(1)
 }
}
