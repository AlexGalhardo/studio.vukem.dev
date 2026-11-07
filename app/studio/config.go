// Package studio holds the video pipeline: brief validation, the prompt
// compiler, the model adapters, the scene plan and the FFmpeg renderer.
package studio

import (
	"fmt"
	"strconv"
	"strings"
)

// Provider names accepted by STUDIO_PROVIDER.
const (
	ProviderAuto = "auto"
	ProviderFake = "fake"
)

// Config is read from the environment. No value here is a secret except the
// two API keys, which are never logged or stored.
type Config struct {
	AnthropicKey   string
	OpenAIKey      string
	OpenAIModel    string
	Models         []string
	Provider       string
	OutputDir      string
	SkillsDir      string
	FFmpeg         string
	FFprobe        string
	FontFile       string
	RenderWidth    int
	MaxJobsPerDay  int
	MaxCostMicros  int64
	MaxOutputToken int
	// PriceIn and PriceOut are USD micros per million tokens, per model id.
	PriceIn  map[string]int64
	PriceOut map[string]int64

	FakePlanner    string
	FakeRenderFail bool
	Production     bool
}

// DefaultAnthropicModel is the model a brief selects when it names none.
const DefaultAnthropicModel = "claude-sonnet-5-5"

// LoadConfig reads STUDIO_* and provider keys through getenv (app.Source.Get).
func LoadConfig(getenv func(string) string) (Config, error) {
	str := func(key, def string) string {
		if v := strings.TrimSpace(getenv(key)); v != "" {
			return v
		}

		return def
	}

	num := func(key string, def int) (int, error) {
		v := strings.TrimSpace(getenv(key))
		if v == "" {
			return def, nil
		}

		n, err := strconv.Atoi(v)
		if err != nil || n < 0 {
			return 0, fmt.Errorf("studio: %s must be a non-negative integer, got %q", key, v)
		}

		return n, nil
	}

	c := Config{
		AnthropicKey: strings.TrimSpace(getenv("ANTHROPIC_API_KEY")),
		OpenAIKey:    strings.TrimSpace(getenv("OPENAI_API_KEY")),
		OpenAIModel:  str("STUDIO_OPENAI_MODEL", "gpt-5.5"),
		Provider:     str("STUDIO_PROVIDER", ProviderAuto),
		OutputDir:    str("STUDIO_OUTPUT_DIR", "storage/videos"),
		SkillsDir:    strings.TrimSpace(getenv("STUDIO_SKILLS_DIR")),
		FFmpeg:       str("STUDIO_FFMPEG", "ffmpeg"),
		FFprobe:      str("STUDIO_FFPROBE", "ffprobe"),
		FontFile:     strings.TrimSpace(getenv("STUDIO_FONT_FILE")),
		FakePlanner:  str("STUDIO_FAKE_PLANNER", "ok"),
		Production:   getenv("APP_ENV") == "production",
	}
	c.FakeRenderFail = getenv("STUDIO_FAKE_RENDER_FAIL") == "true"

	c.Models = []string{DefaultAnthropicModel, "claude-opus-5-5", c.OpenAIModel}
	if extra := str("STUDIO_MODELS", ""); extra != "" {
		c.Models = splitList(extra)
	}

	var err error

	if c.RenderWidth, err = num("STUDIO_RENDER_WIDTH", 1080); err != nil {
		return c, err
	}

	if c.RenderWidth < 64 || c.RenderWidth > 2160 {
		return c, fmt.Errorf("studio: STUDIO_RENDER_WIDTH must be between 64 and 2160, got %d", c.RenderWidth)
	}

	if c.MaxJobsPerDay, err = num("STUDIO_MAX_JOBS_PER_DAY", 20); err != nil {
		return c, err
	}

	if c.MaxOutputToken, err = num("STUDIO_MAX_OUTPUT_TOKENS", 4000); err != nil {
		return c, err
	}

	costCents, err := num("STUDIO_MAX_JOB_COST_CENTS", 100)
	if err != nil {
		return c, err
	}

	c.MaxCostMicros = int64(costCents) * 10_000

	// Estimates, not invoices: override per model with STUDIO_PRICE_<kind>_<MODEL>.
	c.PriceIn = map[string]int64{DefaultAnthropicModel: 3_000_000, "claude-opus-5-5": 15_000_000}
	c.PriceOut = map[string]int64{DefaultAnthropicModel: 15_000_000, "claude-opus-5-5": 75_000_000}

	if c.Production && c.Provider == ProviderFake {
		return c, fmt.Errorf("studio: STUDIO_PROVIDER=fake is refused when APP_ENV=production")
	}

	return c, nil
}

func splitList(s string) []string {
	var out []string

	for _, p := range strings.Split(s, ",") {
		if p = strings.TrimSpace(p); p != "" {
			out = append(out, p)
		}
	}

	return out
}

// ProviderFor maps a model id to its provider name.
func ProviderFor(model string) string {
	if strings.HasPrefix(model, "claude-") {
		return "anthropic"
	}

	return "openai"
}

// ModelAllowed reports whether model is one the operator may pick.
func (c Config) ModelAllowed(model string) bool {
	for _, m := range c.Models {
		if m == model {
			return true
		}
	}

	return false
}

// CostMicros estimates the USD micros of a call.
func (c Config) CostMicros(model string, in, out int64) int64 {
	pin, pout := c.PriceIn[model], c.PriceOut[model]
	if pin == 0 && pout == 0 {
		pin, pout = 5_000_000, 20_000_000
	}

	return (in*pin + out*pout) / 1_000_000
}
