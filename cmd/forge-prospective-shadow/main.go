// forge-prospective-shadow evaluates externally supplied, pre-authorized
// research-owner evidence read-only. It NEVER fetches or launches originals.
package main

import (
 "bytes"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/dreamrsi"
)
func readStrictRegular(path string,max int64)([]byte,error){
 if path==""||!filepath.IsAbs(path){return nil,errors.New("R25_ABSOLUTE_FILE_REQUIRED")}
 st,err:=os.Lstat(path)
 if err!=nil{return nil,errors.New("R25_EVIDENCE_NOT_AVAILABLE")}
 if !st.Mode().IsRegular()||st.Size()<1||st.Size()>max{return nil,errors.New("R25_EVIDENCE_UNSAFE_FILE")}
 f,err:=os.Open(path)
 if err!=nil{return nil,errors.New("R25_EVIDENCE_READ_FAILED")}
 defer f.Close()
 raw,err:=io.ReadAll(io.LimitReader(f,max+1))
 if err!=nil||len(raw)<1||int64(len(raw))>max{return nil,errors.New("R25_EVIDENCE_LIMIT")}
 return raw,nil
}
func run(args []string,out io.Writer)error{
 fs:=flag.NewFlagSet("forge-prospective-shadow",flag.ContinueOnError)
 fs.SetOutput(io.Discard)
 owner:=fs.String("owner-evidence","","existing authorized owner's frozen prospective JSON, absolute path")
 pins:=fs.String("independent-pins","","separately supplied authentic public-key/immutable SHA pins, absolute path")
 single:=fs.Bool("single-lane",false,"review one independently authorized Wingless or Yggdrasil source lane without holding up the other")
 if err:=fs.Parse(args);err!=nil||fs.NArg()!=0||
  *owner==""||*pins==""||!filepath.IsAbs(*owner)||!filepath.IsAbs(*pins)||
  filepath.Clean(*owner)==filepath.Clean(*pins){
  return errors.New("R25_READONLY_INPUT_FLAGS_INVALID")
 }
 evidence,err:=readStrictRegular(*owner,dreamrsi.MaxOwnerEvidenceBytes)
 if err!=nil{return err}
 trust,err:=readStrictRegular(*pins,dreamrsi.MaxIndependentPinsBytes)
 if err!=nil{return err}
 var assessment any
 if *single{
  assessment,err=dreamrsi.ReviewOwnerSingleLaneEvidence(evidence,trust)
 }else{
  assessment,err=dreamrsi.ReviewOwnerEvidence(evidence,trust)
 }
 if err!=nil{return err}
 result,err:=json.Marshal(assessment)
 if err!=nil{return err}
 if _,err=io.Copy(out,bytes.NewReader(append(result,'\n')));err!=nil{return err}
 return nil
}
func main(){
 if err:=run(os.Args[1:],os.Stdout);err!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_R25_PROSPECTIVE_SHADOW_BLOCKED:",err)
  os.Exit(1)
 }
}
