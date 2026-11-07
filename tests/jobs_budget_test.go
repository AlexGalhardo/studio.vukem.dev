package tests

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
	"time"

	"github.com/AlexGalhardo/vukem-studio/app/jobs"
	"github.com/AlexGalhardo/vukem-studio/app/studio"
)

func TestModelBudgetAdmitsOnlyWhatFits(t *testing.T) {
	_, db := limitsApp(t)
	now := time.Now()

	var ok atomic.Int32

	inParallel(parallel*2, func(int) {
		if jobs.ReserveModelSpend(context.Background(), db, 300, 1000, now) == nil {
			ok.Add(1)
		}
	})

	if ok.Load() != 3 {
		t.Fatalf("%d reservations passed a 1000 budget at 300 each, want 3", ok.Load())
	}

	if err := jobs.ReserveModelSpend(context.Background(), db, 300, 1000, now); !errors.Is(err, studio.ErrOverBudget) {
		t.Fatalf("got %v, want the budget error", err)
	}

	// The rolling window frees the budget after 24 hours; zero disables it.
	if err := jobs.ReserveModelSpend(context.Background(), db, 300, 1000, now.Add(25*time.Hour)); err != nil {
		t.Fatalf("after the window: %v", err)
	}

	if err := jobs.ReserveModelSpend(context.Background(), db, 1<<40, 0, now); err != nil {
		t.Fatalf("disabled budget: %v", err)
	}
}

func TestDailyBudgetDefault(t *testing.T) {
	t.Parallel()

	get := func(v string) func(string) string { return func(string) string { return v } }

	for in, want := range map[string]int{"": 500, "0": 0, "1200": 1200, "-1": 500, "x": 500} {
		if got := jobs.DailyBudgetCents(get(in)); got != want {
			t.Errorf("STUDIO_DAILY_BUDGET_CENTS=%q gave %d, want %d", in, got, want)
		}
	}
}

// With the budget used up the planner must not reach the provider, and the
// job fails with a readable reason.
func TestPlannerStopsBeforeTheCallWhenOverBudget(t *testing.T) {
	t.Parallel()

	var hits atomic.Int32

	srv := httptest.NewServer(http.HandlerFunc(func(http.ResponseWriter, *http.Request) { hits.Add(1) }))
	defer srv.Close()

	p := studio.NewLLMPlanner(studio.LLMConfig{
		Model: studio.ModelClaudeSonnet, Key: "k", BaseURL: srv.URL,
		Reserve: func(context.Context, int64) error { return studio.ErrOverBudget },
	})

	dir := t.TempDir()
	st := studio.State{ID: 1, Prompt: "p", Brief: studio.Brief{
		Goal: "g", Audience: "a", Subject: "s", Duration: 5, Ratio: "9:16", StyleSkill: "traco-simples", Language: "en",
	}}

	var saved studio.State

	run := studio.Runner{Root: dir, Planner: p, Save: func(_ context.Context, s studio.State) error { saved = s; return nil }}
	if err := studio.Run(context.Background(), st, run); err != nil {
		t.Fatal(err)
	}

	if hits.Load() != 0 {
		t.Fatalf("the provider was called %d times over budget", hits.Load())
	}

	if saved.Status != studio.StatusFailed || saved.Failure != studio.ErrOverBudget.Error() {
		t.Fatalf("status %q failure %q", saved.Status, saved.Failure)
	}
}
