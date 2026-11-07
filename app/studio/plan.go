package studio

import (
	"context"
	"encoding/json"
	"strings"
	"unicode"
)

// Shot is one card in the plan.
type Shot struct {
	Text  string  `json:"text"`
	Start float64 `json:"start"`
	End   float64 `json:"end"`
}

// Plan is the structured scene plan a model adapter returns.
type Plan struct {
	Script   string  `json:"script"`
	Duration float64 `json:"duration"`
	FPS      int     `json:"fps"`
	Width    int     `json:"width"`
	Height   int     `json:"height"`
	Shots    []Shot  `json:"shots"`
	Voice    bool    `json:"voice"`
}

// Limits on what a model may put into a plan.
const (
	MaxShots       = 200
	MaxShotRunes   = 500
	MaxScriptRunes = 5000
)

// safeCaption rejects what libass would interpret instead of draw: control
// characters, ASS override blocks ({...}) and backslash escapes. A percent
// sign is plain text, since captions are burned from an SRT file and no
// filter expands them.
func safeCaption(s string) bool {
	for _, r := range s {
		if unicode.IsControl(r) || r == '{' || r == '}' || r == '\\' {
			return false
		}
	}

	return true
}

// Valid reports whether the plan has the fields the worker can render.
func (p Plan) Valid() bool {
	if strings.TrimSpace(p.Script) == "" || p.Duration <= 0 || p.Width <= 0 || p.Height <= 0 || p.FPS <= 0 {
		return false
	}

	if len(p.Shots) == 0 {
		return false
	}

	if len(p.Shots) > MaxShots || len([]rune(p.Script)) > MaxScriptRunes {
		return false
	}

	for _, shot := range p.Shots {
		if strings.TrimSpace(shot.Text) == "" || shot.End <= shot.Start || len([]rune(shot.Text)) > MaxShotRunes || !safeCaption(shot.Text) {
			return false
		}
	}

	return true
}

// ParsePlan decodes a model response. Invalid JSON or a plan that fails
// Valid is an error; the caller stores the raw response on the failed job.
func ParsePlan(raw string) (Plan, error) {
	var plan Plan
	if err := json.Unmarshal([]byte(raw), &plan); err != nil {
		return Plan{}, err
	}

	if !plan.Valid() {
		return plan, errInvalidPlan
	}

	return plan, nil
}

// Planner turns a prompt into a scene plan. The raw string is what the model
// returned, stored even when parsing fails.
type Planner interface {
	ID() string
	Plan(ctx context.Context, prompt string, brief Brief) (plan Plan, raw string, err error)
}

// LocalPlanner is the no-network adapter. It writes a deterministic plan from
// the brief so a silent fixture renders without an API key. The model id is
// local-planner.
type LocalPlanner struct{}

// ID is the model id stored on the job.
func (LocalPlanner) ID() string { return "local-planner" }

// Plan returns a plan whose script copies every must-keep fact and whose
// duration is the brief duration.
func (LocalPlanner) Plan(_ context.Context, _ string, brief Brief) (Plan, string, error) {
	width, height, ok := Frame(brief.Ratio)
	if !ok {
		return Plan{}, "", errInvalidPlan
	}

	script := scriptOf(brief)
	duration := float64(brief.Duration)
	end := duration - 0.1

	if end <= 0 {
		end = duration
	}

	plan := Plan{
		Script:   script,
		Duration: duration,
		FPS:      DrawFPS(brief.StyleSkill),
		Width:    width,
		Height:   height,
		Voice:    brief.Spoken(),
		Shots: []Shot{{
			Text:  script,
			Start: 0,
			End:   end,
		}},
	}

	raw, err := json.Marshal(plan)
	if err != nil {
		return Plan{}, "", err
	}

	// Round-trip so a broken encoder cannot store a plan the worker did not parse.
	parsed, err := ParsePlan(string(raw))
	if err != nil {
		return Plan{}, string(raw), err
	}

	return parsed, string(raw), nil
}

func scriptOf(brief Brief) string {
	parts := []string{strings.TrimSpace(brief.Subject), strings.TrimSpace(brief.Goal)}

	parts = append(parts, brief.Facts...)

	if cta := strings.TrimSpace(brief.CallToAction); cta != "" {
		parts = append(parts, cta)
	}

	return strings.Join(parts, " ")
}
