//go:build !linux && !windows

package lcrm01

import "errors"
func O2ProcessMetrics()(int64,int64,error){
    return 0,0,errors.New("O2_PROCESS_RESOURCE_MEASUREMENT_UNSUPPORTED")
}
