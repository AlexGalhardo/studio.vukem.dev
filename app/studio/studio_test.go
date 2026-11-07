package studio

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestParsePlan(t *testing.T) {
	good := `Here you go:
` + "```json" + `
{"title":"T","scenes":[{"title":"a","text":"b","seconds":5,"color":"#112233"},{"title":"c","text":"d","seconds":5,"color":"nope"}]}
` + "```"

	p, err := ParsePlan(good, 10)
	if err != nil || len(p.Scenes) != 2 || p.Scenes[1].Color == "nope" {
		t.Fatalf("good plan: %+v %v", p, err)
	}

	for name, raw := range map[string]string{
		"no json":      "sorry",
		"wrong length": `{"title":"T","scenes":[{"title":"a","text":"b","seconds":5}]}`,
		"no scenes":    `{"title":"T","scenes":[]}`,
		"unknown key":  `{"title":"T","extra":1,"scenes":[{"title":"a","text":"b","seconds":10}]}`,
		"neg seconds":  `{"title":"T","scenes":[{"title":"a","text":"b","seconds":-1}]}`,
	} {
		if _, err := ParsePlan(raw, 10); err == nil {
			t.Errorf("%s: want error", name)
		}
	}
}

func TestCompileCarriesFactsAndFrame(t *testing.T) {
	b := Brief{Goal: "sell", Audience: "devs", Subject: "kit", Duration: 30, Ratio: "9:16", Language: "en", Facts: "Costs $9\nShips Friday", CTA: "Buy now"}

	p, err := Compile(b, Skill{ID: "video-text-cards", Body: "BODY"}, 1080)
	if err != nil {
		t.Fatal(err)
	}

	for _, want := range []string{"Costs $9", "Ships Friday", "1080x1920", "30 seconds", "BODY", "Buy now"} {
		if !strings.Contains(p, want) {
			t.Errorf("prompt lacks %q", want)
		}
	}
}

func TestAdaptersParseProviderReplies(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/v1/messages":
			if r.Header.Get("x-api-key") != "k" {
				w.WriteHeader(401)
				return
			}

			_ = json.NewEncoder(w).Encode(map[string]any{
				"content": []map[string]string{{"type": "text", "text": "{}"}},
				"usage":   map[string]int{"input_tokens": 7, "output_tokens": 3},
			})
		case "/v1/chat/completions":
			_ = json.NewEncoder(w).Encode(map[string]any{
				"choices": []map[string]any{{"message": map[string]string{"content": "{}"}}},
				"usage":   map[string]int{"prompt_tokens": 5, "completion_tokens": 2},
			})
		default:
			w.WriteHeader(500)
		}
	}))
	defer srv.Close()

	ctx := context.Background()

	_, u, err := Claude{Key: "k", BaseURL: srv.URL, Client: srv.Client()}.Plan(ctx, "claude-sonnet-5-5", "p", 100)
	if err != nil || u.InputTokens != 7 || u.OutputTokens != 3 {
		t.Fatalf("claude: %+v %v", u, err)
	}

	if _, _, err := (Claude{Key: "bad", BaseURL: srv.URL, Client: srv.Client()}).Plan(ctx, "m", "p", 1); err == nil || strings.Contains(err.Error(), "bad") {
		t.Fatalf("claude 401 error = %v", err)
	}

	_, u, err = OpenAI{Key: "k", BaseURL: srv.URL, Client: srv.Client()}.Plan(ctx, "gpt", "p", 100)
	if err != nil || u.InputTokens != 5 {
		t.Fatalf("openai: %+v %v", u, err)
	}

	if _, _, err := (Claude{}).Plan(ctx, "m", "p", 1); err == nil {
		t.Fatal("missing key must fail")
	}
}

func TestFFmpegRenderQA(t *testing.T) {
	if os.Getenv("STUDIO_TEST_FFMPEG") != "1" {
		t.Skip("set STUDIO_TEST_FFMPEG=1 (needs ffmpeg and ffprobe)")
	}

	cfg, err := LoadConfig(func(k string) string {
		if k == "STUDIO_RENDER_WIDTH" {
			return "180"
		}

		return os.Getenv(k)
	})
	if err != nil {
		t.Fatal(err)
	}

	f := NewFFmpeg(cfg)
	b := Brief{Ratio: "9:16", Skill: DefaultSkill, Model: "fake"}
	plan := ScenePlan{Title: "t", Scenes: []Scene{
		{Title: "Hi: there", Text: "It's a 'quoted' line, with: colons", Seconds: 1, Color: "#1f2937"},
		{Title: "Bye", Text: "%{eif:1/0:d} %{pts} %{localtime}", Seconds: 1, Color: "#7c2d12"},
	}}

	out := filepath.Join(t.TempDir(), "o.mp4")
	if _, err := f.Render(context.Background(), plan, b, "prompt", out, func(int) {}); err != nil {
		t.Fatal(err)
	}

	if err := f.QA(context.Background(), out, 180, 320, 2); err != nil {
		t.Fatal(err)
	}

	if err := os.WriteFile(out, []byte("truncated"), 0o600); err != nil {
		t.Fatal(err)
	}

	if err := f.QA(context.Background(), out, 180, 320, 2); err == nil {
		t.Fatal("a truncated file must fail QA")
	}

	if _, err := exec.LookPath(cfg.FFmpeg); err != nil {
		t.Fatal(err)
	}
}

func TestHungFFmpegIsKilledByTheDeadline(t *testing.T) {
	t.Setenv("STUDIO_HELPER_HANG", "1")

	f := FFmpeg{Bin: os.Args[0], Timeout: 300 * time.Millisecond}

	start := time.Now()
	err := f.run(context.Background(), t.TempDir(), f.Bin, "-version")

	if err == nil || !strings.Contains(err.Error(), "killed after") {
		t.Fatalf("err = %v, want a kill by the deadline", err)
	}

	if time.Since(start) > 10*time.Second {
		t.Fatalf("took %s, the deadline did not stop the process", time.Since(start))
	}
}

func TestPlanRejectsControlCharacters(t *testing.T) {
	raw := `{"title":"T","scenes":[{"title":"a","text":"line\nbreak","seconds":10}]}`
	if _, err := ParsePlan(raw, 10); err == nil {
		t.Fatal("control characters in scene text must be rejected")
	}

	// A percent sign is plain text: drawtext runs with expansion=none.
	ok := `{"title":"T","scenes":[{"title":"a","text":"100% %{eif:1/0:d}","seconds":10}]}`
	if _, err := ParsePlan(ok, 10); err != nil {
		t.Fatal(err)
	}
}
