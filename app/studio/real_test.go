package studio

import (
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"
)

// TestRealClaudeEndToEnd spends one small model call: brief to plan to MP4.
func TestRealClaudeEndToEnd(t *testing.T) {
	if os.Getenv("STUDIO_TEST_REAL_MODEL") != "1" || os.Getenv("ANTHROPIC_API_KEY") == "" {
		t.Skip("set STUDIO_TEST_REAL_MODEL=1 and ANTHROPIC_API_KEY (one paid call, needs ffmpeg)")
	}

	cfg, err := LoadConfig(func(k string) string {
		if k == "STUDIO_RENDER_WIDTH" {
			return "360"
		}

		return os.Getenv(k)
	})
	if err != nil {
		t.Fatal(err)
	}

	b := Brief{Goal: "Get signups", Audience: "indie developers", Subject: "Studio, a video dashboard", Duration: 10, Ratio: "9:16",
		Skill: DefaultSkill, Language: "English", Model: DefaultAnthropicModel, Facts: "Open source\nMIT licensed", CTA: "Star it on GitHub"}

	sk, err := NewSkills("").Get(b.Skill)
	if err != nil {
		t.Fatal(err)
	}

	prompt, err := Compile(b, sk, cfg.RenderWidth)
	if err != nil {
		t.Fatal(err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	raw, usage, err := NewPlanner(cfg, nil).Plan(ctx, b.Model, prompt, 1200)
	if err != nil {
		t.Fatal(err)
	}

	t.Logf("tokens in=%d out=%d cost=%d micros", usage.InputTokens, usage.OutputTokens, cfg.CostMicros(b.Model, usage.InputTokens, usage.OutputTokens))

	plan, err := ParsePlan(raw, b.Duration)
	if err != nil {
		t.Fatalf("plan: %v\nraw: %s", err, raw)
	}

	out := filepath.Join(t.TempDir(), "real.mp4")
	if _, err := NewFFmpeg(cfg).Render(ctx, plan, b, prompt, out, func(int) {}); err != nil {
		t.Fatal(err)
	}

	st, err := os.Stat(out)
	if err != nil || st.Size() == 0 {
		t.Fatalf("no output: %v", err)
	}

	t.Logf("scenes=%d seconds=%.1f bytes=%d", len(plan.Scenes), plan.TotalSeconds(), st.Size())
}
