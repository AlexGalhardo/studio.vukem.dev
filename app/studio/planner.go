package studio

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// Usage is the token count of one model call.
type Usage struct {
	InputTokens  int64 `json:"input_tokens"`
	OutputTokens int64 `json:"output_tokens"`
}

// Planner turns a compiled prompt into the model's raw reply. Parsing and
// validation stay outside so every adapter shares them and a bad reply can
// be stored verbatim.
type Planner interface {
	Plan(ctx context.Context, model, prompt string, maxOutputTokens int) (raw string, u Usage, err error)
}

// ErrNoKey means the provider for the chosen model has no API key.
var ErrNoKey = errors.New("studio: API key for this model's provider is not configured")

const maxReplyBytes = 1 << 20

// NewPlanner returns the adapter set for cfg. The fake adapter answers every
// model when STUDIO_PROVIDER=fake; otherwise the model id picks the provider.
func NewPlanner(cfg Config, client *http.Client) Planner {
	if client == nil {
		client = &http.Client{Timeout: 3 * time.Minute}
	}

	if cfg.Provider == ProviderFake {
		return Fake{Mode: cfg.FakePlanner}
	}

	return Router{
		Anthropic: Claude{Key: cfg.AnthropicKey, BaseURL: "https://api.anthropic.com", Client: client},
		OpenAI:    OpenAI{Key: cfg.OpenAIKey, BaseURL: "https://api.openai.com", Client: client},
	}
}

// Router sends a model id to its provider's adapter.
type Router struct{ Anthropic, OpenAI Planner }

// Plan implements Planner.
func (r Router) Plan(ctx context.Context, model, prompt string, max int) (string, Usage, error) {
	if ProviderFor(model) == "anthropic" {
		return r.Anthropic.Plan(ctx, model, prompt, max)
	}

	return r.OpenAI.Plan(ctx, model, prompt, max)
}

// Claude calls the Anthropic Messages API.
type Claude struct {
	Key, BaseURL string
	Client       *http.Client
}

// Plan implements Planner.
func (c Claude) Plan(ctx context.Context, model, prompt string, max int) (string, Usage, error) {
	if c.Key == "" {
		return "", Usage{}, fmt.Errorf("%w: set ANTHROPIC_API_KEY", ErrNoKey)
	}

	body := map[string]any{
		"model": model, "max_tokens": max,
		"messages": []map[string]string{{"role": "user", "content": prompt}},
	}

	var res struct {
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
		Usage struct {
			In  int64 `json:"input_tokens"`
			Out int64 `json:"output_tokens"`
		} `json:"usage"`
	}

	hdr := map[string]string{"x-api-key": c.Key, "anthropic-version": "2023-06-01"}
	if err := postJSON(ctx, c.Client, c.BaseURL+"/v1/messages", hdr, body, &res); err != nil {
		return "", Usage{}, fmt.Errorf("anthropic: %w", err)
	}

	var text strings.Builder

	for _, part := range res.Content {
		if part.Type == "text" {
			text.WriteString(part.Text)
		}
	}

	return text.String(), Usage{InputTokens: res.Usage.In, OutputTokens: res.Usage.Out}, nil
}

// OpenAI calls the Chat Completions API.
type OpenAI struct {
	Key, BaseURL string
	Client       *http.Client
}

// Plan implements Planner.
func (o OpenAI) Plan(ctx context.Context, model, prompt string, max int) (string, Usage, error) {
	if o.Key == "" {
		return "", Usage{}, fmt.Errorf("%w: set OPENAI_API_KEY", ErrNoKey)
	}

	body := map[string]any{
		"model": model, "max_completion_tokens": max,
		"response_format": map[string]string{"type": "json_object"},
		"messages":        []map[string]string{{"role": "user", "content": prompt}},
	}

	var res struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
		Usage struct {
			In  int64 `json:"prompt_tokens"`
			Out int64 `json:"completion_tokens"`
		} `json:"usage"`
	}

	hdr := map[string]string{"Authorization": "Bearer " + o.Key}
	if err := postJSON(ctx, o.Client, o.BaseURL+"/v1/chat/completions", hdr, body, &res); err != nil {
		return "", Usage{}, fmt.Errorf("openai: %w", err)
	}

	if len(res.Choices) == 0 {
		return "", Usage{}, errors.New("openai: reply has no choices")
	}

	return res.Choices[0].Message.Content, Usage{InputTokens: res.Usage.In, OutputTokens: res.Usage.Out}, nil
}

// postJSON sends body and decodes the reply. The provider's error text is
// reduced to its status so a key or prompt echoed back never reaches a job.
func postJSON(ctx context.Context, client *http.Client, url string, hdr map[string]string, body, out any) error {
	b, err := json.Marshal(body)
	if err != nil {
		return err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(b))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")

	for k, v := range hdr {
		req.Header.Set(k, v)
	}

	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", errors.Unwrap(err))
	}

	defer func() { _ = resp.Body.Close() }()

	data, err := io.ReadAll(io.LimitReader(resp.Body, maxReplyBytes))
	if err != nil {
		return err
	}

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("HTTP %d from the model provider", resp.StatusCode)
	}

	return json.Unmarshal(data, out)
}

// Fake is the adapter tests and demos use; it never leaves the process.
// Mode: "ok" (valid plan sized to the prompt), "invalid" (not JSON), "error".
type Fake struct{ Mode string }

// Plan implements Planner.
func (f Fake) Plan(_ context.Context, _, prompt string, _ int) (string, Usage, error) {
	u := Usage{InputTokens: int64(len(prompt) / 4), OutputTokens: 120}

	switch f.Mode {
	case "error":
		return "", Usage{}, errors.New("fake: model unavailable")
	case "invalid":
		return "I cannot help with that.", u, nil
	}

	secs := fakeDuration(prompt)
	half := float64(secs) / 2

	plan := ScenePlan{
		Title:       "Fake plan",
		Description: "A deterministic plan for tests.",
		Scenes: []Scene{
			{Title: "Hook", Text: "Start here", Seconds: half, Color: "#1f2937"},
			{Title: "Offer", Text: "Take the next step", Seconds: float64(secs) - half, Color: "#7c2d12"},
		},
	}

	b, _ := json.Marshal(plan)

	return "```json\n" + string(b) + "\n```", u, nil
}

// fakeDuration reads "Total duration: N seconds" from a compiled prompt.
func fakeDuration(prompt string) int {
	var n int

	if _, rest, ok := strings.Cut(prompt, "Total duration: "); ok {
		_, _ = fmt.Sscanf(rest, "%d", &n)
	}

	if n <= 0 {
		n = MinDuration
	}

	return n
}
