package plane

import (
	"context"
	"encoding/json"
	"testing"
)

func objectiveHasCapability(values []string, want string) bool {
	for _, v := range values {
		if v == want {
			return true
		}
	}
	return false
}

func TestObjectiveConsecutivePrioritySteeringPersists(t *testing.T) {
	p, plan := objectiveFixture(t, 1)
	o := ocCreate(t, p, plan)

	first := 10
	v, e := p.ObjectiveControl(context.Background(), 1, ObjectiveRequest{Action: "priority", ID: o.ID, ExpectedRevision: o.Revision, Priority: &first})
	if e != nil {
		t.Fatal(e)
	}
	one := v.(Objective)
	if one.Priority != first {
		t.Fatalf("first priority response=%d want=%d", one.Priority, first)
	}
	one = ocGet(t, p, o.ID)
	if one.Priority != first || one.LastSteeringRevision != one.Revision {
		t.Fatalf("first priority not durable: %+v", one)
	}

	second := 20
	v, e = p.ObjectiveControl(context.Background(), 1, ObjectiveRequest{Action: "priority", ID: o.ID, ExpectedRevision: one.Revision, Priority: &second})
	if e != nil {
		t.Fatal(e)
	}
	two := v.(Objective)
	if two.Priority != second {
		t.Fatalf("second priority response=%d want=%d", two.Priority, second)
	}
	two = ocGet(t, p, o.ID)
	if two.Priority != second || two.Revision != one.Revision+1 || two.LastSteeringRevision != two.Revision {
		t.Fatalf("second priority not durable: before=%+v after=%+v", one, two)
	}
}

func TestObjectiveCapabilityAdvertisementTracksFeatureGate(t *testing.T) {
	for _, tc := range []struct {
		name    string
		enabled bool
	}{
		{name: "enabled", enabled: true},
		{name: "disabled", enabled: false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			p, _ := objectiveFixture(t, 1)
			p.Config.Autonomy.ObjectiveController = tc.enabled
			b, m := bridgeTest(t)
			b.Config.ControlEnabled = true
			p.AttachBridge(b)

			view, e := b.snapshot(context.Background(), BridgeCommand{Action: "ping"})
			if e != nil {
				t.Fatal(e)
			}
			caps, ok := view.(map[string]any)["capabilities"].([]string)
			if !ok {
				t.Fatalf("ping capabilities type=%T", view.(map[string]any)["capabilities"])
			}
			if got := objectiveHasCapability(caps, "objective"); got != tc.enabled {
				t.Fatalf("ping objective capability=%v want=%v capabilities=%v", got, tc.enabled, caps)
			}

			if e = b.Once(context.Background()); e != nil {
				t.Fatal(e)
			}
			var heartbeat struct {
				Capabilities []string `json:"capabilities"`
			}
			if e = json.Unmarshal(m.output["status/heartbeat.json"], &heartbeat); e != nil {
				t.Fatal(e)
			}
			if got := objectiveHasCapability(heartbeat.Capabilities, "objective"); got != tc.enabled {
				t.Fatalf("heartbeat objective capability=%v want=%v capabilities=%v", got, tc.enabled, heartbeat.Capabilities)
			}
		})
	}
}
