package plane

import (
	"strings"
	"testing"
)

func TestRoadmapSuccessorCurrentFrontierPolicy(t *testing.T) {
	c, err := loadRoadmapSuccessorCatalog()
	if err != nil {
		t.Fatal(err)
	}
	if len(c.Entries) != 18 {
		t.Fatalf("entries=%d", len(c.Entries))
	}
	if c.Entries[0].Key != "BTV-03" ||
		c.Entries[0].ID != "V11110_POSTKCH_KTRADE_BTV03_MULTI_SYMBOL_PORTFOLIO_PINE_R1" ||
		c.Entries[0].ParentID != "V11110_POSTKCH_KTRADE_BTV02_REPAINT_LOOKAHEAD_MTF_CAUSALITY_INSPECTOR_R1" {
		t.Fatalf("unexpected post-BTV frontier: %#v", c.Entries[0])
	}
	for i := 1; i < len(c.Entries); i++ {
		if c.Entries[i].ParentID != c.Entries[i-1].ID {
			t.Fatalf("entry[%d] parent=%s previous=%s", i, c.Entries[i].ParentID, c.Entries[i-1].ID)
		}
	}
	for i := 0; i < 17; i++ {
		if !c.Entries[i].AutoAuthorized {
			t.Fatalf("%s must remain auto-authorized", c.Entries[i].Key)
		}
	}
	last := c.Entries[len(c.Entries)-1]
	if last.Key != "LIVE-PROMOTION" || last.AutoAuthorized ||
		!strings.Contains(last.OperatorReason, "Live promotion") {
		t.Fatalf("protected boundary invalid: %#v", last)
	}
}

func TestRoadmapSuccessorCompatibilityParentExceptionIsNarrow(t *testing.T) {
	c, err := loadRoadmapSuccessorCatalog()
	if err != nil {
		t.Fatal(err)
	}
	first := c.Entries[0]
	if first.ParentID != "V11110_POSTKCH_KTRADE_BTV02_REPAINT_LOOKAHEAD_MTF_CAUSALITY_INSPECTOR_R1" {
		t.Fatalf("unexpected compatibility parent: %s", first.ParentID)
	}
	for i := 1; i < len(c.Entries); i++ {
		if c.Entries[i].ParentID != c.Entries[i-1].ID {
			t.Fatalf("compatibility exception leaked beyond first entry at %d", i)
		}
	}
}
