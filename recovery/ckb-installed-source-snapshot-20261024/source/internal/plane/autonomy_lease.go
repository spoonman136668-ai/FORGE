package plane

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"net/url"
	"os"
	"sync"
	"time"
)

var planeLeaseRenewalMu sync.Mutex

type planeLease struct {
	Schema  string    `json:"schema"`
	Owner   string    `json:"owner"`
	Expires time.Time `json:"expires_at"`
}

func (p *Engine) renewPlaneLease(ctx context.Context) error {
	c := p.Config.Autonomy
	m := newGitHubMailbox(BridgeConfig{Repository: c.Repository}, os.Getenv("CKB_PLANE_GITHUB_TOKEN"))
	return p.renewPlaneLeaseWithMailbox(ctx, m)
}

func (p *Engine) renewPlaneLeaseWithMailboxOnce(ctx context.Context, m *gitHubMailbox) error {
	// Lease renewal is a read-modify-write CAS against one repository lease.
	// The autonomy controller and deterministic acceptance can verify authority
	// concurrently; serialize same-process renewals so they cannot race on the
	// same GitHub contents SHA and falsely report PLANE_AUTHORITY_LOST.
	planeLeaseRenewalMu.Lock()
	defer planeLeaseRenewalMu.Unlock()

	endpoint := "/contents/bridge/authority/lease.json"
	branch := "ckb-plane/webui-mailbox"
	var existing bridgeGitContent
	status, e := m.api(ctx, "GET", endpoint+"?ref="+url.QueryEscape(branch), nil, &existing)
	owner := p.setting("installation_id")
	host, _ := os.Hostname()
	owner += ":" + digest([]byte(host+"|"+p.Root))
	if e == nil {
		raw, e := decodeGitContent(existing)
		if e != nil {
			return e
		}
		var lease planeLease
		if e = bridgeDecode(raw, &lease); e != nil || lease.Schema != "ckb-plane.authority-lease.v1" || lease.Owner == "" || lease.Expires.IsZero() {
			return errors.New("AUTHORITY_LEASE_INVALID")
		}
		if lease.Owner != owner && lease.Expires.After(time.Now()) {
			return errors.New("ANOTHER_PLANE_OWNS_REPOSITORY")
		}
	} else if status != 404 {
		return e
	}
	raw, _ := json.Marshal(planeLease{Schema: "ckb-plane.authority-lease.v1", Owner: owner, Expires: time.Now().UTC().Add(2 * time.Minute)})
	payload := map[string]any{"message": "Renew CKB-plane authority lease [skip ci]", "branch": branch, "content": base64.StdEncoding.EncodeToString(raw)}
	if existing.SHA != "" {
		payload["sha"] = existing.SHA
	}
	if status, e = m.api(ctx, "PUT", endpoint, payload, nil); e != nil {
		if status == 409 {
			return errors.New("AUTHORITY_LEASE_CAS_CONFLICT")
		}
		return errors.New("AUTHORITY_LEASE_NOT_ACQUIRED")
	}
	return p.setSetting("authority_verified_at", now())
}
func (p *Engine) renewPlaneLeaseWithMailbox(ctx context.Context, m *gitHubMailbox) error {
	const maxCASAttempts = 3
	for attempt := 0; attempt < maxCASAttempts; attempt++ {
		e := p.renewPlaneLeaseWithMailboxOnce(ctx, m)
		if e == nil {
			return nil
		}
		if e.Error() != "AUTHORITY_LEASE_CAS_CONFLICT" {
			return e
		}
		if attempt == maxCASAttempts-1 {
			return errors.New("AUTHORITY_LEASE_NOT_ACQUIRED")
		}
		select {
		case <-ctx.Done():
			return errors.New("AUTHORITY_LEASE_NOT_ACQUIRED")
		case <-time.After(time.Duration(attempt+1) * 25 * time.Millisecond):
		}
	}
	return errors.New("AUTHORITY_LEASE_NOT_ACQUIRED")
}
