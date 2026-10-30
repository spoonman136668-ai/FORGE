//go:build linux

package main

import (
	"fmt"
	"os"
	"strconv"
	"strings"
)
func peakResidentBytes()(uint64,error){
	b,err:=os.ReadFile("/proc/self/status");if err!=nil{return 0,err}
	for _,line:=range strings.Split(string(b),"\n"){
		if strings.HasPrefix(line,"VmHWM:"){
			f:=strings.Fields(line)
			if len(f)!=3 || f[2]!="kB"{return 0,fmt.Errorf("invalid VmHWM: %q",line)}
			n,e:=strconv.ParseUint(f[1],10,64);if e!=nil{return 0,e}
			return n*1024,nil
		}
	}
	return 0,fmt.Errorf("missing /proc/self/status VmHWM")
}
