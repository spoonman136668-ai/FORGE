// forge-f61p-owner-predecision is a manual, local preparation utility for the
// EXISTING research owner. No source-only output from this command establishes
// independent randomization, owner custody, first-use, science permission,
// optimizer improvement or a controller instruction.
package main

import (
 "bytes"
 "crypto/rand"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/optimizerbridge"
)

var errNotAuthorized=errors.New("F61P_OWNER_WITNESS_AND_FIRSTUSE_REQUIRED")
func run(args []string)error{
 fs:=flag.NewFlagSet("forge-f61p-owner-predecision",flag.ContinueOnError)
 fs.SetOutput(io.Discard)
 source:=fs.String("nomination","","absolute path to owner-provided policy candidate nomination")
 slate:=fs.String("public-slate-sha256","","")
 family:=fs.String("public-family-sha256","","")
 budget:=fs.String("budget-commitment-sha256","","")
 output:=fs.String("out","","exclusive file for UNWITNESSED preparation only")
 if fs.Parse(args)!=nil||fs.NArg()!=0||
  !filepath.IsAbs(*source)||!filepath.IsAbs(*output)||
  filepath.Clean(*source)==filepath.Clean(*output){
  return errNotAuthorized
 }
 info,err:=os.Lstat(*source)
 if err!=nil||!info.Mode().IsRegular()||info.Size()<2||info.Size()>16384{
  return errNotAuthorized
 }
 raw,err:=os.ReadFile(*source)
 if err!=nil||len(raw)<2||len(raw)>16384{return errNotAuthorized}
 var n optimizerbridge.F59PolicyNomination
 dec:=json.NewDecoder(bytes.NewReader(raw));dec.DisallowUnknownFields()
 if dec.Decode(&n)!=nil{return errNotAuthorized}
 var extra any
 if dec.Decode(&extra)!=io.EOF{return errNotAuthorized}
 frozen,err:=optimizerbridge.FreezeF58()
 if err!=nil{return errNotAuthorized}
 prepared,err:=optimizerbridge.PrepareF61OwnerSelection(frozen,n,*slate,*family,*budget,rand.Reader)
 if err!=nil{return errNotAuthorized}
 serial,err:=json.MarshalIndent(prepared,"","  ")
 if err!=nil{return errNotAuthorized}
 // This file is NOT the externally witnessed/atomic first-use register.
 // Exclusive local create avoids accidental reuse but cannot substitute
 // for the existing owner authority's remote once-only publication.
 file,err:=os.OpenFile(*output,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return errNotAuthorized}
 if _,err=file.Write(append(serial,'\n'));err!=nil{_ = file.Close();return errNotAuthorized}
 if err=file.Sync();err!=nil{_ = file.Close();return errNotAuthorized}
 if err=file.Close();err!=nil{return errNotAuthorized}
 fmt.Println("F61P_SIX_ARM_UNBIASED_PREPARATION=COMPLETE")
 fmt.Println("EXTERNALLY_WITNESSED_PREDECISION=FALSE")
 fmt.Println("ONCE_ONLY_SCIENTIFIC_FIRSTUSE=FALSE")
 fmt.Println("CONTROLLER_OR_ORIGINAL_DISPATCH_AUTHORIZED=FALSE")
 return nil
}
func main(){
 if err:=run(os.Args[1:]);err!=nil{
  fmt.Fprintln(os.Stderr,"F61P_MISSING_OWNER_POLICY_NOMINATION_OR_UNSAFE_LOCAL_OUTPUT")
  os.Exit(2)
 }
}
