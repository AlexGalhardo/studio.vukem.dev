package tests

import (
	"context"
	"errors"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/AlexGalhardo/vukem/vukemtest"

	"github.com/AlexGalhardo/vukem-studio/app/jobs"
	"github.com/AlexGalhardo/vukem-studio/app/studio"
	"github.com/AlexGalhardo/vukem-studio/bootstrap"
)

const parallel = 12

func studioBrief() studio.Brief {
	return studio.Brief{Goal: "goal", Audience: "devs", Subject: "kit", Duration: 10, Ratio: "9:16",
		Skill: studio.DefaultSkill, Language: "English", Model: "claude-sonnet-5-5"}
}

func serviceFor(t *testing.T, env map[string]string) (*vukemtest.App, *studio.Service, int64) {
	t.Helper()

	app := vukemtest.New(t, bootstrap.New, studioEnv(t, env))
	register(t, app, app.Client(t), "race@example.com")

	svc, err := jobs.Studio(app.App)
	if err != nil {
		t.Fatal(err)
	}

	return app, svc, 1
}

func inParallel(n int, fn func(i int)) {
	var wg sync.WaitGroup

	start := make(chan struct{})

	for i := range n {
		wg.Add(1)

		go func() {
			defer wg.Done()

			<-start
			fn(i)
		}()
	}

	close(start)
	wg.Wait()
}

func TestDailyQuotaHoldsUnderParallelSubmits(t *testing.T) {
	t.Parallel()

	app, svc, uid := serviceFor(t, map[string]string{"STUDIO_MAX_JOBS_PER_DAY": "3"})

	var ok, limited, other atomic.Int32

	inParallel(parallel, func(int) {
		_, err := svc.Create(context.Background(), uid, studioBrief())

		switch {
		case err == nil:
			ok.Add(1)
		case errors.Is(err, studio.ErrDailyLimit):
			limited.Add(1)
		default:
			other.Add(1)
			t.Errorf("unexpected error: %v", err)
		}
	})

	if ok.Load() != 3 || limited.Load() != parallel-3 {
		t.Fatalf("created %d, limited %d, want 3 and %d", ok.Load(), limited.Load(), parallel-3)
	}

	vukemtest.AssertDatabaseCount(t, app, "videos", 3)
}

func TestQuotaWindowIsRolling(t *testing.T) {
	t.Parallel()

	_, svc, uid := serviceFor(t, map[string]string{"STUDIO_MAX_JOBS_PER_DAY": "2"})
	base := time.Now()

	for range 2 {
		if _, err := svc.Create(context.Background(), uid, studioBrief()); err != nil {
			t.Fatal(err)
		}
	}

	// The limit was used just now. Shortly before the 24-hour mark it still
	// holds, which a calendar-day counter would have reset at midnight.
	svc.Now = func() time.Time { return base.Add(23*time.Hour + 59*time.Minute) }
	if _, err := svc.Create(context.Background(), uid, studioBrief()); !errors.Is(err, studio.ErrDailyLimit) {
		t.Fatalf("at 23h59 got %v, want the daily limit", err)
	}

	svc.Now = func() time.Time { return base.Add(24*time.Hour + time.Minute) }
	if _, err := svc.Create(context.Background(), uid, studioBrief()); err != nil {
		t.Fatalf("after 24h got %v, want success", err)
	}
}
