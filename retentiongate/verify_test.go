package retentiongate
import (
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "strings"
 "testing"
 "time"
)
func encode(v any)[]byte{b,_:=json.Marshal(v);return b}
func TestIndependentSignedReceiptAndRestore(t *testing.T){
 seed1:=[]byte(strings.Repeat("a",32));seed2:=[]byte(strings.Repeat("b",32))
 authority:=ed25519.NewKeyFromSeed(seed1);custodian:=ed25519.NewKeyFromSeed(seed2)
 original:=[]byte("synthetic test original zip bytes; no scientific data")
 h:=sha256.Sum256(original)
 claim:=Claim{Repository:"spoonman136668-ai/Wingless",Experiment:"TEST_1",RunID:9,ArtifactID:10,OriginalZIP_SHA256:hex.EncodeToString(h[:]),BackupZIP_SHA256:hex.EncodeToString(h[:]),StorageObjectID:"external://independently-managed-vault/object/1",RetainUntil:"2032-01-01",Revision:3}
 anchor:=Trust{Schema:AnchorSchema,ResearchAuthorityPub:hex.EncodeToString(authority.Public().(ed25519.PublicKey)),StorageCustodianPub:hex.EncodeToString(custodian.Public().(ed25519.PublicKey)),MinimumRevision:3}
 receipt:=Receipt{Schema:ReceiptSchema,Claim:claim,AuthoritySignature:hex.EncodeToString(ed25519.Sign(authority,signBytes("research-authority",claim))),CustodianSignature:hex.EncodeToString(ed25519.Sign(custodian,signBytes("storage-custodian",claim)))}
 today:=time.Date(2026,10,14,0,0,0,0,time.UTC)
 report,err:=Verify(encode(anchor),encode(receipt),original,original,today)
 if err!=nil{t.Fatal(err)}
 if !report.SignedReceiptCryptographicallyValid||!report.ReplicaBytesRestoredAndMatched||report.ExternalTrustRootsOperationallyIndependent||report.RetentionDurabilityAcrossFailuresProven||report.FirstUseAuthenticated||report.ScientificAccepted{t.Fatal("overclaimed custody or missing verification")}
 invalid:=func(a Trust,r Receipt,orig,backup []byte){t.Helper();if _,err:=Verify(encode(a),encode(r),orig,backup,today);err==nil{t.Fatal("rejected mutation was accepted")}}
 altered:=receipt;altered.Claim.StorageObjectID="external://new-location";invalid(anchor,altered,original,original)
 altered=receipt;altered.CustodianSignature=receipt.AuthoritySignature;invalid(anchor,altered,original,original)
 altered=receipt;altered.Claim.Revision=2;invalid(anchor,altered,original,original)
 invalid(anchor,receipt,original,[]byte("missing original"))
 anchor.StorageCustodianPub=anchor.ResearchAuthorityPub;invalid(anchor,receipt,original,original)
 anchor.StorageCustodianPub=hex.EncodeToString(custodian.Public().(ed25519.PublicKey))
 altered=receipt;altered.Claim.RetainUntil="2026-11-01";invalid(anchor,altered,original,original)
}
