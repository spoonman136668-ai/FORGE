// forge-cutover-audit reads externally pinned old CKB and new FSA evidence.
// It never issues owner grants, restarts consumed originals, or runs science.
package main

import (
 "bytes"
 "context"
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

 "github.com/spoonman136668-ai/forge/ckbhistory"
 "github.com/spoonman136668-ai/forge/ckbreconcile"
 "github.com/spoonman136668-ai/forge/cutovergate"
 "github.com/spoonman136668-ai/forge/fsahead"
 "github.com/spoonman136668-ai/forge/fsaremote"
 "github.com/spoonman136668-ai/forge/lanetakeover"
)
const schema="forge.ckb-fsa.cutover-audit-bundle.v1"
type oldPlan struct{
 TrustedCollectorPublicKeyHex string `json:"trusted_collector_public_key_hex"`
 Wingless lanetakeover.ExpectedLane `json:"wingless"`
 Yggdrasil lanetakeover.ExpectedLane `json:"yggdrasil"`
 MinimumObservationSequence uint64 `json:"minimum_observation_sequence"`
}
type anchorWire struct{
 ArchiveID string `json:"archive_id"`
 KeyID string `json:"key_id"`
 PublicKeyHex string `json:"public_key_hex"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 Sequence uint64 `json:"sequence"`
 HeadSHA256 string `json:"head_sha256"`
}
type pinWire struct{
 ArchiveID string `json:"archive_id"`
 KeyID string `json:"key_id"`
 PublicKeyHex string `json:"public_key_hex"`
 AuthorityEpoch uint64 `json:"authority_epoch"`
 BindingSHA256 string `json:"binding_sha256"`
 WitnessPublicKeyHex string `json:"witness_public_key_hex"`
 MinimumRevision uint64 `json:"minimum_revision"`
}
type bundle struct{
 Schema string `json:"schema"`
 LegacyStateDirectory string `json:"legacy_state_directory"`
 LegacySHA256Pins map[string]string `json:"legacy_sha256_pins"`
 LegacyPlan oldPlan `json:"legacy_plan"`
 LegacyLaneCustody []lanetakeover.SignedCustody `json:"legacy_lane_custody"`
 LegacyJoin cutovergate.SignedJoint `json:"legacy_join"`
 FSAAnchor anchorWire `json:"fsa_anchor"`
 FSAPin pinWire `json:"fsa_pin"`
 FSAWitness fsaremote.SignedWitness `json:"fsa_witness"`
 ForgeOriginalLedgerDirectory string `json:"forge_original_ledger_directory"`
 ForgeOriginalGrantPublicKeyHex string `json:"forge_original_grant_public_key_hex"`
}
func publicKey(s string)(ed25519.PublicKey,error){
 raw,err:=hex.DecodeString(s)
 if err!=nil||len(raw)!=ed25519.PublicKeySize{return nil,cutovergate.ErrBlocked}
 return ed25519.PublicKey(raw),nil
}
func readBundle(path string)(bundle,error){
 var b bundle
 if path==""||!filepath.IsAbs(path){return b,cutovergate.ErrBlocked}
 st,err:=os.Lstat(path)
 if err!=nil||!st.Mode().IsRegular()||st.Size()<2||st.Size()>262144{return b,cutovergate.ErrBlocked}
 raw,err:=os.ReadFile(path)
 if err!=nil||len(raw)>262144{return b,cutovergate.ErrBlocked}
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if err:=d.Decode(&b);err!=nil||b.Schema!=schema{return bundle{},cutovergate.ErrBlocked}
 var extra any
 if !errors.Is(d.Decode(&extra),io.EOF){return bundle{},cutovergate.ErrBlocked}
 // Canonical input rejects duplicate keys, unknown fields and hidden
 // trailing JSON. Caller-maintained pins must be independently sourced.
 normalized,err:=json.Marshal(b)
 if err!=nil||!bytes.Equal(raw,append(normalized,'\n')){return bundle{},cutovergate.ErrBlocked}
 return b,nil
}
func assess(ctx context.Context,source ckbreconcile.WakeReader,b bundle,now uint64)(cutovergate.CompleteReport,error){
 collector,err:=publicKey(b.LegacyPlan.TrustedCollectorPublicKeyHex)
 if err!=nil{return cutovergate.CompleteReport{},err}
 authority,err:=publicKey(b.FSAAnchor.PublicKeyHex)
 if err!=nil{return cutovergate.CompleteReport{},err}
 fsa,err:=publicKey(b.FSAPin.PublicKeyHex)
 if err!=nil{return cutovergate.CompleteReport{},err}
 witness,err:=publicKey(b.FSAPin.WitnessPublicKeyHex)
 if err!=nil{return cutovergate.CompleteReport{},err}
 original,err:=publicKey(b.ForgeOriginalGrantPublicKeyHex)
 if err!=nil{return cutovergate.CompleteReport{},err}
 anchor:=fsahead.Anchor{ArchiveID:b.FSAAnchor.ArchiveID,KeyID:b.FSAAnchor.KeyID,
  PublicKey:authority,AuthorityEpoch:b.FSAAnchor.AuthorityEpoch,
  Sequence:b.FSAAnchor.Sequence,HeadSHA256:b.FSAAnchor.HeadSHA256}
 pin:=fsaremote.Pin{ArchiveID:b.FSAPin.ArchiveID,KeyID:b.FSAPin.KeyID,
  PublicKey:fsa,AuthorityEpoch:b.FSAPin.AuthorityEpoch,
  BindingSHA256:b.FSAPin.BindingSHA256,
  WitnessPublicKey:witness,MinimumRevision:b.FSAPin.MinimumRevision}
 return cutovergate.AssessWithWake(ctx,source,cutovergate.Input{
  LegacyStateDirectory:b.LegacyStateDirectory,LegacySHA256Pins:b.LegacySHA256Pins,
  LegacyPlan:lanetakeover.Plan{TrustedCollectorKey:collector,
   Wingless:b.LegacyPlan.Wingless,Yggdrasil:b.LegacyPlan.Yggdrasil,
   MinimumObservationSequence:b.LegacyPlan.MinimumObservationSequence},
  LegacyLaneCustody:b.LegacyLaneCustody,LegacyJoin:b.LegacyJoin,NowUnix:now,
  FSAAnchor:anchor,FSAPin:pin,FSAWitness:b.FSAWitness,
  ForgeOriginalLedgerDirectory:b.ForgeOriginalLedgerDirectory,
  ForgeOriginalGrantPublicKey:original,
 })
}
func run(args []string,output io.Writer,now uint64)error{
 fs:=flag.NewFlagSet("forge-cutover-audit",flag.ContinueOnError)
 fs.SetOutput(io.Discard)
 bundlePath:=fs.String("bundle","","absolute externally pinned evidence bundle path")
 if err:=fs.Parse(args);err!=nil||fs.NArg()!=0||now==0{return cutovergate.ErrBlocked}
 b,err:=readBundle(*bundlePath);if err!=nil{return err}
 // The full original CKB issuer wake and GitHub execution history must be
 // authenticated from the pinned CKB repository before reporting anything.
 client,err:=ckbhistory.New(os.Getenv("GH_TOKEN"));if err!=nil{return err}
 ctx,cancel:=context.WithTimeout(context.Background(),60*time.Second)
 defer cancel()
 report,err:=assess(ctx,client,b,now);if err!=nil{return err}
 return json.NewEncoder(output).Encode(report)
}
func main(){
 seconds:=time.Now().Unix()
 if seconds<=0||run(os.Args[1:],os.Stdout,uint64(seconds))!=nil{
  fmt.Fprintln(os.Stderr,"FORGE_CKB_FSA_CUTOVER_AUDIT_BLOCKED_NO_REPLAY")
  os.Exit(1)
 }
}
