// Package evidencegate verifies content-addressed original scientific evidence
// before a sealed result can be considered for independent classification.
// It provides no authority to classify, promote, or dispatch experiments.
package evidencegate

import (
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "io"
 "os"
)
var ErrBlocked=errors.New("FORGE_ORIGINAL_EVIDENCE_UNVERIFIED")
const MaxOriginalBytes int64=128<<20
type Manifest struct {
 Lane string
 ExperimentID string
 FrozenSHA256 string
 OriginalRunID string
 OriginalSHA256 string
 OriginalBytes int64
 Classification string
}
func hex64(s string)bool{
 if len(s)!=64{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
// VerifyOriginal authenticates bytes against a frozen original manifest.
// A hash match alone never confers scientific validity or custody authority.
func VerifyOriginal(m Manifest, path string)error{
 if (m.Lane!="Wingless"&&m.Lane!="Yggdrasil")||
 m.ExperimentID==""||m.OriginalRunID==""||!hex64(m.FrozenSHA256)||
 !hex64(m.OriginalSHA256)||m.OriginalBytes<=0||
 m.OriginalBytes>MaxOriginalBytes||
 (m.Classification!="POSITIVE"&&m.Classification!="NEGATIVE"&&
 m.Classification!="INCONCLUSIVE"&&m.Classification!="INVALID") {
  return ErrBlocked
 }
 file,err:=os.Open(path);if err!=nil{return ErrBlocked}
 defer file.Close()
 stat,err:=file.Stat()
 if err!=nil||!stat.Mode().IsRegular()||stat.Size()!=m.OriginalBytes{return ErrBlocked}
 h:=sha256.New()
 n,err:=io.Copy(h,io.LimitReader(file,MaxOriginalBytes+1))
 if err!=nil||n!=m.OriginalBytes||hex.EncodeToString(h.Sum(nil))!=m.OriginalSHA256{return ErrBlocked}
 return nil
}
