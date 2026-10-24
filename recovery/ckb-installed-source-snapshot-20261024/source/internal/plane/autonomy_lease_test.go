package plane

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"
)

func TestAutonomyRepositoryLeaseFencing(t *testing.T) {
	for _, scenario := range []string{"foreign-owner", "expired-owner", "missing", "cas-conflict", "invalid"} {
		t.Run(scenario, func(t *testing.T) {
			p, _ := setup(t)
			m := newGitHubMailbox(bridgeTestConfig(), "fixture-only")
			expiry := time.Now().Add(-time.Minute)
			if scenario == "foreign-owner" {
				expiry = time.Now().Add(time.Minute)
			}
			raw, _ := json.Marshal(planeLease{Schema: "ckb-plane.authority-lease.v1", Owner: "another-plane", Expires: expiry})
			if scenario == "invalid" {
				raw = []byte(`{"schema":"unknown"}`)
			}
			blob := bridgeBlobSHA(raw)
			writes := 0
			m.client.Transport = bridgeRoundTrip(func(r *http.Request) (*http.Response, error) {
				status, body := 200, "{}"
				if r.Method == "GET" {
					if scenario == "missing" {
						status = 404
					} else {
						b, _ := json.Marshal(bridgeGitContent{SHA: blob, Encoding: "base64", Size: len(raw), Content: base64.StdEncoding.EncodeToString(raw)})
						body = string(b)
					}
				} else {
					writes++
					var payload struct {
						SHA     string `json:"sha"`
						Branch  string `json:"branch"`
						Content string `json:"content"`
					}
					if e := json.NewDecoder(r.Body).Decode(&payload); e != nil {
						t.Fatal(e)
					}
					if payload.Branch != "ckb-plane/webui-mailbox" {
						t.Fatal(payload)
					}
					if scenario != "missing" && payload.SHA != blob {
						t.Fatal("lease update lacks CAS binding")
					}
					next, _ := base64.StdEncoding.DecodeString(payload.Content)
					var lease planeLease
					if e := json.Unmarshal(next, &lease); e != nil || !strings.HasPrefix(lease.Owner, p.setting("installation_id")+":") || !lease.Expires.After(time.Now()) {
						t.Fatal(string(next), e)
					}
					if scenario == "cas-conflict" && writes == 1 {
						status = 409
					}
				}
				return &http.Response{StatusCode: status, Body: io.NopCloser(strings.NewReader(body)), Header: make(http.Header)}, nil
			})
			e := p.renewPlaneLeaseWithMailbox(context.Background(), m)
			success := scenario == "expired-owner" || scenario == "missing" || scenario == "cas-conflict"
			if (e == nil) != success {
				t.Fatal(e)
			}
			if (scenario == "foreign-owner" || scenario == "invalid") && writes != 0 {
				t.Fatal("wrote a refused lease")
			}
			if success && p.setting("authority_verified_at") == "" {
				t.Fatal("verification not recorded")
			}
		})
	}
}
