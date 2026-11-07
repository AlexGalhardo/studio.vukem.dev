package tests

import (
	"context"
	"sync/atomic"
	"testing"

	"github.com/AlexGalhardo/vukem/orm"

	"github.com/AlexGalhardo/vukem-studio/app/models"
	"github.com/AlexGalhardo/vukem-studio/app/studio"
)

type countingPlanner struct {
	studio.Planner
	calls atomic.Int32
}

func (c *countingPlanner) Plan(ctx context.Context, m, p string, n int) (string, studio.Usage, error) {
	c.calls.Add(1)

	return c.Planner.Plan(ctx, m, p, n)
}

func TestRunClaimsAJobOnce(t *testing.T) {
	t.Parallel()

	_, svc, uid := serviceFor(t, nil)

	v, err := svc.Create(context.Background(), uid, studioBrief())
	if err != nil {
		t.Fatal(err)
	}

	cp := &countingPlanner{Planner: svc.Planner}
	svc.Planner = cp

	inParallel(parallel, func(int) {
		if err := svc.Run(context.Background(), v.ID); err != nil {
			t.Errorf("run: %v", err)
		}
	})

	got, err := orm.QueryOf[models.Video](svc.DB).Find(context.Background(), v.ID)
	if err != nil {
		t.Fatal(err)
	}

	if cp.calls.Load() != 1 || got.Attempts != 1 || got.Status != models.VideoReady {
		t.Fatalf("model calls %d, attempts %d, status %s; want 1, 1, ready", cp.calls.Load(), got.Attempts, got.Status)
	}
}

func TestRetryCannotBypassTheAttemptLimit(t *testing.T) {
	t.Parallel()

	_, svc, uid := serviceFor(t, map[string]string{"STUDIO_FAKE_PLANNER": "error"})

	v, err := svc.Create(context.Background(), uid, studioBrief())
	if err != nil {
		t.Fatal(err)
	}

	for range studio.MaxAttempts {
		if err := svc.Run(context.Background(), v.ID); err != nil {
			t.Fatal(err)
		}

		cur, _ := orm.QueryOf[models.Video](svc.DB).Find(context.Background(), v.ID)
		if cur.Attempts < studio.MaxAttempts {
			if err := svc.Retry(context.Background(), &cur); err != nil {
				t.Fatal(err)
			}
		}
	}

	// All attempts are spent: no parallel retry may re-queue it.
	var won atomic.Int32

	inParallel(parallel, func(int) {
		cur, _ := orm.QueryOf[models.Video](svc.DB).Find(context.Background(), v.ID)
		if svc.Retry(context.Background(), &cur) == nil {
			won.Add(1)
		}
	})

	if won.Load() != 0 {
		t.Fatalf("%d retries passed the attempt limit", won.Load())
	}
}

func TestParallelRetriesQueueOnce(t *testing.T) {
	t.Parallel()

	_, svc, uid := serviceFor(t, map[string]string{"STUDIO_FAKE_PLANNER": "error"})

	v, err := svc.Create(context.Background(), uid, studioBrief())
	if err != nil {
		t.Fatal(err)
	}

	if err := svc.Run(context.Background(), v.ID); err != nil {
		t.Fatal(err)
	}

	var won atomic.Int32

	inParallel(parallel, func(int) {
		cur, _ := orm.QueryOf[models.Video](svc.DB).Find(context.Background(), v.ID)
		if svc.Retry(context.Background(), &cur) == nil {
			won.Add(1)
		}
	})

	if won.Load() != 1 {
		t.Fatalf("%d retries won, want exactly 1", won.Load())
	}
}
