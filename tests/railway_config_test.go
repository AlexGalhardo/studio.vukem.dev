package tests

import (
	"os"
	"strings"
	"testing"
)

// The start command runs as root; a recursive chown would follow a symlink
// that the app user planted in the volume.
func TestStartCommandDoesNotChownRecursively(t *testing.T) {
	body, err := os.ReadFile("../railway.app.toml")
	if err != nil {
		t.Fatal(err)
	}

	var cmd string

	for line := range strings.SplitSeq(string(body), "\n") {
		if strings.HasPrefix(line, "startCommand") {
			cmd = line
		}
	}

	if cmd == "" || strings.Contains(cmd, "chown -R") || !strings.Contains(cmd, "chown -h") {
		t.Fatalf("start command must chown the mount point and use chown -h below it: %q", cmd)
	}
}
