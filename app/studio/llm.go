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

// Model ids the adapters know prices for. Any other id is sent to OpenAI.
const (
	ModelClaudeSonnet = "claude-sonnet-5-5"
	ModelClaudeOpus   = "claude-opus-5-5"
)

// Errors a model adapter returns. Run shows them to the operator as written.
var (
	ErrNoKey     = errors.New("API key for this model's provider is not configured")
	ErrModelCall = errors.New("the model call failed")
	ErrOverCost  = errors.New("the worst-case cost is over the per-job limit")
)

const maxReplyBytes = 1 << 20

// LLMConfig configures one hosted-model planner.
type LLMConfig struct {
	Model     string
	Key       string
	BaseURL   string
	Client    *http.Client
	MaxTokens int
	// MaxCostMicros caps the worst-case cost of one call in USD micros; zero
	// means no cap.
	MaxCostMicros int64
}

// LLMPlanner asks Claude or OpenAI for the scene plan. The prompt the job
// stored is sent as is, followed by the JSON shape the worker can render.
type LLMPlanner struct{ LLMConfig }

// NewLLMPlanner fills defaults.
func NewLLMPlanner(c LLMConfig) LLMPlanner {
	if c.Client == nil {
		c.Client = &http.Client{Timeout: 3 * time.Minute}
	}

	if c.MaxTokens <= 0 {
		c.MaxTokens = 4000
	}

	if c.BaseURL == "" {
		c.BaseURL = "https://api.openai.com"
		if isClaude(c.Model) {
			c.BaseURL = "https://api.anthropic.com"
		}
	}

	return LLMPlanner{c}
}

func isClaude(model string) bool { return strings.HasPrefix(model, "claude-") }

// ID is the model id stored on the job.
func (p LLMPlanner) ID() string { return p.Model }

// Plan implements Planner.
func (p LLMPlanner) Plan(ctx context.Context, prompt string, brief Brief) (Plan, string, error) {
	if p.Key == "" {
		env := "OPENAI_API_KEY"
		if isClaude(p.Model) {
			env = "ANTHROPIC_API_KEY"
		}

		return Plan{}, "", fmt.Errorf("%w: set %s", ErrNoKey, env)
	}

	full := prompt + planShape(brief)

	// A longer cut needs a longer plan: 30 more output tokens per second.
	tokens := p.MaxTokens + 30*brief.Duration

	if p.MaxCostMicros > 0 {
		if worst := EstimateCostMicros(p.Model, int64(len(full)/3), int64(tokens)); worst > p.MaxCostMicros {
			return Plan{}, "", fmt.Errorf("%w: $%.4f against $%.4f; lower STUDIO_MAX_OUTPUT_TOKENS, pick a cheaper model or raise STUDIO_MAX_JOB_COST_CENTS",
				ErrOverCost, float64(worst)/1e6, float64(p.MaxCostMicros)/1e6)
		}
	}

	raw, err := p.call(ctx, full, tokens)
	if err != nil {
		return Plan{}, "", fmt.Errorf("%w: %s", ErrModelCall, err)
	}

	// Keep only the outermost JSON object: models wrap it in fences or prose.
	if start, end := strings.Index(raw, "{"), strings.LastIndex(raw, "}"); start >= 0 && end > start {
		raw = raw[start : end+1]
	}

	plan, err := ParsePlan(raw)

	return plan, raw, err
}

func planShape(b Brief) string {
	w, h, _ := Frame(b.Ratio)

	return fmt.Sprintf(`

Answer with one JSON object and nothing else, in this shape:
{"script": "the full on-screen text, containing every must-keep fact verbatim", "duration": %d, "fps": %d, "width": %d, "height": %d, "voice": %t,
 "shots": [{"text": "caption text, no braces or backslashes", "start": 0, "end": %.1f}]}
Shots follow each other in order, each end is greater than its start, and the last shot must end 0.1 seconds before the duration.
`, b.Duration, DrawFPS(b.StyleSkill), w, h, b.Spoken(), float64(b.Duration)-0.1)
}

// EstimateCostMicros estimates USD micros from a per-million-token table. It
// is a guard, not an invoice.
func EstimateCostMicros(model string, in, out int64) int64 {
	pin, pout := int64(5_000_000), int64(20_000_000)

	switch model {
	case ModelClaudeSonnet:
		pin, pout = 3_000_000, 15_000_000
	case ModelClaudeOpus:
		pin, pout = 15_000_000, 75_000_000
	}

	return (in*pin + out*pout) / 1_000_000
}

func (p LLMPlanner) call(ctx context.Context, prompt string, tokens int) (string, error) {
	if isClaude(p.Model) {
		body := map[string]any{"model": p.Model, "max_tokens": tokens, "messages": []map[string]string{{"role": "user", "content": prompt}}}

		var res struct {
			Content []struct {
				Type string `json:"type"`
				Text string `json:"text"`
			} `json:"content"`
		}

		hdr := map[string]string{"x-api-key": p.Key, "anthropic-version": "2023-06-01"}
		if err := postJSON(ctx, p.Client, p.BaseURL+"/v1/messages", hdr, body, &res); err != nil {
			return "", err
		}

		var text strings.Builder

		for _, part := range res.Content {
			if part.Type == "text" {
				text.WriteString(part.Text)
			}
		}

		return text.String(), nil
	}

	body := map[string]any{
		"model": p.Model, "max_completion_tokens": tokens,
		"response_format": map[string]string{"type": "json_object"},
		"messages":        []map[string]string{{"role": "user", "content": prompt}},
	}

	var res struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
	}

	if err := postJSON(ctx, p.Client, p.BaseURL+"/v1/chat/completions", map[string]string{"Authorization": "Bearer " + p.Key}, body, &res); err != nil {
		return "", err
	}

	if len(res.Choices) == 0 {
		return "", errors.New("reply has no choices")
	}

	return res.Choices[0].Message.Content, nil
}

// postJSON sends body and decodes the reply. A provider error is reduced to
// its status so a key or prompt echoed back never reaches a job row.
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
		return errors.New("request failed or timed out")
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
