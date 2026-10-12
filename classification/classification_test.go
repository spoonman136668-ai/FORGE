package classification
import("crypto/ed25519";"crypto/sha256";"encoding/hex";"encoding/json";"strings";"testing")
func TestSignedNegativeAndTamperDenial(t *testing.T){
 seed:=sha256.Sum256([]byte("TEST ONLY independent classifier"))
 key:=ed25519.NewKeyFromSeed(seed[:])
 e:=Expected{Lane:"Yggdrasil",ExperimentID:"existing_1",FrozenSHA256:strings.Repeat("a",64),OriginalEvidenceSHA256:strings.Repeat("b",64),ReviewerID:"independent",TrustedKey:key.Public().(ed25519.PublicKey)}
 a:=Attestation{Statement:Statement{Schema:Schema,Lane:e.Lane,ExperimentID:e.ExperimentID,FrozenSHA256:e.FrozenSHA256,OriginalEvidenceSHA256:e.OriginalEvidenceSHA256,ReviewerID:e.ReviewerID,Outcome:"NEGATIVE"}}
 b,err:=json.Marshal(a.Statement);if err!=nil{t.Fatal(err)}
 a.SignatureHex=hex.EncodeToString(ed25519.Sign(key,append([]byte(domain),b...)))
 if _,err:=Verify(a,e);err!=nil{t.Fatal(err)}
 a.Statement.Outcome="POSITIVE";if _,err:=Verify(a,e);err==nil{t.Fatal("tampered classification accepted")}
 a.Statement.Outcome="NEGATIVE";a.Statement.OriginalEvidenceSHA256=strings.Repeat("c",64)
 if _,err:=Verify(a,e);err==nil{t.Fatal("incorrect evidence accepted")}
}
