//go:build !windows && !linux

package plane

import (
	"errors"
	"os/exec"
)

func configureHost(cmd *exec.Cmd) {}
func containHost() error          { return errors.New("unsupported host platform") }
