// forge-lane-watchdog is a read-only diagnosis of the EXISTING Wingless
// and Yggdrasil programs. It cannot launch science, provision trust, dispatch
// original starts or transfer CKB ownership to FORGE.
package main

import(
 "bytes"
 "crypto/ed25519"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "path/filepath"
 "time"

 "github.com/spoonman136668-ai/forge/lanewitness"
)

type pinFile struct{
 Lane string `json:"lane"`
 ExistingLaneID string `json:"existing_lane_id"`
 ExistingQueueID string `json:"existing_queue_id"`
 SourceRepo string `json:"source_repo"`
 SourceCommitSHA string `json:"source_commit_sha"`
 OwnerID string `json:"owner_id"`
 OwnerEpoch uint64 `json:"owner_epoch"`
 JournalHeadSHA256 string `json:"journal_head_sha256"`
 MinimumObservationSequence uint64 `json:"minimum_observation_sequence"`
 PublicKeyHex string `json:"public_key_hex"`
}
func readBounded(path string,target any)error{
 if path==""||!filepath.IsAbs(path){return fmt.Errorf("absolute, pinned input path required")}
 info,err:=os.Lstat(path)
 if err!=nil||!info.Mode().IsRegular()||info.Size()<=0||info.Size()>65536{
  return fmt.Errorf("witness input missing, nonregular, or oversized")
 }
 f,err:=os.Open(path);if err!=nil{return err};defer f.Close()
 if err:=verifyOpenedWitness(info,f);err!=nil{return err}
 return decodeBoundedWitness(f,target)
}
// Lstat is a path check, not a guarantee about a subsequently opened handle.
// Reject a replaced file or post-Lstat growth/shrinkage before parsing it.
func verifyOpenedWitness(checked os.FileInfo,f *os.File)error{
 opened,err:=f.Stat()
 if err!=nil||!opened.Mode().IsRegular()||opened.Size()!=checked.Size()||!os.SameFile(checked,opened){
  return errors.New("witness input changed between check and open")
 }
 return nil
}
// A reader-size sentinel is checked BEFORE parsing or mutating the target.
func decodeBoundedWitness(in io.Reader,target any)error{
 raw,err:=io.ReadAll(io.LimitReader(in,65537))
 if err!=nil||len(raw)==0||len(raw)>65536{
  return errors.New("witness input read failed or changed size")
 }
 dec:=json.NewDecoder(bytes.NewReader(raw));dec.DisallowUnknownFields()
 if err:=dec.Decode(target);err!=nil{return err}
 var extra any
 if !errors.Is(dec.Decode(&extra),io.EOF){return fmt.Errorf("trailing witness input rejected")}
 return nil
}
func run(args []string,out io.Writer,now uint64)error{
 fs:=flag.NewFlagSet("forge-lane-watchdog",flag.ContinueOnError)
 fs.SetOutput(io.Discard)
 pinsPath:=fs.String("pinned", "", "operator-provisioned pinned witness identities JSON")
 claimsPath:=fs.String("claims", "", "independently signed observations JSON")
 if err:=fs.Parse(args);err!=nil{return err}
 if fs.NArg()!=0||now==0{return fmt.Errorf("invalid watchdog invocation")}
 var files []pinFile
 if err:=readBounded(*pinsPath,&files);err!=nil{return err}
 if len(files)!=2{return fmt.Errorf("exactly two existing lane pins required")}
 pins:=make([]lanewitness.Pinned,0,2)
 for _,p:=range files{
  key,err:=hex.DecodeString(p.PublicKeyHex)
  if err!=nil||len(key)!=ed25519.PublicKeySize{return fmt.Errorf("invalid pinned witness public key")}
  pins=append(pins,lanewitness.Pinned{
   Lane:p.Lane,ExistingLaneID:p.ExistingLaneID,ExistingQueueID:p.ExistingQueueID,
   SourceRepo:p.SourceRepo,SourceCommitSHA:p.SourceCommitSHA,
   OwnerID:p.OwnerID,OwnerEpoch:p.OwnerEpoch,
   JournalHeadSHA256:p.JournalHeadSHA256,
   MinimumObservationSequence:p.MinimumObservationSequence,
   PublicKey:ed25519.PublicKey(key),
  })
 }
 var claims []lanewitness.Signed
 if err:=readBounded(*claimsPath,&claims);err!=nil{return err}
 report,err:=lanewitness.AssessPair(now,claims,pins)
 if err!=nil{return err}
 encoder:=json.NewEncoder(out)
 encoder.SetIndent("","  ")
 return encoder.Encode(report)
}
func main(){
 now:=time.Now().Unix()
 if now<=0||run(os.Args[1:],os.Stdout,uint64(now))!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_WITNESSED_WATCHDOG_FAIL_CLOSED")
  os.Exit(1)
 }
}
