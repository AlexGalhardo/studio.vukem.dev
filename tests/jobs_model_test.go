package tests

import (
	"strings"
	"testing"

	"github.com/AlexGalhardo/vukem/vukemtest"

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
