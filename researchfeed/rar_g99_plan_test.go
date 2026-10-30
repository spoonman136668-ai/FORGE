package researchfeed

import (
    "encoding/json"
    "os"
    "path/filepath"
    "reflect"
    "testing"
)

func rarG99Source(t *testing.T, file string) []byte {
    t.Helper()
    raw, err := os.ReadFile(filepath.Join("..", "research", "replay_acceleration", file))
    if err != nil { t.Fatal(err) }
    return raw
}
func rarG99Inputs(t *testing.T) ([]byte, []byte, []byte) {
    t.Helper()
    return rarG99Source(t,"rar_g90_source_index.json"),
        rarG99Source(t,"rar_g7_g8_advisory_evidence.json"),
        rarG99Source(t,"rar_g33_original_cross_os_nested_receipts.json")
}
func TestRARG99AuthenticSourceOnlyPlanningChangesCounterfactualOrder(t *testing.T) {
    index,g78,g33 := rarG99Inputs(t)
    proposed := []RARHypothesis{
        {ID:"unchanged-surprise-replay",PriorResearchID:"RAR-G7"},
        {ID:"unreviewed-new-hypothesis"},
        {ID:"invalid-cpu-speedup-claim",PriorResearchID:"RAR-G33"},
        {ID:"fresh-g8-comparative-test",PriorResearchID:"RAR-G8"},
    }
    got,err := PreviewRARPlanning(index,g78,g33,proposed)
    if err != nil { t.Fatal(err) }
    order := []string{}
    for _,c := range got.Choices {
        order=append(order,c.ID)
        if c.LinkageAuthenticated {t.Fatalf("caller link laundered as authenticated: %#v",c)}
    }
    want := []string{
        "unreviewed-new-hypothesis","fresh-g8-comparative-test",
        "unchanged-surprise-replay","invalid-cpu-speedup-claim",
    }
    if !reflect.DeepEqual(order,want) || !got.InputOrderChanged {
        t.Fatalf("advisory did not change offline planning order: %#v",got)
    }
    if !got.GitBlobsVerified || !got.SourceClassificationsVerified ||
        !got.AdvisoryOnly || got.OriginalExperimentalBytesAuthenticated ||
        got.CandidateMechanismLinkageAuthenticated || got.ScientificAccepted ||
        got.ScientificFirstUseAuthorized || got.DispatchAuthorized || got.AcceptedRefMutation {
        t.Fatalf("invalid authorization/source witness: %#v",got)
    }
    again,err:=PreviewRARPlanning(index,g78,g33,proposed)
    if err!=nil || !reflect.DeepEqual(got,again) {t.Fatal("nondeterministic advisory",err)}
}
func TestRARG99UnlinkedHypothesesCannotBeRejectedByReplay(t *testing.T) {
    index,g78,g33:=rarG99Inputs(t)
    unlinked:=[]RARHypothesis{{ID:"native-learning-question"},{ID:"independent-new-control"}}
    p,err:=PreviewRARPlanning(index,g78,g33,unlinked)
    if err!=nil || p.InputOrderChanged || len(p.Choices)!=2 {t.Fatal("unlinked hypotheses reordered",err)}
    for _,c:=range p.Choices {
        if c.Advisory!="NO_INDEXED_REPLAY_FINDING"{t.Fatal("unlinked hypothesis misclassified")}
    }
}
func TestRARG99RejectSourceByteOrIndexDrift(t *testing.T) {
    index,g78,g33:=rarG99Inputs(t)
    candidates:=[]RARHypothesis{{ID:"same-replay",PriorResearchID:"RAR-G7"}}
    if _,e:=PreviewRARPlanning(index,append(append([]byte(nil),g78...), ' '),g33,candidates);e==nil {
        t.Fatal("changed G7/G8 source accepted")
    }
    if _,e:=PreviewRARPlanning(index,g78,append(append([]byte(nil),g33...), ' '),candidates);e==nil {
        t.Fatal("changed G33 source accepted")
    }
    var doc Input
    if err:=json.Unmarshal(index,&doc);err!=nil{t.Fatal(err)}
    doc.Candidates[0].Outcome="POSITIVE"
    raw,err:=json.Marshal(doc)
    if err!=nil{t.Fatal(err)}
    if _,e:=PreviewRARPlanning(raw,g78,g33,candidates);e==nil {t.Fatal("forged positive accepted")}
}
func TestRARG99RejectUnprovenMappingAndMalformedHypotheses(t *testing.T) {
    index,g78,g33:=rarG99Inputs(t)
    for _,v:=range [][]RARHypothesis{
        nil,
        {{ID:"foo",PriorResearchID:"RAR-G404"}},
        {{ID:"duplicate"},{ID:"duplicate"}},
        {{ID:"../invalid"}},
    } {
        if _,err:=PreviewRARPlanning(index,g78,g33,v);err==nil {
            t.Fatalf("unbounded hypothesis accepted: %#v",v)
        }
    }
}
