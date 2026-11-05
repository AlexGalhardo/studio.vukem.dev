package tests

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/AlexGalhardo/vukem/vukemtest"

	"github.com/AlexGalhardo/vukem-studio/app/jobs"
	"github.com/AlexGalhardo/vukem-studio/app/studio"
	"github.com/AlexGalhardo/vukem-studio/bootstrap"
)

func TestJobsRequireASession(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New)

	app.Client(t).Get("/jobs").AssertRedirect("/login")
	app.Client(t).Get("/jobs/create").AssertRedirect("/login")
	app.Client(t).Get("/").AssertRedirect("/login")
}

func TestBriefValidation(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New)
	c := app.Client(t).Inertia("").WithHeader("Referer", "/jobs/create")
	register(t, app, c, "brief@example.com")

	c.PostJSON("/jobs", map[string]any{"audience": "neighbors"}).AssertRedirect("/jobs/create")
	c.Get("/jobs/create").AssertInertia("Jobs/Create").HasProp("errors.goal")

	c.PostJSON("/jobs", validBrief(map[string]any{"style_skill": "no-such-style"})).AssertRedirect("/jobs/create")
	c.Get("/jobs/create").AssertInertia("Jobs/Create").HasProp("errors.style_skill")

	c.PostJSON("/jobs", validBrief(map[string]any{"voice": "upload"})).AssertRedirect("/jobs/create")
	c.Get("/jobs/create").AssertInertia("Jobs/Create").HasProp("errors.voice_file")
}

func TestJobsDoNotLeakAcrossUsers(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New)
	jobs.UsePlanner(app.App, rejectPlanner{})

	ana := app.Client(t).Inertia("")
	register(t, app, ana, "ana-jobs@example.com")
	ana.PostJSON("/jobs", validBrief(map[string]any{"subject": "Ana harbor"})).AssertRedirect("/jobs/1")

	bia := app.Client(t).Inertia("")
	register(t, app, bia, "bia-jobs@example.com")
	bia.PostJSON("/jobs", validBrief(map[string]any{"subject": "Bia market"})).AssertRedirect("/jobs/2")

	bia.Get("/jobs").AssertInertia("Jobs/Index").HasProp("jobs", 1).PropEquals("jobs.0.subject", "Bia market")
	bia.Get("/jobs/1").AssertNotFound()
	bia.Get("/jobs/1/download").AssertNotFound()
	ana.Get("/jobs").AssertInertia("Jobs/Index").HasProp("jobs", 1).PropEquals("jobs.0.subject", "Ana harbor")
}

func TestInvalidModelAndMissingFactAndDuration(t *testing.T) {
	t.Parallel()

	t.Run("model", func(t *testing.T) {
		t.Parallel()

		app := vukemtest.New(t, bootstrap.New)
		jobs.UsePlanner(app.App, rejectPlanner{})
		c := app.Client(t).Inertia("")
		register(t, app, c, "model@example.com")

		c.PostJSON("/jobs", validBrief(nil)).AssertRedirect("/jobs/1")
		page := c.Get("/jobs/1").AssertInertia("Jobs/Show")
		page.PropEquals("job.status", "failed")

		raw, _ := page.Prop("job.raw_model")
		if raw != "{" {
			t.Fatalf("raw model = %v", raw)
		}

		prompt, _ := page.Prop("job.prompt")
		if !strings.Contains(fmt.Sprint(prompt), "the harbor opens at 6") {
			t.Fatalf("prompt = %v", prompt)
		}

		c.Get("/jobs/1/download").AssertNotFound()
	})

	t.Run("fact", func(t *testing.T) {
		t.Parallel()

		app := vukemtest.New(t, bootstrap.New)
		jobs.UsePlanner(app.App, dropFacts{})
		c := app.Client(t).Inertia("")
		register(t, app, c, "fact@example.com")
		c.PostJSON("/jobs", validBrief(nil)).AssertRedirect("/jobs/1")

		page := c.Get("/jobs/1").AssertOK().AssertInertia("Jobs/Show")
		page.PropEquals("job.status", "failed")

		failure, _ := page.Prop("job.failure")
		if !strings.Contains(fmt.Sprint(failure), "the harbor opens at 6") {
			t.Fatalf("failure = %v", failure)
		}

		c.Get("/jobs/1/download").AssertNotFound()
	})

	t.Run("duration", func(t *testing.T) {
		t.Parallel()

		app := vukemtest.New(t, bootstrap.New)
		jobs.UsePlanner(app.App, durationPlanner{seconds: 99})
		c := app.Client(t).Inertia("")
		register(t, app, c, "duration@example.com")
		c.PostJSON("/jobs", validBrief(nil)).AssertRedirect("/jobs/1")
		c.Get("/jobs/1").AssertInertia("Jobs/Show").PropEquals("job.status", "failed")
	})
}

