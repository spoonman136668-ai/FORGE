package plane

import (
	"os"
	"testing"
)

func TestMPReconstitutedLiveCompatibility(t *testing.T) {
	cfgPath := os.Getenv("MP_LIVE_CONFIG_COPY")
	liveRoot := os.Getenv("MP_LIVE_ROOT")
	snap := os.Getenv("MP_LIVE_DB_SNAPSHOT")
	if cfgPath == "" || liveRoot == "" || snap == "" {
		t.Fatal("missing compatibility environment")
	}
	c, err := LoadConfig(cfgPath)
	if err != nil {
		t.Fatalf("LIVE_CONFIG_PARSE_FAILED: %v", err)
	}
	c.State.SQLitePath = snap
	p, err := NewEngine(c, liveRoot)
	if err != nil {
		t.Fatalf("LIVE_ENGINE_INIT_FAILED: %v", err)
	}
	defer p.Store.DB.Close()
}
