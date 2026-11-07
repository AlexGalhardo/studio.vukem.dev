package studio

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/AlexGalhardo/vukem/database"
	"github.com/AlexGalhardo/vukem/orm"

	"github.com/AlexGalhardo/vukem-studio/app/models"
)

// MaxAttempts is how many times one job may be run, retries included.
const MaxAttempts = 3

// Errors the controller maps to a response.
var (
	ErrDailyLimit    = errors.New("daily job limit reached")
	ErrAttemptsLimit = errors.New("this job has used all its attempts")
	ErrNotRetryable  = errors.New("only a failed job can be retried")
)

// Service owns the job lifecycle. The controller creates jobs; the queue
// handler runs them.
type Service struct {
	DB       *database.DB
	Cfg      Config
	Skills   *Skills
	Planner  Planner
	Renderer Renderer
	Log      *slog.Logger
	Now      func() time.Time
}

// NewService wires a Service from cfg.
func NewService(db *database.DB, cfg Config, log *slog.Logger, now func() time.Time) *Service {
	return &Service{
		DB: db, Cfg: cfg, Skills: NewSkills(cfg.SkillsDir),
		Planner: NewPlanner(cfg, nil), Renderer: NewRenderer(cfg), Log: log, Now: now,
	}
}

// Create validates the brief against the catalog and limits, compiles the
// prompt and stores a queued job.
func (s *Service) Create(ctx context.Context, userID int64, b Brief) (models.Video, error) {
	since := s.Now().Add(-24 * time.Hour)

	n, err := orm.QueryOf[models.Video](s.DB).Where("user_id", userID).Where("created_at", ">=", since).Count(ctx)
	if err != nil {
		return models.Video{}, err
	}

	if s.Cfg.MaxJobsPerDay > 0 && int(n) >= s.Cfg.MaxJobsPerDay {
		return models.Video{}, fmt.Errorf("%w (%d per 24 hours)", ErrDailyLimit, s.Cfg.MaxJobsPerDay)
	}

	sk, err := s.Skills.Get(b.Skill)
	if err != nil {
		return models.Video{}, err
	}

	prompt, err := Compile(b, sk, s.Cfg.RenderWidth)
	if err != nil {
		return models.Video{}, err
	}

	raw, err := json.Marshal(b)
	if err != nil {
		return models.Video{}, err
	}

	v := models.Video{
		UserID: userID, Status: models.VideoQueued, Stage: "Waiting for a worker", Title: b.Subject,
		Brief: string(raw), SkillID: b.Skill, ModelID: b.Model, Prompt: prompt,
	}

	if err := orm.Create(ctx, s.DB, &v); err != nil {
		return models.Video{}, err
	}

	return v, nil
}

// Retry puts a failed job back in the queue.
func (s *Service) Retry(ctx context.Context, v *models.Video) error {
	if v.Status != models.VideoFailed {
		return ErrNotRetryable
	}

	if v.Attempts >= MaxAttempts {
		return ErrAttemptsLimit
	}

	v.Status, v.Stage, v.Progress, v.Error = models.VideoQueued, "Waiting for a worker", 0, ""

	return orm.Update(ctx, s.DB, v)
}

// Run executes one queued job. It never returns the job's own failure: a
// failed job is a stored state, not a queue retry, because every retry would
// bill another model call. It returns only storage errors.
func (s *Service) Run(ctx context.Context, id int64) (err error) {
	v, err := orm.QueryOf[models.Video](s.DB).Find(ctx, id)
	if err != nil {
		return err
	}

	if v.Status != models.VideoQueued {
		return nil
	}

	defer func() {
		if r := recover(); r != nil {
			err = s.fail(ctx, &v, fmt.Sprintf("internal error: %v", r))
		}
	}()

	v.Attempts++
	v.Error = ""

	if err := s.set(ctx, &v, models.VideoPlanning, "Writing the scene plan", 5); err != nil {
		return err
	}

	var b Brief
	if err := json.Unmarshal([]byte(v.Brief), &b); err != nil {
		return s.fail(ctx, &v, "stored brief is unreadable")
	}

	maxOut := s.Cfg.MaxOutputToken
	if worst := s.Cfg.CostMicros(v.ModelID, int64(len(v.Prompt)/3), int64(maxOut)); s.Cfg.MaxCostMicros > 0 && worst > s.Cfg.MaxCostMicros {
		return s.fail(ctx, &v, fmt.Sprintf("worst-case cost %s exceeds the per-job limit %s; lower STUDIO_MAX_OUTPUT_TOKENS, pick a cheaper model or raise STUDIO_MAX_JOB_COST_CENTS",
			usd(worst), usd(s.Cfg.MaxCostMicros)))
	}

	raw, usage, perr := s.Planner.Plan(ctx, v.ModelID, v.Prompt, maxOut)
	v.RawResponse, v.InputTokens, v.OutputTokens = raw, usage.InputTokens, usage.OutputTokens
	v.CostMicros = s.Cfg.CostMicros(v.ModelID, usage.InputTokens, usage.OutputTokens)

	if perr != nil {
		return s.fail(ctx, &v, "The model call failed: "+perr.Error())
	}

	if s.Cfg.MaxCostMicros > 0 && v.CostMicros > s.Cfg.MaxCostMicros {
		return s.fail(ctx, &v, fmt.Sprintf("cost %s exceeded the per-job limit %s", usd(v.CostMicros), usd(s.Cfg.MaxCostMicros)))
	}

	plan, perr := ParsePlan(raw, b.Duration)
	if perr != nil {
		return s.fail(ctx, &v, "The model returned an unusable plan: "+perr.Error())
	}

	planJSON, _ := json.Marshal(plan)
	v.Plan, v.Title = string(planJSON), plan.Title

	if err := s.set(ctx, &v, models.VideoRendering, "Rendering the video", 20); err != nil {
		return err
	}

	rel := filepath.ToSlash(filepath.Join(strconv.FormatInt(v.UserID, 10), strconv.FormatInt(v.ID, 10)+".mp4"))
	out := filepath.Join(s.Cfg.OutputDir, filepath.FromSlash(rel))

	last := 0
	car, rerr := s.Renderer.Render(ctx, plan, b, v.Prompt, out, func(p int) {
		if p >= last+10 || p == 100 {
			last = p
			v.Progress = 20 + p*80/100
			_ = orm.Update(ctx, s.DB, &v)
		}
	})

	if rerr != nil {
		return s.fail(ctx, &v, "The render failed: "+rerr.Error())
	}

	side, _ := json.Marshal(car)
	if err := os.WriteFile(out+".json", side, 0o600); err != nil {
		return s.fail(ctx, &v, "could not store the sidecar: "+err.Error())
	}

	v.Sidecar, v.OutputPath = string(side), rel

	return s.set(ctx, &v, models.VideoReady, "Ready", 100)
}

func (s *Service) set(ctx context.Context, v *models.Video, status, stage string, progress int) error {
	v.Status, v.Stage, v.Progress = status, stage, progress

	return orm.Update(ctx, s.DB, v)
}

func (s *Service) fail(ctx context.Context, v *models.Video, reason string) error {
	if len(reason) > 800 {
		reason = reason[:800]
	}

	s.Log.Warn("video job failed", "video", v.ID, "reason", reason)

	v.Status, v.Stage, v.Error = models.VideoFailed, "Failed", reason

	// A retry must not leave the previous failure's partial output public.
	v.OutputPath = ""

	return orm.Update(ctx, s.DB, v)
}

func usd(micros int64) string { return fmt.Sprintf("$%.4f", float64(micros)/1_000_000) }