func TestTruncatedAndKilledEncoder(t *testing.T) {
	t.Parallel()

	for _, tc := range []struct {
		name string
		r    studio.Renderer
	}{
		{name: "truncated", r: truncatedRenderer{}},
		{name: "killed", r: killedRenderer{}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			app := vukemtest.New(t, bootstrap.New)
			jobs.UseRenderer(app.App, tc.r)
			c := app.Client(t).Inertia("")
			register(t, app, c, tc.name+"@example.com")
			c.PostJSON("/jobs", validBrief(nil)).AssertRedirect("/jobs/1")
			c.Get("/jobs/1").AssertInertia("Jobs/Show").PropEquals("job.status", "failed")
			c.Get("/jobs/1/download").AssertNotFound()
		})
	}
}

func TestSilentFixture(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	app := vukemtest.New(t, bootstrap.New, vukemtest.Options{Env: map[string]string{"STUDIO_STORAGE": dir}})
	c := app.Client(t).Inertia("")
	register(t, app, c, "silent@example.com")

	c.PostJSON("/jobs", validBrief(nil)).AssertRedirect("/jobs/1")

	page := c.Get("/jobs/1").AssertOK().AssertInertia("Jobs/Show")
	page.PropEquals("job.status", "ready")
	page.PropEquals("job.model_id", "local-planner")
	page.PropEquals("job.style_skill", "traco-simples")
	page.PropEquals("job.duration", 6)

	prompt, _ := page.Prop("job.prompt")
	text := fmt.Sprint(prompt)

	for _, want := range []string{"the harbor opens at 6", "Frame size: 1080x1920", "1080x1920", "traco-simples"} {
		if !strings.Contains(text, want) {
			t.Fatalf("prompt missing %q", want)
		}
	}

	page.PropEquals("download", true)

	body := download(t, app, "silent@example.com", "/jobs/1/download")
	path := filepath.Join(t.TempDir(), "out.mp4")

	if err := os.WriteFile(path, body, 0o644); err != nil {
		t.Fatal(err)
	}

	probe := probeFile(t, path)
	if probe.width != 1080 || probe.height != 1920 || probe.pix != "yuv420p" || probe.audio {
		t.Fatalf("probe = %+v", probe)
	}

	if math.Abs(probe.duration-6) > 0.5 {
		t.Fatalf("duration = %v", probe.duration)
	}

	fast, err := studio.FastStart(path)
	if err != nil || !fast {
		t.Fatalf("faststart = %v, %v", fast, err)
	}

	args, err := os.ReadFile(filepath.Join(dir, "1", "encode-args.txt"))
	if err != nil || !strings.Contains(string(args), "subtitles=captions.srt") {
		t.Fatalf("encode args = %s (%v)", args, err)
	}

	srt := download(t, app, "silent@example.com", "/jobs/1/captions.srt")
	if !bytes.Contains(srt, []byte("the harbor opens at 6")) {
		t.Fatalf("srt = %s", srt)
	}

	c.Get("/jobs").AssertInertia("Jobs/Index").HasProp("jobs", 1).
		PropEquals("jobs.0.status", "ready").
		PropEquals("jobs.0.duration", 6).
		PropEquals("jobs.0.style_skill", "traco-simples")

	c.WithHeader("Referer", "/jobs/1").PostJSON("/jobs/1/pack", map[string]any{
		"platform": "youtube", "title": strings.Repeat("a", 101), "description": "Come early",
	}).AssertRedirect("/jobs/1")
	c.Get("/jobs/1").AssertInertia("Jobs/Show").HasProp("errors.title")

	c.PostJSON("/jobs/1/pack", map[string]any{
		"platform": "reels", "title": "Harbor market", "description": "Come early.", "hashtags": "#harbor #market",
	}).AssertRedirect("/jobs/1")
	packed := c.Get("/jobs/1").AssertInertia("Jobs/Show")
	packed.PropEquals("job.pack_title", "Harbor market").PropEquals("job.pack_platform", "reels")

	if _, ok := packed.Prop("job.posted_url"); ok {
		t.Fatal("the pack posted to a network")
	}
}

