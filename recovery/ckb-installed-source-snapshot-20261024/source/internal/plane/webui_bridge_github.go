package plane

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"sort"
	"strings"
	"time"
)

type gitHubMailbox struct {
	cfg    BridgeConfig
	token  string
	client *http.Client
}

func newGitHubMailbox(c BridgeConfig, token string) *gitHubMailbox {
	return &gitHubMailbox{cfg: c, token: token, client: &http.Client{Timeout: 30 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return errors.New("BRIDGE_REDIRECT_REFUSED") }}}
}

func (m *gitHubMailbox) api(ctx context.Context, method, endpoint string, payload any, output any) (int, error) {
	var body io.Reader
	if payload != nil {
		b, e := json.Marshal(payload)
		if e != nil {
			return 0, e
		}
		body = bytes.NewReader(b)
	}
	req, e := http.NewRequestWithContext(ctx, method, "https://api.github.com/repos/"+m.cfg.Repository+endpoint, body)
	if e != nil {
		return 0, errors.New("BRIDGE_REQUEST_INVALID")
	}
	req.Header.Set("Authorization", "Bearer "+m.token)
	req.Header.Set("Accept", "application/vnd.github+json")
	req.Header.Set("X-GitHub-Api-Version", "2022-11-28")
	req.Header.Set("User-Agent", "ckb-plane/"+BridgeVersion)
	if payload != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	res, e := m.client.Do(req)
	if e != nil {
		return 0, errors.New("BRIDGE_GITHUB_UNAVAILABLE")
	}
	defer res.Body.Close()
	if res.StatusCode < 200 || res.StatusCode >= 300 {
		// Do not copy error bodies, request headers, tokens or URLs into evidence.
		return res.StatusCode, fmt.Errorf("BRIDGE_GITHUB_HTTP_%d", res.StatusCode)
	}
	b, e := io.ReadAll(io.LimitReader(res.Body, 2*1024*1024+1))
	if e != nil {
		return res.StatusCode, errors.New("BRIDGE_GITHUB_READ_FAILED")
	}
	if len(b) > 2*1024*1024 {
		return res.StatusCode, errors.New("BRIDGE_GITHUB_RESPONSE_TOO_LARGE")
	}
	if output != nil {
		if e = json.Unmarshal(b, output); e != nil {
			return res.StatusCode, errors.New("BRIDGE_GITHUB_RESPONSE_INVALID")
		}
	}
	return res.StatusCode, nil
}

func (m *gitHubMailbox) contentEndpoint(path string) string {
	parts := strings.Split("bridge/"+path, "/")
	for i := range parts {
		parts[i] = url.PathEscape(parts[i])
	}
	return "/contents/" + strings.Join(parts, "/") + "?ref=" + url.QueryEscape(m.cfg.Branch)
}

type bridgeGitContent struct {
	Name     string `json:"name"`
	Type     string `json:"type"`
	SHA      string `json:"sha"`
	Content  string `json:"content"`
	Encoding string `json:"encoding"`
	Size     int    `json:"size"`
}

func decodeGitContent(c bridgeGitContent) ([]byte, error) {
	if c.Encoding != "base64" || c.Size < 0 || c.Size > bridgeMaxBytes {
		return nil, errors.New("BRIDGE_GITHUB_CONTENT_INVALID")
	}
	b, e := base64.StdEncoding.DecodeString(strings.ReplaceAll(c.Content, "\n", ""))
	if e != nil || len(b) > bridgeMaxBytes || bridgeBlobSHA(b) != c.SHA {
		return nil, errors.New("BRIDGE_GITHUB_CONTENT_INTEGRITY")
	}
	return b, nil
}

func (m *gitHubMailbox) get(ctx context.Context, path string) ([]byte, string, int, error) {
	var c bridgeGitContent
	status, e := m.api(ctx, "GET", m.contentEndpoint(path), nil, &c)
	if e != nil {
		return nil, "", status, e
	}
	if c.Type != "file" {
		return nil, "", status, errors.New("BRIDGE_REGULAR_FILE_REQUIRED")
	}
	b, e := decodeGitContent(c)
	return b, c.SHA, status, e
}

