// forge-optimizer-external-intake is a bounded, offline, read-only entry
// point for Wingless/Yggdrasil research produced outside the FORGE selector.
// It cannot call the signed Dream/Pareto promotion or scientific dispatch path.
package main

import (
 "encoding/json"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/optimizerbridge"
)
func run(args []string,out io.Writer)error{
 flags:=flag.NewFlagSet("forge-optimizer-external-intake",flag.ContinueOnError)
 flags.SetOutput(io.Discard)
 file:=flags.String("manifest","","absolute path to pinned observational TRAIN-only evidence")
 if flags.Parse(args)!=nil||flags.NArg()!=0||*file=="" {
  return optimizerbridge.ErrExternalTrainingEvidence
 }
 if !filepath.IsAbs(*file){return optimizerbridge.ErrExternalTrainingEvidence}
 info,err:=os.Lstat(*file)
 if err!=nil||!info.Mode().IsRegular()||info.Size()==0||
  info.Size()>optimizerbridge.MaxExternalTrainingBytes{
  return optimizerbridge.ErrExternalTrainingEvidence
 }
 raw,err:=os.ReadFile(*file)
 if err!=nil{return err}
 report,err:=optimizerbridge.ObserveExternalTraining(raw)
 if err!=nil{return err}
 encoder:=json.NewEncoder(out)
 encoder.SetIndent("","  ")
 if err:=encoder.Encode(report);err!=nil{return fmt.Errorf("write advisory: %w",err)}
 return nil
}
func main(){
 if err:=run(os.Args[1:],os.Stdout);err!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_EXTERNAL_TRAINING_INTAKE_BLOCKED:",err)
  os.Exit(1)
 }
}