func TestRerunKeepsThePreviousFile(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	app := vukemtest.New(t, bootstrap.New, vukemtest.Options{Env: map[string]string{"STUDIO_STORAGE": dir}})
	c := app.Client(t).Inertia("")
	register(t, app, c, "rerun@example.com")
	c.PostJSON("/jobs", validBrief(nil)).AssertRedirect("/jobs/1")

	before := download(t, app, "rerun@example.com", "/jobs/1/download")
	jobs.UseRenderer(app.App, killedRenderer{})
	c.PostJSON("/jobs/1/retry", map[string]any{}).AssertRedirect("/jobs/1")

	page := c.Get("/jobs/1").AssertInertia("Jobs/Show")
	page.PropEquals("job.status", "ready")

	failure, _ := page.Prop("job.failure")
	if !strings.Contains(fmt.Sprint(failure), "previous file") {
		t.Fatalf("failure = %v", failure)
	}

	after := download(t, app, "rerun@example.com", "/jobs/1/download")
	if !bytes.Equal(before, after) {
		t.Fatal("the failed re-run replaced the ready file")
	}

	matches, err := filepath.Glob(filepath.Join(dir, "1", "*.mp4"))
	if err != nil {
		t.Fatal(err)
	}

	if len(matches) != 1 || filepath.Base(matches[0]) != "output.mp4" {
		t.Fatalf("mp4 files = %v", matches)
	}
}

func TestRetryDoesNotLeaveASecondFile(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	app := vukemtest.New(t, bootstrap.New, vukemtest.Options{Env: map[string]string{"STUDIO_STORAGE": dir}})
	c := app.Client(t).Inertia("")
	register(t, app, c, "twice@example.com")
	c.PostJSON("/jobs", validBrief(nil)).AssertRedirect("/jobs/1")
	c.PostJSON("/jobs/1/retry", map[string]any{}).AssertRedirect("/jobs/1")
	c.Get("/jobs/1").AssertInertia("Jobs/Show").PropEquals("job.status", "ready")

	matches, err := filepath.Glob(filepath.Join(dir, "1", "*.mp4"))
	if err != nil {
		t.Fatal(err)
	}

	if len(matches) != 1 {
		t.Fatalf("mp4 files = %v", matches)
	}
}

func TestSpokenFixture(t *testing.T) {
	t.Parallel()

	t.Run("no bed", func(t *testing.T) {
		t.Parallel()
		assertSpoken(t, "", false)
	})

	t.Run("licensed bed", func(t *testing.T) {
		t.Parallel()
		assertSpoken(t, "Pixabay 123", true)
	})
}