func (m *gitHubMailbox) Verify(ctx context.Context, cfg BridgeConfig) error {
	var repo struct {
		ID       int64  `json:"id"`
		Private  bool   `json:"private"`
		FullName string `json:"full_name"`
		Archived bool   `json:"archived"`
	}
	if _, e := m.api(ctx, "GET", "", nil, &repo); e != nil {
		return e
	}
	if repo.ID != cfg.RepositoryID || !repo.Private || repo.Archived || !strings.EqualFold(repo.FullName, cfg.Repository) {
		return errors.New("BRIDGE_PRIVATE_REPOSITORY_IDENTITY_MISMATCH")
	}
	b, _, _, e := m.get(ctx, "mailbox.json")
	if e != nil {
		return e
	}
	var manifest struct {
		Schema    string `json:"schema"`
		PlaneID   string `json:"plane_id"`
		MailboxID string `json:"mailbox_id"`
		ReadOnly  bool   `json:"read_only"`
	}
	if e = bridgeDecode(b, &manifest); e != nil {
		return e
	}
	if (manifest.Schema != "ckb-plane.webui-mailbox.v1" && manifest.Schema != "ckb-plane.webui-mailbox.v2") || manifest.PlaneID != cfg.PlaneID || manifest.MailboxID != cfg.MailboxID || manifest.ReadOnly == cfg.ControlEnabled || (cfg.ControlEnabled && manifest.Schema != "ckb-plane.webui-mailbox.v2") {
		return errors.New("BRIDGE_MAILBOX_IDENTITY_MISMATCH")
	}
	return nil
}

