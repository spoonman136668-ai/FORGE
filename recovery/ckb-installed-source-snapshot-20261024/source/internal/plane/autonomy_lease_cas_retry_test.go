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

func TestAutonomyRepositoryLeaseTransientCASConflictRetries(t *testing.T) {
	p, _ := setup(t)
	m := newGitHubMailbox(bridgeTestConfig(), "fixture-only")
	raw, _ := json.Marshal(planeLease{Schema: "ckb-plane.authority-lease.v1", Owner: "expired-plane", Expires: time.Now().Add(-time.Minute)})
	blob := bridgeBlobSHA(raw)
	reads := 0
	writes := 0

	m.client.Transport = bridgeRoundTrip(func(r *http.Request) (*http.Response, error) {
		status, body := 200, "{}"
		switch r.Method {
		case "GET":
			reads++
			b, _ := json.Marshal(bridgeGitContent{SHA: blob, Encoding: "base64", Size: len(raw), Content: base64.StdEncoding.EncodeToString(raw)})
			body = string(b)
		case "PUT":
			writes++
			var payload struct {
				SHA     string `json:"sha"`
				Branch  string `json:"branch"`
				Content string `json:"content"`
			}
			if e := json.NewDecoder(r.Body).Decode(&payload); e != nil {
				t.Fatal(e)
			}
			if payload.Branch != "ckb-plane/webui-mailbox" || payload.SHA != blob {
				t.Fatal("lease retry lost branch/CAS fencing")
			}
			next, _ := base64.StdEncoding.DecodeString(payload.Content)
			var lease planeLease
			if e := json.Unmarshal(next, &lease); e != nil || !strings.HasPrefix(lease.Owner, p.setting("installation_id")+":") || !lease.Expires.After(time.Now()) {
				t.Fatal(string(next), e)
			}
			if writes == 1 {
				status = 409
			}
		}
		return &http.Response{StatusCode: status, Body: io.NopCloser(strings.NewReader(body)), Header: make(http.Header)}, nil
	})

	if e := p.renewPlaneLeaseWithMailbox(context.Background(), m); e != nil {
		t.Fatal(e)
	}
	if reads != 2 || writes != 2 {
		t.Fatalf("expected one bounded CAS retry, reads=%d writes=%d", reads, writes)
	}
	if p.setting("authority_verified_at") == "" {
		t.Fatal("successful retried lease did not record verification")
	}
}

func TestAutonomyRepositoryLeasePersistentCASConflictFailsClosed(t *testing.T) {
	p, _ := setup(t)
	m := newGitHubMailbox(bridgeTestConfig(), "fixture-only")
	raw, _ := json.Marshal(planeLease{Schema: "ckb-plane.authority-lease.v1", Owner: "expired-plane", Expires: time.Now().Add(-time.Minute)})
	blob := bridgeBlobSHA(raw)
	reads := 0
	writes := 0

	m.client.Transport = bridgeRoundTrip(func(r *http.Request) (*http.Response, error) {
		status, body := 200, "{}"
		if r.Method == "GET" {
			reads++
			b, _ := json.Marshal(bridgeGitContent{SHA: blob, Encoding: "base64", Size: len(raw), Content: base64.StdEncoding.EncodeToString(raw)})
			body = string(b)
		} else {
			writes++
			status = 409
		}
		return &http.Response{StatusCode: status, Body: io.NopCloser(strings.NewReader(body)), Header: make(http.Header)}, nil
	})

	e := p.renewPlaneLeaseWithMailbox(context.Background(), m)
	if e == nil || e.Error() != "AUTHORITY_LEASE_NOT_ACQUIRED" {
		t.Fatal(e)
	}
	if reads != 3 || writes != 3 {
		t.Fatalf("persistent conflict did not stop at bounded retry limit: reads=%d writes=%d", reads, writes)
	}
}

func TestAutonomyRepositoryLeaseRevalidatesForeignOwnerAfterConflict(t *testing.T) {
	p, _ := setup(t)
	m := newGitHubMailbox(bridgeTestConfig(), "fixture-only")
	expiredRaw, _ := json.Marshal(planeLease{Schema: "ckb-plane.authority-lease.v1", Owner: "expired-plane", Expires: time.Now().Add(-time.Minute)})
	expiredBlob := bridgeBlobSHA(expiredRaw)
	foreignRaw, _ := json.Marshal(planeLease{Schema: "ckb-plane.authority-lease.v1", Owner: "another-plane", Expires: time.Now().Add(time.Minute)})
	foreignBlob := bridgeBlobSHA(foreignRaw)
	reads := 0
	writes := 0

	m.client.Transport = bridgeRoundTrip(func(r *http.Request) (*http.Response, error) {
		status, body := 200, "{}"
		if r.Method == "GET" {
			reads++
			raw, blob := expiredRaw, expiredBlob
			if reads > 1 {
				raw, blob = foreignRaw, foreignBlob
			}
			b, _ := json.Marshal(bridgeGitContent{SHA: blob, Encoding: "base64", Size: len(raw), Content: base64.StdEncoding.EncodeToString(raw)})
			body = string(b)
		} else {
			writes++
			status = 409
		}
		return &http.Response{StatusCode: status, Body: io.NopCloser(strings.NewReader(body)), Header: make(http.Header)}, nil
	})

	e := p.renewPlaneLeaseWithMailbox(context.Background(), m)
	if e == nil || e.Error() != "ANOTHER_PLANE_OWNS_REPOSITORY" {
		t.Fatal(e)
	}
	if reads != 2 || writes != 1 {
		t.Fatalf("foreign owner was not revalidated before retry write: reads=%d writes=%d", reads, writes)
	}
}
