package studio

import (
	"context"
	"os"
	"strings"
	"testing"
	"time"
)

// TestMain lets the test binary stand in for a hung encoder: with the helper
// variable set it sleeps instead of running tests.
func TestMain(m *testing.M) {
	if os.Getenv("STUDIO_HELPER_HANG") == "1" {
		time.Sleep(time.Minute)
		os.Exit(0)
	}

	os.Exit(m.Run())
}

func TestHungEncoderIsKilledByTheDeadline(t *testing.T) {
	t.Setenv("STUDIO_HELPER_HANG", "1")

	old := CmdTimeout
	CmdTimeout = 300 * time.Millisecond

	t.Cleanup(func() { CmdTimeout = old })

	req := RenderRequest{Dir: t.TempDir()}
	start := time.Now()
	err := runEncode(context.Background(), os.Args[0], []string{"-x"}, req)

	if err == nil || !strings.Contains(err.Error(), "encoder failed") {
		t.Fatalf("err = %v, want an encoder failure from the kill", err)
	}

	if time.Since(start) > 10*time.Second {
		t.Fatalf("took %s: the deadline did not stop the process", time.Since(start))
	}
}