func assertSpoken(t *testing.T, license string, wantBed bool) {
	t.Helper()

	dir := t.TempDir()
	app := vukemtest.New(t, bootstrap.New, vukemtest.Options{Env: map[string]string{"STUDIO_STORAGE": dir}})
	c := app.Client(t).Inertia("")
	email := "spoken-bed@example.com"

	if license == "" {
		email = "spoken-none@example.com"
	}

	register(t, app, c, email)

	brief := validBrief(map[string]any{"duration": 5, "voice": "tts", "music_license": license})
	c.PostJSON("/jobs", brief).AssertRedirect("/jobs/1")
	c.Get("/jobs/1").AssertInertia("Jobs/Show").PropEquals("job.status", "ready")

	body := download(t, app, email, "/jobs/1/download")
	path := filepath.Join(t.TempDir(), "spoken.mp4")

	if err := os.WriteFile(path, body, 0o644); err != nil {
		t.Fatal(err)
	}

	probe := probeFile(t, path)
	if !probe.audio || probe.codec != "aac" {
		t.Fatalf("audio probe = %+v", probe)
	}

	integrated, peak, err := studio.MeasureLoudness(t.Context(), path)
	if err != nil {
		t.Fatal(err)
	}

	if math.Abs(integrated-(-14)) > 2 || peak > -1.5 {
		t.Fatalf("loudness = %.2f LUFS %.2f dBTP", integrated, peak)
	}

	srt := string(download(t, app, email, "/jobs/1/captions.srt"))
	if !strings.Contains(srt, "harbor") {
		t.Fatalf("srt = %s", srt)
	}

	samples, err := studio.DecodeMono(t.Context(), path)
	if err != nil {
		t.Fatal(err)
	}

	power := studio.Goertzel(samples, 48000, 80)
	if wantBed && power < 1 {
		t.Fatalf("licensed bed power = %v", power)
	}

	if !wantBed && power > 1e6 {
		t.Fatalf("unlicensed file has an 80 Hz bed (%v)", power)
	}

	side, err := os.ReadFile(filepath.Join(dir, "1", "sidecar.json"))
	if err != nil {
		t.Fatal(err)
	}

	if wantBed && !bytes.Contains(side, []byte(`"music_bed": true`)) {
		t.Fatalf("sidecar = %s", side)
	}

	if !wantBed && !bytes.Contains(side, []byte(`"music_bed": false`)) {
		t.Fatalf("sidecar = %s", side)
	}
}

func TestUploadThatDoesNotFit(t *testing.T) {
	t.Parallel()

	app := vukemtest.New(t, bootstrap.New)
	c := app.Client(t).Inertia("")
	register(t, app, c, "upload@example.com")

	wav := filepath.Join(t.TempDir(), "short.wav")
	if err := studio.WriteWAV(wav, studio.Synthesize("hello", 1, 48000), 48000); err != nil {
		t.Fatal(err)
	}

	body, contentType := briefMultipart(t, wav)
	res := c.WithHeader("Referer", "/jobs/create").Do(http.MethodPost, "/jobs", body, contentType)
	res.AssertRedirect("/jobs/1")

	page := c.Get("/jobs/1").AssertInertia("Jobs/Show")
	page.PropEquals("job.status", "failed")

	failure, _ := page.Prop("job.failure")
	if !strings.Contains(fmt.Sprint(failure), "does not fit") {
		t.Fatalf("failure = %v", failure)
	}

	c.Get("/jobs/1/download").AssertNotFound()
}

func validBrief(over map[string]any) map[string]any {
	brief := map[string]any{
		"goal": "Visit the harbor", "audience": "neighbors", "subject": "Saturday market",
		"duration": 6, "ratio": "9:16", "style_skill": "traco-simples", "language": "en",
		"facts": "the harbor opens at 6", "links": "https://example.com/harbor",
		"call_to_action": "Come early", "voice": "none",
	}

	for k, v := range over {
		brief[k] = v
	}

	return brief
}

func download(t *testing.T, app *vukemtest.App, email, path string) []byte {
	t.Helper()

	plain := app.Client(t)
	plain.PostJSON("/login", map[string]any{"email": email, "password": testPassword}).AssertRedirect("/dashboard")

	res := plain.Get(path)
	res.AssertOK()

	if !strings.Contains(res.Recorder().Header().Get("Content-Disposition"), "attachment") {
		t.Fatalf("download disposition = %q", res.Recorder().Header().Get("Content-Disposition"))
	}

	return []byte(res.Body())
}

