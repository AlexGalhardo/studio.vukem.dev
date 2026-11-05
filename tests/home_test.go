package tests

import (
	"testing"

	"github.com/AlexGalhardo/vukem/vukemtest"

	"github.com/AlexGalhardo/vukem-studio/bootstrap"
)

func TestHome(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New)

	app.Client(t).Get("/").AssertRedirect("/login")
	app.Client(t).Inertia("").Get("/").AssertRedirect("/login")
	app.Client(t).Get("/up").AssertOK()
}

func TestErrorPage(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New)

	// Errors on Inertia visits render resources/js/pages/Error; full page
	// loads keep the HTML status page.
	app.Client(t).Inertia("").Get("/no-such-page").AssertStatus(404).
		AssertInertia("Error").
		PropEquals("status", 404).
		PropEquals("message", "Not Found")
	app.Client(t).Get("/no-such-page").AssertStatus(404).AssertHeader("X-Inertia", "")
}
