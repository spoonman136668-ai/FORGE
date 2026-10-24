//go:build !windows && !linux

package plane

import (
	"errors"
	"os"
)

func lockFile(f *os.File) error { return errors.New("unsupported platform") }
func processAlive(pid int) bool { return true }
