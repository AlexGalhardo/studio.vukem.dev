package models

import "github.com/AlexGalhardo/vukem/orm"

// Video statuses, in order: queued, planning, rendering, then ready or failed.
const (
	VideoQueued    = "queued"
	VideoPlanning  = "planning"
	VideoRendering = "rendering"
	VideoReady     = "ready"
	VideoFailed    = "failed"
)

// Video is one job: the brief, the compiled prompt, the model's plan, the
// render state and the stored output.
type Video struct {
	orm.Model

	UserID       int64  `json:"user_id"`
	Status       string `json:"status"`
	Stage        string `json:"stage"`
	Progress     int    `json:"progress"`
	Attempts     int    `json:"attempts"`
	Title        string `json:"title"`
	Brief        string `json:"brief"`
	SkillID      string `json:"skill_id"`
	ModelID      string `json:"model_id"`
	Prompt       string `json:"prompt"`
	Plan         string `json:"plan"`
	RawResponse  string `json:"raw_response"`
	Error        string `json:"error"`
	OutputPath   string `json:"-"`
	Sidecar      string `json:"sidecar"`
	InputTokens  int64  `json:"input_tokens"`
	OutputTokens int64  `json:"output_tokens"`
	CostMicros   int64  `json:"cost_micros"`
	// CreatedUnix is the creation time in epoch milliseconds, written by the
	// quota code and compared as an integer so no timestamp text format matters.
	CreatedUnix int64 `json:"-"`
}

// Table names the table explicitly.
func (Video) Table() string { return "videos" }
