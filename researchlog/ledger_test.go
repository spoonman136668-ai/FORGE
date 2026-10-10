package researchlog
import "testing"
func TestNewJournal(t *testing.T){
 j:=New()
 if err:=Verify(j);err!=nil{t.Fatal(err)}
 if j.Schema!=Schema||len(j.Entries)!=0{t.Fatal("new journal invalid")}
}
