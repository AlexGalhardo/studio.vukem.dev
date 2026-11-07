package tests

import (
	"net"
	"net/http"
	"os"
	"os/signal"
	"testing"
	"time"

	"github.com/AlexGalhardo/vukem/social"
	"github.com/AlexGalhardo/vukem/vukemtest"

	"github.com/AlexGalhardo/vukem-studio/app/jobs"
	"github.com/AlexGalhardo/vukem-studio/bootstrap"
)

// TestE2EServer is the server Playwright drives (bun run e2e). It stays
// skipped unless STUDIO_E2E_ADDR is set. Google sign-in goes through vukem's
// fake provider, so no real account is involved. STUDIO_E2E_MODE picks the
// failure to inject: ok, model, or render. The server stops after a TTL so a
// killed runner cannot leave it behind.
func TestE2EServer(t *testing.T) {
	addr := os.Getenv("STUDIO_E2E_ADDR")
	if addr == "" {
		t.Skip("set STUDIO_E2E_ADDR to start the browser test server")
	}

	user := social.User{ID: "e2e-1", Email: "e2e@example.com", EmailVerified: true, Name: "E2E Maker"}
	app := vukemtest.New(t, bootstrap.New, vukemtest.Options{Env: vukemtest.FakeSocial(user)})

	switch os.Getenv("STUDIO_E2E_MODE") {
	case "model":
		jobs.UsePlanner(app.App, rejectPlanner{})
	case "render":
		jobs.UseRenderer(app.App, killedRenderer{})
	}

	ln, err := net.Listen("tcp", addr)
	if err != nil {
		t.Fatal(err)
	}

	srv := &http.Server{Handler: app.Handler(), ReadHeaderTimeout: 10 * time.Second}

	go func() { _ = srv.Serve(ln) }()

	defer func() { _ = srv.Close() }()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt)

	select {
	case <-stop:
	case <-time.After(15 * time.Minute):
	}
}
