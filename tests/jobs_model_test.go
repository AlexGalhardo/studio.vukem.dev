package tests

import (
	"os"
	"strings"
	"testing"

	"github.com/AlexGalhardo/vukem/vukemtest"

	"github.com/AlexGalhardo/vukem-studio/app/jobs"
	"github.com/AlexGalhardo/vukem-studio/bootstrap"
)

func TestHostedModelWithoutKeyFailsReadably(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New, vukemtest.Options{Env: map[string]string{
		"STUDIO_MODEL": "claude-sonnet-5-5", "ANTHROPIC_API_KEY": "",
	}})
	c := app.Client(t).Inertia("")
	register(t, app, c, "nokey@example.com")

	c.PostJSON("/jobs", validBrief(nil)).AssertRedirect("/jobs/1")

	page := c.Get("/jobs/1").AssertInertia("Jobs/Show").PropEquals("job.status", "failed").PropEquals("job.model_id", "claude-sonnet-5-5")

	failure, _ := page.Prop("job.failure")
	if !strings.Contains(failure.(string), "ANTHROPIC_API_KEY") {
		t.Fatalf("failure = %v, want the variable name", failure)
	}
}

// 300 seconds is accepted and queued (a stub encoder keeps the test fast);
// 301 and 4 are rejected by the server.
func TestDurationLimitIsThreeHundredSeconds(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New)
	jobs.UseRenderer(app.App, killedRenderer{})

	c := app.Client(t)
	register(t, app, c, "long@example.com")

	c.Inertia("").PostJSON("/jobs", validBrief(map[string]any{"duration": 300})).AssertRedirect("/jobs/1")
	vukemtest.AssertDatabaseHas(t, app, "jobs", map[string]any{"duration": 300})

	api := c.AcceptJSON()
	api.PostJSON("/jobs", validBrief(map[string]any{"duration": 301})).AssertJSONValidationErrors("duration")
	api.PostJSON("/jobs", validBrief(map[string]any{"duration": 4})).AssertJSONValidationErrors("duration")
	vukemtest.AssertDatabaseCount(t, app, "jobs", 1)
}

// TestFiveMinuteVideoRenders renders a real 300-second file (about a minute).
func TestFiveMinuteVideoRenders(t *testing.T) {
	if os.Getenv("STUDIO_TEST_LONG") != "1" {
		t.Skip("set STUDIO_TEST_LONG=1 to render a real 300-second video")
	}

	app := vukemtest.New(t, bootstrap.New)
	c := app.Client(t).Inertia("")
	register(t, app, c, "five@example.com")

	c.PostJSON("/jobs", validBrief(map[string]any{"duration": 300})).AssertRedirect("/jobs/1")
	c.Get("/jobs/1").AssertInertia("Jobs/Show").PropEquals("job.status", "ready")
}