type probeResult struct {
	width, height int
	pix, codec    string
	duration      float64
	audio         bool
}

func probeFile(t *testing.T, path string) probeResult {
	t.Helper()

	probe, err := studio.Inspect(t.Context(), path)
	if err != nil {
		t.Fatal(err)
	}

	var got probeResult

	for _, stream := range probe.Streams {
		switch stream.CodecType {
		case "video":
			got.width = stream.Width
			got.height = stream.Height
			got.pix = stream.PixFmt
		case "audio":
			got.audio = true
			got.codec = stream.CodecName
		}
	}

	got.duration, _ = parseFloat(probe.Format.Duration)

	return got
}

func parseFloat(s string) (float64, error) {
	var f float64
	_, err := fmt.Sscan(s, &f)

	return f, err
}

func briefMultipart(t *testing.T, wavPath string) (*bytes.Buffer, string) {
	t.Helper()

	var buf bytes.Buffer
	w := multipart.NewWriter(&buf)
	fields := validBrief(map[string]any{"voice": "upload", "duration": "6"})

	for key, value := range fields {
		if err := w.WriteField(key, fmt.Sprint(value)); err != nil {
			t.Fatal(err)
		}
	}

	part, err := w.CreateFormFile("voice_file", "voice.wav")
	if err != nil {
		t.Fatal(err)
	}

	contents, err := os.ReadFile(wavPath)
	if err != nil {
		t.Fatal(err)
	}

	if _, err := part.Write(contents); err != nil {
		t.Fatal(err)
	}

	if err := w.Close(); err != nil {
		t.Fatal(err)
	}

	return &buf, w.FormDataContentType()
}

type rejectPlanner struct{}

func (rejectPlanner) ID() string { return "reject" }

func (rejectPlanner) Plan(context.Context, string, studio.Brief) (studio.Plan, string, error) {
	return studio.Plan{}, "{", errors.New("not json")
}

type dropFacts struct{}

func (dropFacts) ID() string { return "drop-facts" }

func (dropFacts) Plan(_ context.Context, prompt string, brief studio.Brief) (studio.Plan, string, error) {
	plan, _, err := (studio.LocalPlanner{}).Plan(context.Background(), prompt, brief)
	if err != nil {
		return plan, "", err
	}

	plan.Script = "nothing required was kept"
	plan.Shots[0].Text = plan.Script

	return mustRaw(plan)
}

type durationPlanner struct{ seconds float64 }

func (d durationPlanner) ID() string { return "duration" }

func (d durationPlanner) Plan(_ context.Context, prompt string, brief studio.Brief) (studio.Plan, string, error) {
	plan, _, err := (studio.LocalPlanner{}).Plan(context.Background(), prompt, brief)
	if err != nil {
		return plan, "", err
	}

	plan.Duration = d.seconds

	return mustRaw(plan)
}

func mustRaw(plan studio.Plan) (studio.Plan, string, error) {
	b, err := json.Marshal(plan)

	return plan, string(b), err
}

type killedRenderer struct{}

func (killedRenderer) Name() string                   { return "killed" }
func (killedRenderer) Version(context.Context) string { return "killed-test" }
func (killedRenderer) Render(_ context.Context, req studio.RenderRequest) error {
	_ = os.WriteFile(req.PendingPath(), []byte("partial"), 0o644)

	return errors.New("encoder killed")
}

type truncatedRenderer struct{}

func (truncatedRenderer) Name() string                   { return "truncated" }
func (truncatedRenderer) Version(context.Context) string { return "truncated-test" }
func (truncatedRenderer) Render(_ context.Context, req studio.RenderRequest) error {
	if err := os.WriteFile(filepath.Join(req.Dir, "encode-args.txt"), []byte("truncated captions.srt\n"), 0o644); err != nil {
		return err
	}

	return os.WriteFile(req.PendingPath(), []byte("not a video"), 0o644)
}
