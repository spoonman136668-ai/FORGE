package evoportfolio
import "testing"
func TestR19ESignatureDeduplicationPreservesArchive(t *testing.T){
 f:=fixture()
 f.Candidates[0].Signature="shared_signature"
 f.Candidates[2].Signature="shared_signature"
 f.Candidates[1].Signature="unique_signature"
 f.Candidates[3].Signature="invalid_signature"
 d,err:=Select(f,Digest(f));if err!=nil{t.Fatal(err)}
 if len(d.Archive)!=4||len(d.Finalists)!=2||d.Finalists[0].ID!="alpha"||d.Finalists[1].ID!="beta"{t.Fatalf("deduped finalists or archive incorrect: %+v",d)}
 f.Candidates[1].Signature="bad!"
 if _,err=Select(f,Digest(f));err==nil{t.Fatal("malformed signature admitted")}
}