func (m *gitHubMailbox) List(ctx context.Context) ([]bridgeEntry, error) {
	var files []bridgeGitContent
	_, e := m.api(ctx, "GET", m.contentEndpoint("inbox"), nil, &files)
	if e != nil {
		return nil, e
	}
	out := []bridgeEntry{}
	for _, f := range files {
		if !strings.HasSuffix(f.Name, ".json") {
			continue
		}
		if f.Type != "file" || !shaRE.MatchString(f.SHA) || f.Size > bridgeMaxBytes {
			return nil, errors.New("BRIDGE_INBOX_ENTRY_INVALID")
		}
		out = append(out, bridgeEntry{f.Name, f.SHA})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	if len(files) >= 1000 {
		return m.listInboxTree(ctx)
	}
	return out, nil
}

func (m *gitHubMailbox) listInboxTree(ctx context.Context) ([]bridgeEntry, error) {
	var ref struct {
		Object struct {
			SHA string `json:"sha"`
		} `json:"object"`
	}
	refPath := "/git/ref/heads/" + m.cfg.Branch
	if _, e := m.api(ctx, "GET", refPath, nil, &ref); e != nil {
		return nil, e
	}
	if !shaRE.MatchString(ref.Object.SHA) {
		return nil, errors.New("BRIDGE_GITHUB_REF_INVALID")
	}

	var commit struct {
		Tree struct {
			SHA string `json:"sha"`
		} `json:"tree"`
	}
	if _, e := m.api(ctx, "GET", "/git/commits/"+ref.Object.SHA, nil, &commit); e != nil {
		return nil, e
	}
	if !shaRE.MatchString(commit.Tree.SHA) {
		return nil, errors.New("BRIDGE_GITHUB_TREE_INVALID")
	}

	var tree struct {
		Truncated bool `json:"truncated"`
		Tree      []struct {
			Path string `json:"path"`
			Type string `json:"type"`
			SHA  string `json:"sha"`
			Size int    `json:"size"`
		} `json:"tree"`
	}
	if _, e := m.api(ctx, "GET", "/git/trees/"+commit.Tree.SHA+"?recursive=1", nil, &tree); e != nil {
		return nil, e
	}
	if tree.Truncated {
		return nil, errors.New("BRIDGE_GITHUB_TREE_TRUNCATED")
	}

	const prefix = "bridge/inbox/"
	out := []bridgeEntry{}
	for _, item := range tree.Tree {
		if !strings.HasPrefix(item.Path, prefix) {
			continue
		}
		name := strings.TrimPrefix(item.Path, prefix)
		if strings.Contains(name, "/") || !strings.HasSuffix(name, ".json") {
			continue
		}
		if item.Type != "blob" || !shaRE.MatchString(item.SHA) || item.Size < 0 || item.Size > bridgeMaxBytes {
			return nil, errors.New("BRIDGE_INBOX_ENTRY_INVALID")
		}
		out = append(out, bridgeEntry{Name: name, SHA: item.SHA})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	return out, nil
}

func (m *gitHubMailbox) Read(ctx context.Context, entry bridgeEntry) ([]byte, error) {
	if !shaRE.MatchString(entry.SHA) {
		return nil, errors.New("BRIDGE_BLOB_SHA_INVALID")
	}
	// Read the blob from the listing, not mutable branch contents a second time.
	var c bridgeGitContent
	if _, e := m.api(ctx, "GET", "/git/blobs/"+entry.SHA, nil, &c); e != nil {
		return nil, e
	}
	if c.SHA != entry.SHA {
		return nil, errors.New("BRIDGE_COMMAND_CONTENT_CHANGED")
	}
	return decodeGitContent(c)
}

func (m *gitHubMailbox) Publish(ctx context.Context, path string, raw []byte, replace bool) error {
	if len(raw) > bridgeMaxBytes || !safePath(path) {
		return errors.New("BRIDGE_OUTPUT_INVALID")
	}
	if replace {
		if path != "status/heartbeat.json" {
			return errors.New("BRIDGE_REPLACE_FORBIDDEN")
		}
	} else if !strings.HasPrefix(path, "outbox/") || !strings.HasSuffix(path, ".json") || !bridgeSegment.MatchString(strings.TrimSuffix(strings.TrimPrefix(path, "outbox/"), ".json")) {
		return errors.New("BRIDGE_OUTPUT_PATH_FORBIDDEN")
	}
	old, sha, status, e := m.get(ctx, path)
	if e == nil {
		if bytes.Equal(old, raw) {
			return nil
		}
		if !replace {
			return errors.New("BRIDGE_RESULT_CONFLICT")
		}
	} else if status != 404 {
		return e
	}
	payload := map[string]any{"message": "CKB-plane bridge result [skip ci]", "branch": m.cfg.Branch, "content": base64.StdEncoding.EncodeToString(raw)}
	if sha != "" {
		payload["sha"] = sha
	}
	endpoint := strings.Split(m.contentEndpoint(path), "?")[0]
	status, e = m.api(ctx, "PUT", endpoint, payload, nil)
	if e == nil {
		return nil
	}
	// Lost acknowledgement and racing creates must never overwrite a different result.
	if status == 409 || status == 422 || status == 0 {
		actual, _, _, readErr := m.get(ctx, path)
		if readErr == nil && bytes.Equal(actual, raw) {
			return nil
		}
	}
	return e
}

func bridgeArchivePath(entry bridgeEntry) (string, error) {
	id := strings.TrimSuffix(entry.Name, ".json")
	if !strings.HasSuffix(entry.Name, ".json") || !bridgeSegment.MatchString(id) || !shaRE.MatchString(entry.SHA) {
		return "", errors.New("BRIDGE_ARCHIVE_ENTRY_INVALID")
	}
	return "archive/inbox/" + entry.SHA[:2] + "/" + entry.SHA[2:4] + "/" + entry.Name, nil
}

func (m *gitHubMailbox) Archive(ctx context.Context, entry bridgeEntry) error {
	archivePath, e := bridgeArchivePath(entry)
	if e != nil {
		return e
	}

	raw, e := m.Read(ctx, entry)
	if e != nil {
		return e
	}

	archived, _, status, e := m.get(ctx, archivePath)
	if e == nil {
		if !bytes.Equal(archived, raw) {
			return errors.New("BRIDGE_ARCHIVE_CONFLICT")
		}
	} else if status == 404 {
		payload := map[string]any{
			"message": "CKB-plane bridge archive [skip ci]",
			"branch":  m.cfg.Branch,
			"content": base64.StdEncoding.EncodeToString(raw),
		}
		endpoint := strings.Split(m.contentEndpoint(archivePath), "?")[0]
		status, e = m.api(ctx, "PUT", endpoint, payload, nil)
		if e != nil {
			if status == 409 || status == 422 || status == 0 {
				actual, _, _, readErr := m.get(ctx, archivePath)
				if readErr == nil && bytes.Equal(actual, raw) {
					e = nil
				}
			}
			if e != nil {
				return e
			}
		}
	} else {
		return e
	}

	archived, _, _, e = m.get(ctx, archivePath)
	if e != nil || !bytes.Equal(archived, raw) {
		return errors.New("BRIDGE_ARCHIVE_VERIFY_FAILED")
	}

	inboxPath := "inbox/" + entry.Name
	endpoint := strings.Split(m.contentEndpoint(inboxPath), "?")[0]
	payload := map[string]any{
		"message": "CKB-plane bridge compact delivered inbox [skip ci]",
		"branch":  m.cfg.Branch,
		"sha":     entry.SHA,
	}
	status, e = m.api(ctx, "DELETE", endpoint, payload, nil)
	if e == nil || status == 404 {
		return nil
	}
	if status == 409 || status == 422 || status == 0 {
		_, currentSHA, currentStatus, readErr := m.get(ctx, inboxPath)
		if currentStatus == 404 {
			return nil
		}
		if readErr == nil && currentSHA != entry.SHA {
			return errors.New("BRIDGE_COMMAND_CONTENT_CHANGED")
		}
	}
	return e
}
