package studio

import (
	"os"
	"testing"
	"time"
)

// TestMain lets the test binary stand in for a hung ffmpeg: with the helper
// variable set it sleeps instead of running tests.
func TestMain(m *testing.M) {
	if os.Getenv("STUDIO_HELPER_HANG") == "1" {
		time.Sleep(time.Minute)
		os.Exit(0)
	}

	os.Exit(m.Run())
}
