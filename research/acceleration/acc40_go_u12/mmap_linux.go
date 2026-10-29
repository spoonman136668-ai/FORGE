//go:build linux

package main

import (
	"os"
	"syscall"
)
func mapFile(f *os.File,n int)([]byte,error){
	return syscall.Mmap(int(f.Fd()),0,n,syscall.PROT_READ,syscall.MAP_SHARED)
}
func unmapFile(b []byte)error{return syscall.Munmap(b)}
