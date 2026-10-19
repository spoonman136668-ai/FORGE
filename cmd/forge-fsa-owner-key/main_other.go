//go:build !windows

package main

import (
 "fmt"
 "os"
)
func main(){fmt.Fprintln(os.Stderr,"FSA_OWNER_KEY_STOP: Windows CurrentUser DPAPI required");os.Exit(1)}
