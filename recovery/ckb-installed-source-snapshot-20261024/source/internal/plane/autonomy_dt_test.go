package plane

import (
	"context"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"
)

func TestDTNativeExportActionExportsAcceptedCandidate(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "DT_NATIVE_EXPORT")

	if e := p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}
	j := wait(t, p, q.ID)
	if j.State != "ACCEPTED" {
		t.Fatalf("candidate was not accepted: %+v", j)
	}
	if e := p.AutonomyTick(context.Background()); e != nil {
		t.Fatal(e)
	}

	v, e := p.HandleNative(context.Background(), NativeRequest{Action: "export", ID: q.ID})
	if e != nil {
		t.Fatal(e)
	}
	out, ok := v.(map[string]any)
	if !ok {
		t.Fatalf("unexpected native export payload: %#v", v)
	}
	if out["published"] != false || out["accepted_ref_mutated"] != false {
		t.Fatalf("export changed publication policy: %#v", out)
	}
	bundle, _ := out["bundle"].(string)
	if !strings.Contains(bundle, q.ID) || !strings.HasSuffix(bundle, "candidate.bundle") {
		t.Fatalf("unexpected bundle path: %#v", out)
	}

	again, e := p.HandleNative(context.Background(), NativeRequest{Action: "export", ID: q.ID})
	if e != nil {
		t.Fatal("idempotent native export", e)
	}
	if jsonText(again) != jsonText(out) {
		t.Fatalf("native export must be idempotent: first=%s second=%s", jsonText(out), jsonText(again))
	}
}

func TestDTNativeExportRequiresAcceptedCandidate(t *testing.T) {
	p, w := setup(t)
	testAuthority(p)
	q := sourceQueue(t, p, w, "DT_NATIVE_EXPORT_REJECTS_UNACCEPTED")

	for _, id := range []string{q.ID, "DT_NATIVE_EXPORT_MISSING_LOCAL_JOB"} {
		if _, e := p.HandleNative(context.Background(), NativeRequest{Action: "export", ID: id}); e == nil || !strings.Contains(e.Error(), "LOCAL_ACCEPTANCE_REQUIRED") {
			t.Fatalf("expected local acceptance guard for %s, got %v", id, e)
		}
	}

	draft := w
	draft.ID = "DT_NATIVE_EXPORT_DRAFT_LOCAL_JOB"
	draft.Worker.Branch = "codex/dt-native-export-draft-local-job"
	draftRaw, e := yaml.Marshal(draft)
	if e != nil {
		t.Fatal(e)
	}
	if e := p.Store.Load(draftRaw); e != nil {
		t.Fatal(e)
	}
	if _, e := p.HandleNative(context.Background(), NativeRequest{Action: "export", ID: draft.ID}); e == nil || !strings.Contains(e.Error(), "LOCAL_ACCEPTANCE_REQUIRED") {
		t.Fatalf("expected local acceptance guard for draft local job, got %v", e)
	}
}
