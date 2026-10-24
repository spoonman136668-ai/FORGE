package plane

import (
	"context"
	"errors"
	"os/exec"
	"regexp"
	"strings"
	"time"
)

// Windows CLI builds have exposed both a platform subcommand and a native
// command-tail form. Select only a syntax advertised by the installed CLI;
// neither form changes the fixed permission policy.
func detectSandboxSyntax(tool, home string) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, tool, "sandbox", "--help")
	cmd.Env = replaceEnv(minimalEnv(), map[string]string{"CODEX_HOME": home})
	cmd.WaitDelay = 2 * time.Second
	out, e := cmd.CombinedOutput()
	if e != nil || len(out) > 128<<10 {
		return "", errors.New("SANDBOX_HELP_UNAVAILABLE")
	}
	text := strings.ToLower(string(out))
	if regexp.MustCompile(`(?m)^\s+windows\s`).MatchString(text) {
		return "windows-subcommand", nil
	}
	if strings.Contains(text, "usage:") && strings.Contains(text, "sandbox") && (strings.Contains(text, "<command>") || strings.Contains(text, "<command>...") || strings.Contains(text, "[command]") || strings.Contains(text, "[command]...")) && !strings.Contains(text, "commands:") {
		return "native", nil
	}
	return "", errors.New("SANDBOX_SYNTAX_UNRECOGNIZED")
}
func (p *Engine) sandboxArgs(args []string) []string {
	if p.Config.Autonomy.Enabled && p.Config.Execution.SandboxSyntax == "native" {
		copyArgs := append([]string{}, args...)
		for i := 0; i+1 < len(copyArgs); i++ {
			if copyArgs[i] == "sandbox" && copyArgs[i+1] == "windows" {
				return append(copyArgs[:i+1], copyArgs[i+2:]...)
			}
		}
	}
	return args
}
