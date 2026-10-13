//go:build forge_f4_science_unreleased
// +build forge_f4_science_unreleased

package pilotf4
import("strings";"testing")
func TestF4OriginalInputsFailClosedWithoutRunningHeldout(t *testing.T){
 for _,tc:=range []struct{lane,run,source string}{
  {"invalid","1",strings.Repeat("a",40)},
  {"Wingless","x",strings.Repeat("a",40)},
  {"Wingless","",strings.Repeat("a",40)},
  {"Yggdrasil","1","bad"},
 }{
  if _,err:=Primary(tc.lane,tc.run,tc.source,Frozen{});err==nil{t.Fatal("bad original request accepted")}
 }
}
