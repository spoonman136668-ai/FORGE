// forge-optimizer-shadow is a read-only entry point for pre-existing
// evidence exporters. It makes no Cloudflare network request and does not
// trigger science, scientific acceptance, first-use, or a FORGE controller.
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

 "github.com/spoonman136668-ai/forge/optimizerbridge"
)

func readRegularFile(path string,limit int64)([]byte,error){
 if !filepath.IsAbs(path){return nil,errors.New("ABSOLUTE_EVIDENCE_PATH_REQUIRED")}
 info,err:=os.Lstat(path)
 if err!=nil{return nil,err}
 if !info.Mode().IsRegular()||info.Size()==0||info.Size()>limit{
  return nil,errors.New("INVALID_OR_UNSAFE_EVIDENCE_FILE")
 }
 f,err:=os.Open(path)
 if err!=nil{return nil,err}
 defer f.Close()
 b,err:=io.ReadAll(io.LimitReader(f,limit+1))
 if err!=nil||len(b)==0||int64(len(b))>limit{return nil,errors.New("INVALID_EVIDENCE_FILE_LENGTH")}
 return b,nil
}
func parseJSON(raw []byte,dst any)error{
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if err:=d.Decode(dst);err!=nil{return err}
 var extra any
 if err:=d.Decode(&extra);err!=io.EOF{return errors.New("TRAILING_OR_INVALID_JSON")}
 return nil
}
func run(args []string,out io.Writer)error{
 fs:=flag.NewFlagSet("forge-optimizer-shadow",flag.ContinueOnError)
 fs.SetOutput(io.Discard)
 w:=fs.String("wingless-evidence","","existing-worker exported Wingless JSON (absolute path)")
 y:=fs.String("yggdrasil-evidence","","existing-worker exported Yggdrasil JSON (absolute path)")
 signed:=fs.String("signed-export","","custodian-signed Cloudflare export manifest")
 anchor:=fs.String("independent-anchor","","independently sourced public trust pins")
 lanePins:=fs.String("independent-lane-pins","","independently sourced frozen optimizer pins")
 wa:=fs.String("wingless-selection-audit","","independently signed Wingless assignment claim audit")
 ya:=fs.String("yggdrasil-selection-audit","","independently signed Yggdrasil assignment claim audit")
 ap:=fs.String("independent-audit-pins","","independently pinned public audit identities")
 if err:=fs.Parse(args);err!=nil||fs.NArg()!=0{return errors.New("FORGE_OPTIMIZER_SHADOW_FLAGS_INVALID")}
 paths:=[]string{*w,*y,*signed,*anchor,*lanePins,*wa,*ya,*ap}
 seen:=map[string]bool{}
 for _,p:=range paths{
  if p==""||!filepath.IsAbs(p){return errors.New("FORGE_OPTIMIZER_SHADOW_INPUTS_MISSING")}
  normalized:=filepath.Clean(p)
  if seen[normalized]{return errors.New("FORGE_OPTIMIZER_SHADOW_INPUT_ALIAS")}
  seen[normalized]=true
 }
 var inputs [2][]byte
 var err error
 if inputs[0],err=readRegularFile(*w,optimizerbridge.MaxLaneEvidenceBytes);err!=nil{return err}
 if inputs[1],err=readRegularFile(*y,optimizerbridge.MaxLaneEvidenceBytes);err!=nil{return err}
 rawManifest,err:=readRegularFile(*signed,256*1024);if err!=nil{return err}
 rawAnchor,err:=readRegularFile(*anchor,64*1024);if err!=nil{return err}
 rawPins,err:=readRegularFile(*lanePins,128*1024);if err!=nil{return err}
 var export optimizerbridge.SignedExport
 var trust optimizerbridge.ExternalTrust
 var pins []optimizerbridge.LanePins
 if err=parseJSON(rawManifest,&export);err!=nil{return err}
 if err=parseJSON(rawAnchor,&trust);err!=nil{return err}
 if err=parseJSON(rawPins,&pins);err!=nil{return err}
 var signedAudits [2]optimizerbridge.SignedSelectionAudit
 for i,path:=range []string{*wa,*ya}{
  b,err:=readRegularFile(path,optimizerbridge.MaxLaneEvidenceBytes)
  if err!=nil{return err}
  if err:=parseJSON(b,&signedAudits[i]);err!=nil{return err}
 }
 auditPinsRaw,err:=readRegularFile(*ap,64*1024)
 if err!=nil{return err}
 var auditorPins []optimizerbridge.SelectionAuditPin
 if err:=parseJSON(auditPinsRaw,&auditorPins);err!=nil||len(auditorPins)!=2{
  return errors.New("FORGE_OPTIMIZER_INDEPENDENT_AUDIT_PINS_MISSING")
 }
 var pinPair [2]optimizerbridge.SelectionAuditPin
 copy(pinPair[:],auditorPins)
 verified,err:=optimizerbridge.EvaluatePinnedExportWithAudits(
  export,trust,inputs,pins,signedAudits,pinPair)
 if err!=nil{return err}
 encoded,err:=json.MarshalIndent(verified,"","  ")
 if err!=nil{return err}
 _,err=fmt.Fprintln(out,string(encoded))
 return err
}
func main(){
 if err:=run(os.Args[1:],os.Stdout);err!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_OPTIMIZER_SHADOW_BLOCKED:",err)
  os.Exit(1)
 }
}
