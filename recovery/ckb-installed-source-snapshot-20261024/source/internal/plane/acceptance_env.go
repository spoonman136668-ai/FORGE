package plane

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// Build output must not share the frozen candidate tree or another invocation's
// cache. Only this fresh temporary root is added to sandbox write permissions.
func acceptanceEnv() ([]string, string, error) {
	root, err := os.MkdirTemp("", "ckb-plane-go-")
	if err != nil {
		return nil, "", err
	}
	root, err = filepath.Abs(root)
	if err != nil {
		return nil, "", err
	}
	for _, name := range []string{"cache", "tmp"} {
		if err = os.Mkdir(filepath.Join(root, name), 0700); err != nil {
			os.RemoveAll(root)
			return nil, "", err
		}
	}
	env := minimalEnv()
	// Replace, rather than append, inherited TEMP/TMP entries on Windows.
	env = replaceEnv(env, map[string]string{
		"GOFLAGS": "-buildvcs=false", "GOENV": "off", "GOWORK": "off",
		"GOTOOLCHAIN": "local", "GOPROXY": "off", "GOSUMDB": "off",
		"GOCACHE": filepath.Join(root, "cache"), "GOTMPDIR": filepath.Join(root, "tmp"),
		"TEMP": filepath.Join(root, "tmp"), "TMP": filepath.Join(root, "tmp"),
	})
	return env, root, nil
}
func acceptanceSandboxArgs(tool, root string, args []string) []string {
	// JSON string arrays are also TOML arrays; encoding preserves Windows slashes
	// and spaces without passing the command through a shell.
	roots, _ := json.Marshal([]string{root})
	out := append(policyArgs(), "-c", fmt.Sprintf("sandbox_workspace_write.writable_roots=%s", roots))
	out = append(out, "sandbox", "windows", "--", filepath.Clean(tool))
	return append(out, args...)
}

func replaceEnv(env []string, values map[string]string) []string {
	out := []string{}
	for _, entry := range env {
		key, _, _ := strings.Cut(entry, "=")
		if _, replaced := values[strings.ToUpper(key)]; !replaced {
			out = append(out, entry)
		}
	}
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	for _, key := range keys {
		out = append(out, key+"="+values[key])
	}
	return out
}
