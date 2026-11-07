package studio

import (
	"context"
	"os/exec"
	"time"
)

// CmdTimeout bounds every ffmpeg, ffprobe and renderer process. A hung or
// expensive filter graph is killed at the deadline instead of holding a
// worker. Tests lower it.
var CmdTimeout = 5 * time.Minute

// commandCtx is exec.CommandContext with a per-process deadline. Callers
// must call the returned cancel. WaitDelay closes the pipes a stuck child
// would keep open after the kill.
func commandCtx(ctx context.Context, name string, args ...string) (*exec.Cmd, context.CancelFunc) {
	ctx, cancel := context.WithTimeout(ctx, CmdTimeout)
	cmd := exec.CommandContext(ctx, name, args...)
	cmd.WaitDelay = 2 * time.Second

	return cmd, cancel
}
