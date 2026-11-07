package researchobserver

import (
 "bytes"
 "encoding/json"
 "strings"
 "testing"
)

func hybridEnvelope(conclusion string) []byte {
 return []byte(strings.ReplaceAll(string(validEnvelope("Wingless", conclusion)), "Wingless", "TTT-Hybrid-Lab"))
}

func TestHybridObserverAddsOnlyOptionalUnverifiedMetadata(t *testing.T) {
 w, y, h := validEnvelope("Wingless","success"), validEnvelope("Yggdrasil","failure"), hybridEnvelope("success")
 original, err := Build(w,y)
 if err != nil {t.Fatal(err)}
 before, err := json.Marshal(original)
 if err != nil {t.Fatal(err)}
 if original.Hybrid != nil || bytes.Contains(before, []byte(`"hybrid"`)) {t.Fatal("legacy output changed")}
 report, err := BuildWithHybrid(w,y,h)
 if err != nil {t.Fatal(err)}
 if report.Hybrid == nil || report.Hybrid.Lane != "Hybrid" ||
  report.Hybrid.Repository != "spoonman136668-ai/TTT-Hybrid-Lab" ||
  report.Hybrid.InputRawSHA256 == "" || len(report.Hybrid.Runs)!=1 ||
  report.Hybrid.Runs[0].Conclusion != "success" ||
  report.Hybrid.Runs[0].ScientificClassification != "UNVERIFIED_NOT_A_SCIENTIFIC_RESULT" ||
  report.Hybrid.ScientificEvidenceAuthenticated || report.Hybrid.HistoricalCompletenessVerified ||
  report.ScientificAccepted || report.ExecutionAuthorized || report.AcceptedRefMutation ||
  report.ResearchOriginalsExecuted != 0 { t.Fatalf("hybrid CI metadata elevated to science: %+v",report) }
 again, err := BuildWithHybrid(w,y,h)
 if err != nil || again.Hybrid.InputRawSHA256 != report.Hybrid.InputRawSHA256 {t.Fatal("unstable replay",err)}
}

func TestHybridObserverRejectsForeignIdentityAndConflictingSources(t *testing.T) {
 w,y,h:=validEnvelope("Wingless","success"),validEnvelope("Yggdrasil","failure"),hybridEnvelope("success")
 bad:=[]struct{name string;raw []byte}{
  {"empty",nil},
  {"copied-wingless",w},
  {"copied-yggdrasil",y},
  {"wrong-repo",[]byte(strings.ReplaceAll(string(h),"TTT-Hybrid-Lab","Other-Hybrid"))},
  {"wrong-url",[]byte(strings.Replace(string(h),"/actions/runs/38379395699","/actions/runs/1",1))},
  {"wrong-sha",[]byte(strings.Replace(string(h),strings.Repeat("a",40),"bad",1))},
  {"malformed",append(append([]byte{},h...),[]byte("{}")...)},
  {"same-input",nil},
 }
 for _,tc:=range bad{
  t.Run(tc.name,func(t *testing.T){
   raw:=tc.raw
   if tc.name=="same-input" {raw=w}
   if _,err:=BuildWithHybrid(w,y,raw);err==nil {t.Fatalf("accepted unsafe snapshot %s",tc.name)}
  })
 }
}
