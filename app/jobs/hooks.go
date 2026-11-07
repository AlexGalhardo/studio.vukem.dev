package jobs

import (
	"context"
	"strconv"
	"strings"
	"sync"

	vukem "github.com/AlexGalhardo/vukem"

	"github.com/AlexGalhardo/vukem-studio/app/studio"
)

// Per-app overrides. Tests swap the planner or the renderer on their own
// app; a parallel test does not see the swap.
var (
	planners  sync.Map
	renderers sync.Map

	rootMu sync.Mutex
	roots  = map[*vukem.App]string{}
)

// UsePlanner makes app plan with p. The default is the local planner.
func UsePlanner(app *vukem.App, p studio.Planner) { planners.Store(app, p) }

// PlannerFor returns the planner for app.
func PlannerFor(app *vukem.App) studio.Planner {
	if app != nil {
		if v, ok := planners.Load(app); ok {
			return v.(studio.Planner)
		}
	}

	return plannerFromEnv(app)
}

// plannerFromEnv picks the hosted model: STUDIO_MODEL when set, else
// claude-sonnet-5-5 when ANTHROPIC_API_KEY is set, else the local planner.
// An explicit model without its key fails each job with a readable reason.
func plannerFromEnv(app *vukem.App) studio.Planner {
	if app == nil {
		return studio.LocalPlanner{}
	}

	model := app.Source.Get("STUDIO_MODEL")
	if model == "" && app.Source.Get("ANTHROPIC_API_KEY") != "" {
		model = studio.ModelClaudeSonnet
	}

	if model == "" || model == "local-planner" {
		return studio.LocalPlanner{}
	}

	key := app.Source.Get("OPENAI_API_KEY")
	if strings.HasPrefix(model, "claude-") {
		key = app.Source.Get("ANTHROPIC_API_KEY")
	}

	maxTokens, _ := strconv.Atoi(app.Source.Get("STUDIO_MAX_OUTPUT_TOKENS"))

	costCents := 100
	if v, err := strconv.Atoi(app.Source.Get("STUDIO_MAX_JOB_COST_CENTS")); err == nil && v >= 0 {
		costCents = v
	}

	budget := int64(DailyBudgetCents(app.Source.Get)) * 10_000

	return studio.NewLLMPlanner(studio.LLMConfig{
		Model: model, Key: key, MaxTokens: maxTokens, MaxCostMicros: int64(costCents) * 10_000,
		Reserve: func(ctx context.Context, micros int64) error {
			db, err := app.DB()
			if err != nil {
				return err
			}

			return ReserveModelSpend(ctx, db, micros, budget, app.Now())
		},
		BaseURL: app.Source.Get("STUDIO_LLM_BASE_URL"),
	})
}

// UseRenderer makes app encode with r. The default follows STUDIO_RENDERER.
func UseRenderer(app *vukem.App, r studio.Renderer) { renderers.Store(app, r) }

// RendererFor returns the renderer for app.
func RendererFor(app *vukem.App) studio.Renderer {
	if app != nil {
		if v, ok := renderers.Load(app); ok {
			return v.(studio.Renderer)
		}

		switch app.Source.Get("STUDIO_RENDERER") {
		case "hyperframes":
			return studio.HyperFramesRenderer{}
		case "remotion":
			return studio.RemotionRenderer{}
		}
	}

	return studio.FFmpegRenderer{}
}

// RootFor is the directory that holds one folder per job. Tests and deploys
// can set STUDIO_STORAGE. A test process otherwise gets a private temp dir
// so two apps cannot overwrite each other's job 1.
func RootFor(app *vukem.App) string {
	rootMu.Lock()
	defer rootMu.Unlock()

	if root, ok := roots[app]; ok {
		return root
	}

	root := "storage/renders"

	if app != nil {
		if dir := app.Source.Get("STUDIO_STORAGE"); dir != "" {
			root = dir
		} else if app.Kind == vukem.KindTest {
			if dir, err := mkdirTemp(); err == nil {
				root = dir
			}
		}
	}

	roots[app] = root

	return root
}
