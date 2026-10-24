package plane

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"strings"
	"sync"
	"testing"
	"time"
)

func TestAutonomyRepositoryLeaseSamePlaneRenewalsSerialize(t *testing.T) {
	p, _ := setup(t)
	m := newGitHubMailbox(bridgeTestConfig(), "fixture-only")

	host, _ := os.Hostname()
	owner := p.setting("installation_id") + ":" + digest([]byte(host+"|"+p.Root))
	leaseRaw, _ := json.Marshal(planeLease{
		Schema:  "ckb-plane.authority-lease.v1",
		Owner:   owner,
		Expires: time.Now().Add(time.Minute),
	})

	var stateMu sync.Mutex
	currentRaw := leaseRaw
	currentSHA := bridgeBlobSHA(currentRaw)
	getCount := 0
	putCount := 0
	secondGetSeen := make(chan struct{})
	var secondGetOnce sync.Once

	m.client.Transport = bridgeRoundTrip(func(r *http.Request) (*http.Response, error) {
		switch r.Method {
		case http.MethodGet:
			stateMu.Lock()
			getCount++
			if getCount == 2 {
				secondGetOnce.Do(func() { close(secondGetSeen) })
			}
			body, _ := json.Marshal(bridgeGitContent{
				SHA:      currentSHA,
				Encoding: "base64",
				Size:     len(currentRaw),
				Content:  base64.StdEncoding.EncodeToString(currentRaw),
			})
			stateMu.Unlock()
			return &http.Response{
				StatusCode: http.StatusOK,
				Body:       io.NopCloser(strings.NewReader(string(body))),
				Header:     make(http.Header),
			}, nil

		case http.MethodPut:
			var payload struct {
				SHA     string `json:"sha"`
				Content string `json:"content"`
			}
			if e := json.NewDecoder(r.Body).Decode(&payload); e != nil {
				return nil, e
			}
			nextRaw, e := base64.StdEncoding.DecodeString(payload.Content)
			if e != nil {
				return nil, e
			}

			stateMu.Lock()
			putCount++
			thisPut := putCount
			stateMu.Unlock()

			// Without same-process serialization the first renewal pauses here,
			// allowing the second renewal to read the same SHA. One of the two
			// PUTs then loses the CAS race. With serialization, the timeout lets
			// the first renewal finish before the second GET can occur.
			if thisPut == 1 {
				select {
				case <-secondGetSeen:
				case <-time.After(50 * time.Millisecond):
				}
			}

			stateMu.Lock()
			defer stateMu.Unlock()
			if payload.SHA != currentSHA {
				return &http.Response{
					StatusCode: http.StatusConflict,
					Body:       io.NopCloser(strings.NewReader(`{"message":"sha mismatch"}`)),
					Header:     make(http.Header),
				}, nil
			}
			currentRaw = nextRaw
			currentSHA = bridgeBlobSHA(currentRaw)
			return &http.Response{
				StatusCode: http.StatusOK,
				Body:       io.NopCloser(strings.NewReader(`{}`)),
				Header:     make(http.Header),
			}, nil
		default:
			return &http.Response{
				StatusCode: http.StatusMethodNotAllowed,
				Body:       io.NopCloser(strings.NewReader(`{}`)),
				Header:     make(http.Header),
			}, nil
		}
	})

	start := make(chan struct{})
	errs := make(chan error, 2)
	for i := 0; i < 2; i++ {
		go func() {
			<-start
			errs <- p.renewPlaneLeaseWithMailbox(context.Background(), m)
		}()
	}
	close(start)

	for i := 0; i < 2; i++ {
		if e := <-errs; e != nil {
			t.Fatalf("same-plane concurrent renewal failed: %v", e)
		}
	}

	stateMu.Lock()
	defer stateMu.Unlock()
	if getCount != 2 || putCount != 2 {
		t.Fatalf("expected two serialized renewals, gets=%d puts=%d", getCount, putCount)
	}
	if p.setting("authority_verified_at") == "" {
		t.Fatal("verification not recorded")
	}
}
