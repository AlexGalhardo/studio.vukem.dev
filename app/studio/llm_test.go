package studio

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func llmBrief() Brief {
	return Brief{Goal: "g", Audience: "a", Subject: "s", Duration: 10, Ratio: "9:16", StyleSkill: "x", Language: "en", Facts: []string{"MIT licensed"}}
}

func planBody(script string) string {
	b, _ := json.Marshal(Plan{Script: script, Duration: 10, FPS: 30, Width: 1080, Height: 1920, Shots: []Shot{{Text: "hi", Start: 0, End: 9.9}}})

	return "```json\n" + string(b) + "\n```"
}

func TestLLMAdaptersParseProviderReplies(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/v1/messages":
			if r.Header.Get("x-api-key") != "k" {
				w.WriteHeader(401)

				return
			}

			_ = json.NewEncoder(w).Encode(map[string]any{"content": []map[string]string{{"type": "text", "text": planBody("MIT licensed")}}})
		case "/v1/chat/completions":
			_ = json.NewEncoder(w).Encode(map[string]any{"choices": []map[string]any{{"message": map[string]string{"content": planBody("MIT licensed")}}}})
		default:
			w.WriteHeader(500)
		}
	}))
	defer srv.Close()

	for _, model := range []string{ModelClaudeSonnet, "gpt-test"} {
		p := NewLLMPlanner(LLMConfig{Model: model, Key: "k", BaseURL: srv.URL, Client: srv.Client()})

		plan, raw, err := p.Plan(context.Background(), "prompt", llmBrief())
		if err != nil || !strings.Contains(plan.Script, "MIT") || raw == "" {
			t.Fatalf("%s: plan %+v raw %q err %v", model, plan, raw, err)
		}
	}

	bad := NewLLMPlanner(LLMConfig{Model: ModelClaudeSonnet, Key: "wrong", BaseURL: srv.URL, Client: srv.Client()})
	if _, _, err := bad.Plan(context.Background(), "p", llmBrief()); err == nil || !strings.Contains(err.Error(), "HTTP 401") || strings.Contains(err.Error(), "wrong") {
		t.Fatalf("401 error = %v, want the status without the key", err)
	}
}

func TestLLMMissingKeyAndCostCap(t *testing.T) {
	noKey := NewLLMPlanner(LLMConfig{Model: ModelClaudeSonnet})
	if _, _, err := noKey.Plan(context.Background(), "p", llmBrief()); err == nil || !strings.Contains(err.Error(), "ANTHROPIC_API_KEY") {
		t.Fatalf("err = %v, want the variable name", err)
	}

	capped := NewLLMPlanner(LLMConfig{Model: ModelClaudeOpus, Key: "k", MaxTokens: 4000, MaxCostMicros: 1000})
	if _, _, err := capped.Plan(context.Background(), "p", llmBrief()); err == nil || !strings.Contains(err.Error(), "per-job limit") {
		t.Fatalf("err = %v, want the cost cap before any call", err)
	}
}

// TestRealClaudeEndToEnd spends one small model call: brief to plan to MP4.
func TestRealClaudeEndToEnd(t *testing.T) {
	key := os.Getenv("ANTHROPIC_API_KEY")
	if os.Getenv("STUDIO_TEST_REAL_MODEL") != "1" || key == "" {
		t.Skip("set STUDIO_TEST_REAL_MODEL=1 and ANTHROPIC_API_KEY (one paid call, needs ffmpeg)")
	}

	b := llmBrief()
	b.Facts = []string{"Open source", "MIT licensed"}
	b.StyleSkill = "video-text-cards"
	prompt := Compile(b, LoadSkill(b.StyleSkill))

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	p := NewLLMPlanner(LLMConfig{Model: ModelClaudeSonnet, Key: key, MaxTokens: 1200})

	plan, _, err := p.Plan(ctx, prompt, b)
	if err != nil {
		t.Fatal(err)
	}

	root := t.TempDir()
	st := State{ID: 1, Brief: b, Prompt: prompt, Status: StatusQueued}

	var last State

	err = Run(ctx, st, Runner{Root: root, Planner: p, Save: func(_ context.Context, s State) error { last = s; return nil }})
	if err != nil || last.Status != StatusReady {
		t.Fatalf("run: %v status %s failure %q", err, last.Status, last.Failure)
	}

	if _, err := os.Stat(filepath.Join(root, "1")); err != nil {
		t.Fatal(err)
	}

	t.Logf("scenes=%d seconds=%.1f", len(plan.Shots), plan.Duration)
}
