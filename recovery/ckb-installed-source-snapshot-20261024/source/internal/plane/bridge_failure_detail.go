package plane

import "strings"

const bridgeFailureDetailLimit = 1024

// bridgeFailureDetail exposes deterministic failed-gate metadata only. Passing
// checks carry no detail through the bridge. Whitespace is collapsed and output
// is bounded so this cannot become an arbitrary log/source exfiltration surface.
func bridgeFailureDetail(pass bool, detail string) string {
	if pass {
		return ""
	}
	detail = strings.Join(strings.Fields(detail), " ")
	if len(detail) > bridgeFailureDetailLimit {
		detail = detail[:bridgeFailureDetailLimit]
	}
	return detail
}
