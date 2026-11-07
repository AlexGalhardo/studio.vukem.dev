package tests

import (
	"strings"
	"testing"

	"github.com/AlexGalhardo/vukem/vukemtest"

	"github.com/AlexGalhardo/vukem-studio/bootstrap"
)

func studioEnv(t *testing.T, extra map[string]string) vukemtest.Options {
	t.Helper()

	env := map[string]string{"STUDIO_PROVIDER": "fake", "STUDIO_OUTPUT_DIR": t.TempDir()}
	for k, v := range extra {
		env[k] = v
	}

	return vukemtest.Options{Env: env}
}

func brief(over map[string]any) map[string]any {
	b := map[string]any{
		"goal": "Get signups", "audience": "indie developers", "subject": "Studio kit", "duration": 10,
		"ratio": "9:16", "skill": "video-text-cards", "language": "English", "model": "claude-sonnet-5-5",
		"facts": "Costs 9 dollars\nShips on Friday", "links": "https://example.com/kit", "cta": "Buy now",
	}
	for k, v := range over {
		b[k] = v
	}

	return b
}

func TestVideosRequireLogin(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New, studioEnv(t, nil))
	c := app.Client(t)

	for _, path := range []string{"/videos", "/videos/create", "/videos/1", "/videos/1/status", "/videos/1/download"} {
		c.Get(path).AssertRedirect("/login")
	}

	c.PostJSON("/videos", brief(nil)).AssertStatus(401)
	c.Inertia("").PostJSON("/videos", brief(nil)).AssertRedirect("/login")
	c.Inertia("").PostJSON("/videos/1/retry", nil).AssertRedirect("/login")
}

func TestVideoHappyPath(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New, studioEnv(t, nil))
	c := app.Client(t)
	register(t, app, c, "maker@example.com")

	c.Get("/videos/create").AssertOK().AssertInertia("Videos/Create")

	c.Inertia("").PostJSON("/videos", brief(nil)).AssertRedirect("/videos/1")

	vukemtest.AssertDatabaseHas(t, app, "videos", map[string]any{
		"status": "ready", "skill_id": "video-text-cards", "model_id": "claude-sonnet-5-5",
	})

	show := c.Inertia("").Get("/videos/1").AssertOK().AssertInertia("Videos/Show").PropEquals("ready", true)
	show.PropEquals("video.status", "ready")

	body := c.Inertia("").Get("/videos/1").Body()
	for _, fact := range []string{"Costs 9 dollars", "Ships on Friday", "1080x1920", "Buy now"} {
		if !strings.Contains(body, fact) {
			t.Errorf("stored prompt lacks %q", fact)
		}
	}

	c.AcceptJSON().Get("/videos/1/status").AssertOK().AssertJSONPath("status", "ready").AssertJSONPath("progress", 100)
	c.Get("/videos/1/download").AssertOK()
	c.Inertia("").Get("/videos").AssertOK().AssertInertia("Videos/Index").HasProp("videos", 1)
}

func TestVideoBriefValidation(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New, studioEnv(t, nil))
	c := app.Client(t)
	register(t, app, c, "val@example.com")
	api := c.AcceptJSON()

	api.PostJSON("/videos", brief(map[string]any{"goal": ""})).AssertJSONValidationErrors("goal")
	api.PostJSON("/videos", brief(map[string]any{"skill": "no-such-skill"})).AssertJSONValidationErrors("skill")
	api.PostJSON("/videos", brief(map[string]any{"skill": "../../etc/passwd"})).AssertJSONValidationErrors("skill")
	api.PostJSON("/videos", brief(map[string]any{"model": "gpt-unknown"})).AssertJSONValidationErrors("model")
	api.PostJSON("/videos", brief(map[string]any{"duration": 301})).AssertJSONValidationErrors("duration")
	api.PostJSON("/videos", brief(map[string]any{"duration": 1})).AssertJSONValidationErrors("duration")
	api.PostJSON("/videos", brief(map[string]any{"ratio": "2:1"})).AssertJSONValidationErrors("ratio")
	api.PostJSON("/videos", brief(map[string]any{"goal": strings.Repeat("x", 301)})).AssertJSONValidationErrors("goal")
	api.PostJSON("/videos", brief(map[string]any{"facts": strings.Repeat("f", 400)})).AssertJSONValidationErrors("facts")
	api.PostJSON("/videos", brief(map[string]any{"links": "javascript:alert(1)"})).AssertJSONValidationErrors("links")

	vukemtest.AssertDatabaseCount(t, app, "videos", 0)
}

