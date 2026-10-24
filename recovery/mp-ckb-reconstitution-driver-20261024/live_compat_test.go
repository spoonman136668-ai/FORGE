package plane

import (
	"os"
	"testing"
)

func TestMPReconstitutionLiveCompatibility(t *testing.T) {
	cfgPath := os.Getenv("MP_RECON_LIVE_CONFIG")
	liveRoot := os.Getenv("MP_RECON_LIVE_ROOT")
	snapshot := os.Getenv("MP_RECON_DB_SNAPSHOT")
	if cfgPath == "" || liveRoot == "" || snapshot == "" {
		t.Fatal("missing compatibility environment")
	}
	c, err := LoadConfig(cfgPath)
	if err != nil {
		t.Fatalf("LIVE_CONFIG_PARSE_FAILED: %v", err)
	}
	c.State.SQLitePath = snapshot
	p, err := NewEngine(c, liveRoot)
	if err != nil {
		t.Fatalf("LIVE_ENGINE_INIT_FAILED: %v", err)
	}
	defer p.Store.DB.Close()
}
