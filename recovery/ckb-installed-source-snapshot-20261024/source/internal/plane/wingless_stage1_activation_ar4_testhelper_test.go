package plane

import (
	"context"
	"io"
)

type ProcessRunnerFunc func(context.Context, ProcessSpec, io.Writer, io.Writer) error

func (f ProcessRunnerFunc) Run(ctx context.Context, spec ProcessSpec, stdout, stderr io.Writer) error {
	return f(ctx, spec, stdout, stderr)
}