func TestVideoModelFailureAndRetry(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New, studioEnv(t, map[string]string{"STUDIO_FAKE_PLANNER": "error"}))
	c := app.Client(t)
	register(t, app, c, "fail@example.com")

	c.Inertia("").PostJSON("/videos", brief(nil)).AssertRedirect("/videos/1")
	vukemtest.AssertDatabaseHas(t, app, "videos", map[string]any{"status": "failed"})

	api := c.AcceptJSON()
	api.Get("/videos/1").AssertOK().AssertJSONPath("status", "failed")
	c.Get("/videos/1/download").AssertStatus(409)

	// Retry stays allowed until the attempt budget is spent.
	for range 2 {
		api.PostJSON("/videos/1/retry", nil).AssertOK()
	}

	api.PostJSON("/videos/1/retry", nil).AssertStatus(409)
}

func TestVideoInvalidPlanKeepsRawResponse(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New, studioEnv(t, map[string]string{"STUDIO_FAKE_PLANNER": "invalid"}))
	c := app.Client(t)
	register(t, app, c, "plan@example.com")

	c.Inertia("").PostJSON("/videos", brief(nil)).AssertRedirect("/videos/1")
	vukemtest.AssertDatabaseHas(t, app, "videos", map[string]any{"status": "failed", "raw_response": "I cannot help with that."})
}

func TestVideoRenderFailure(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New, studioEnv(t, map[string]string{"STUDIO_FAKE_RENDER_FAIL": "true"}))
	c := app.Client(t)
	register(t, app, c, "render@example.com")

	c.Inertia("").PostJSON("/videos", brief(nil)).AssertRedirect("/videos/1")
	vukemtest.AssertDatabaseHas(t, app, "videos", map[string]any{"status": "failed"})
	c.Get("/videos/1/download").AssertStatus(409)
}

func TestVideoMissingKeyDegradesClearly(t *testing.T) {
	t.Parallel()

	// No fake provider and no key: the job must fail with a readable reason.
	app := vukemtest.New(t, bootstrap.New, vukemtest.Options{Env: map[string]string{
		"STUDIO_OUTPUT_DIR": t.TempDir(), "ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": "",
	}})
	c := app.Client(t)
	register(t, app, c, "nokey@example.com")

	c.Inertia("").PostJSON("/videos", brief(nil)).AssertRedirect("/videos/1")
	c.AcceptJSON().Get("/videos/1").AssertOK().AssertJSONPath("status", "failed").AssertSee("ANTHROPIC_API_KEY")
}

func TestVideoCostAndDailyLimits(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New, studioEnv(t, map[string]string{"STUDIO_MAX_JOBS_PER_DAY": "1"}))
	c := app.Client(t)
	register(t, app, c, "limit@example.com")

	c.Inertia("").PostJSON("/videos", brief(nil)).AssertRedirect("/videos/1")
	c.AcceptJSON().PostJSON("/videos", brief(nil)).AssertJSONValidationErrors("form")
	vukemtest.AssertDatabaseCount(t, app, "videos", 1)

	capped := vukemtest.New(t, bootstrap.New, studioEnv(t, map[string]string{"STUDIO_MAX_JOB_COST_CENTS": "0", "STUDIO_MAX_OUTPUT_TOKENS": "4000"}))
	c2 := capped.Client(t)
	register(t, capped, c2, "nocap@example.com")
	// A cost cap of zero means unlimited; a tiny cap fails the job before any model call.
	c2.Inertia("").PostJSON("/videos", brief(nil)).AssertRedirect("/videos/1")
	vukemtest.AssertDatabaseHas(t, capped, "videos", map[string]any{"status": "ready"})

	tiny := vukemtest.New(t, bootstrap.New, studioEnv(t, map[string]string{"STUDIO_MAX_JOB_COST_CENTS": "1"}))
	c3 := tiny.Client(t)
	register(t, tiny, c3, "tiny@example.com")
	c3.Inertia("").PostJSON("/videos", brief(map[string]any{"model": "claude-opus-5-5"})).AssertRedirect("/videos/1")
	vukemtest.AssertDatabaseHas(t, tiny, "videos", map[string]any{"status": "failed"})
}

func TestVideosAreIsolatedBetweenUsers(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New, studioEnv(t, nil))
	owner := app.Client(t)
	register(t, app, owner, "owner@example.com")
	owner.Inertia("").PostJSON("/videos", brief(nil)).AssertRedirect("/videos/1")

	other := app.Client(t)
	register(t, app, other, "other@example.com")

	other.Get("/videos/1").AssertNotFound()
	other.Get("/videos/1/status").AssertNotFound()
	other.Get("/videos/1/download").AssertNotFound()
	other.PostJSON("/videos/1/retry", nil).AssertNotFound()
	other.Inertia("").Get("/videos").AssertOK().AssertInertia("Videos/Index").HasProp("videos", 0)
	owner.Get("/videos/1/download").AssertOK()
}
