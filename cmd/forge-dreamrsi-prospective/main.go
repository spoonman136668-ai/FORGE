// forge-dreamrsi-prospective verifies two independently signed evidence
// records and emits a read-only, unprivileged observation. It cannot dispatch.
package main

import (
 "bytes"
 "encoding/json"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/dreamrsi"
 "github.com/spoonman136668-ai/forge/dreamrsi/prospective"
)
func readRegular(path string)([]byte,error){
 if !filepath.IsAbs(path){return nil,prospective.ErrEvidence}
 s,err:=os.Lstat(path)
 if err!=nil||!s.Mode().IsRegular()||s.Size()<1||s.Size()>65536{
  return nil,prospective.ErrEvidence
 }
 return os.ReadFile(path)
}
func run(selectionFile,originalFile,policyFile,selectionSHA,selectionKey,originalSHA,originalKey,output string)error{
 beforeRaw,err:=readRegular(selectionFile);if err!=nil{return err}
 afterRaw,err:=readRegular(originalFile);if err!=nil{return err}
 policyRaw,err:=readRegular(policyFile);if err!=nil{return err}
 signedBefore,err:=prospective.ParseSignedSelection(beforeRaw);if err!=nil{return err}
 signedAfter,err:=prospective.ParseSignedOriginal(afterRaw);if err!=nil{return err}
 var policy dreamrsi.Policy
 decoder:=json.NewDecoder(bytes.NewReader(policyRaw));decoder.DisallowUnknownFields()
 if err=decoder.Decode(&policy);err!=nil{return err}
 var extra any
 if err=decoder.Decode(&extra);err!=io.EOF{return prospective.ErrEvidence}
 before,err:=prospective.VerifySelection(signedBefore,prospective.IndependentPin{
  ExpectedSHA256:selectionSHA,PublicKeyHex:selectionKey},policy)
 if err!=nil{return err}
 after,err:=prospective.VerifyOriginal(signedAfter,prospective.IndependentPin{
  ExpectedSHA256:originalSHA,PublicKeyHex:originalKey})
 if err!=nil{return err}
 observation,err:=prospective.Join(before,after)
 if err!=nil{return err}
 if err=prospective.PersistOnce(output,observation);err!=nil{return err}
 fmt.Printf("FORGE_DREAMRSI_PROSPECTIVE=PASS lane=%s tick=%d original_joined=true randomized_audited=false FSA_accepted=false dispatch=false\n",observation.Lane,observation.Tick)
 return nil
}
func main(){
 selection:=flag.String("selection","","absolute path to externally signed predecision")
 original:=flag.String("original","","absolute path to independently signed original result link")
 policy:=flag.String("policy","","absolute path to policy JSON pinned by selection")
 selectionSHA:=flag.String("selection-sha","","independently recorded SHA-256 of canonical predecision")
 selectionKey:=flag.String("selection-public-key","","independently pinned predecision Ed25519 public key")
 originalSHA:=flag.String("original-sha","","independently recorded SHA-256 of canonical result link")
 originalKey:=flag.String("original-public-key","","independently pinned result Ed25519 public key")
 output:=flag.String("output","","new exclusive-create absolute observation file")
 flag.Parse()
 if flag.NArg()!=0||run(*selection,*original,*policy,*selectionSHA,*selectionKey,*originalSHA,*originalKey,*output)!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_DREAMRSI_PREDECISION_LINK_BLOCKED")
  os.Exit(2)
 }
}
