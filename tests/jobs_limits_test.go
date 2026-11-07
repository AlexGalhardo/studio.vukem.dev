package tests

import (
	"context"
	"errors"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/AlexGalhardo/vukem/database"
	"github.com/AlexGalhardo/vukem/orm"
	"github.com/AlexGalhardo/vukem/vukemtest"

	"github.com/AlexGalhardo/vukem-studio/app/jobs"
	"github.com/AlexGalhardo/vukem-studio/app/models"
	"github.com/AlexGalhardo/vukem-studio/app/studio"
	"github.com/AlexGalhardo/vukem-studio/bootstrap"
)

const parallel = 12

func limitsApp(t *testing.T) (*vukemtest.App, *database.DB) {
	t.Helper()

	app := vukemtest.New(t, bootstrap.New)
	register(t, app, app.Client(t), "race@example.com")

	db, err := app.DB()
	if err != nil {
		t.Fatal(err)
	}

	return app, db
}

func newJob(status string) models.Job {
	return models.Job{UserID: 1, Status: status, Goal: "g", Audience: "a", Subject: "s", Duration: 5, Ratio: "9:16",
		StyleSkill: "x", Language: "en", Prompt: "p", ModelID: "m"}
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

func TestQuotaHoldsUnderParallelSubmits(t *testing.T) {
	t.Parallel()

	app, db := limitsApp(t)

	var ok, limited atomic.Int32

	inParallel(parallel, func(int) {
		row := newJob(studio.StatusQueued)

		switch err := jobs.CreateWithQuota(context.Background(), db, &row, 3, time.Now()); {
		case err == nil:
			ok.Add(1)
		case errors.Is(err, jobs.ErrQuota):
			limited.Add(1)
		default:
			t.Errorf("unexpected error: %v", err)
		}
	})

	if ok.Load() != 3 || limited.Load() != parallel-3 {
		t.Fatalf("created %d, limited %d, want 3 and %d", ok.Load(), limited.Load(), parallel-3)
	}

	vukemtest.AssertDatabaseCount(t, app, "jobs", 3)
}

// Rows 23h59m and 24h01m old land on the right side of the window, and the
// window rolls: a limit used just now still holds shortly before 24 hours.
func TestQuotaWindowIsRollingAndCountsIntegers(t *testing.T) {
	t.Parallel()

	_, db := limitsApp(t)
	now := time.Now().UTC()

	for _, age := range []time.Duration{23*time.Hour + 59*time.Minute, 24*time.Hour + time.Minute} {
		row := newJob(studio.StatusReady)
		row.CreatedUnix = now.Add(-age).UnixMilli()

		if err := orm.Create(context.Background(), db, &row); err != nil {
			t.Fatal(err)
		}

		seedRender(t, db, row.UserID, row.CreatedUnix)
	}

	create := func(at time.Time) error {
		row := newJob(studio.StatusQueued)

		return jobs.CreateWithQuota(context.Background(), db, &row, 2, at)
	}

	if err := create(now); err != nil {
		t.Fatalf("one row inside the window, limit 2: %v", err)
	}

	if err := create(now); !errors.Is(err, jobs.ErrQuota) {
		t.Fatalf("two rows inside the window: got %v, want the quota error", err)
	}

	// The in-window row from 23h59m ago ages out a minute later, not at
	// midnight: still limited at +30s, free at +2m.
	if err := create(now.Add(30 * time.Second)); !errors.Is(err, jobs.ErrQuota) {
		t.Fatalf("at +30s got %v, want the quota error", err)
	}

	if err := create(now.Add(2 * time.Minute)); err != nil {
		t.Fatalf("at +2m got %v, want success once the old row aged out", err)
	}
}

func TestClaimRunsAJobOnce(t *testing.T) {
	t.Parallel()

	_, db := limitsApp(t)
	row := newJob(studio.StatusQueued)

	if err := orm.Create(context.Background(), db, &row); err != nil {
		t.Fatal(err)
	}

	var won atomic.Int32

	inParallel(parallel, func(int) {
		if ok, err := jobs.Claim(context.Background(), db, row.ID, time.Now()); err != nil {
			t.Error(err)
		} else if ok {
			won.Add(1)
		}
	})

	got, _ := orm.QueryOf[models.Job](db).Find(context.Background(), row.ID)
	if won.Load() != 1 || got.Attempts != 1 || got.Status != studio.StatusRendering {
		t.Fatalf("claims %d, attempts %d, status %s; want 1, 1, rendering", won.Load(), got.Attempts, got.Status)
	}
}

func TestParallelRequeueQueuesOnce(t *testing.T) {
	t.Parallel()

	_, db := limitsApp(t)
	row := newJob(studio.StatusFailed)

	if err := orm.Create(context.Background(), db, &row); err != nil {
		t.Fatal(err)
	}

	var won atomic.Int32

	inParallel(parallel, func(int) {
		if jobs.Requeue(context.Background(), db, row.ID, time.Now()) == nil {
			won.Add(1)
		}
	})

	if won.Load() != 1 {
		t.Fatalf("%d requeues won, want exactly 1", won.Load())
	}
}

func TestRequeueCannotPassTheAttemptLimit(t *testing.T) {
	t.Parallel()

	_, db := limitsApp(t)
	row := newJob(studio.StatusFailed)
	row.Attempts = jobs.MaxAttempts

	if err := orm.Create(context.Background(), db, &row); err != nil {
		t.Fatal(err)
	}

	var won atomic.Int32

	inParallel(parallel, func(int) {
		if jobs.Requeue(context.Background(), db, row.ID, time.Now()) == nil {
			won.Add(1)
		}
	})

	if won.Load() != 0 {
		t.Fatalf("%d requeues passed the attempt limit", won.Load())
	}

	if err := jobs.Requeue(context.Background(), db, row.ID, time.Now()); !errors.Is(err, jobs.ErrExhausted) {
		t.Fatalf("got %v, want ErrExhausted", err)
	}
}

func seedRender(t *testing.T, db *database.DB, userID, createdUnix int64) {
	t.Helper()

	if _, err := db.ExecContext(context.Background(),
		database.Rebind(db.Dialect(), "INSERT INTO job_renders (user_id, created_unix) VALUES (?, ?)"), userID, createdUnix); err != nil {
		t.Fatal(err)
	}
}

func renderSlots(t *testing.T, db *database.DB) int {
	t.Helper()

	var n int
	if err := db.QueryRowContext(context.Background(), "SELECT COUNT(*) FROM job_renders").Scan(&n); err != nil {
		t.Fatal(err)
	}

	return n
}

func setStatus(t *testing.T, db *database.DB, id int64, status string) {
	t.Helper()

	if _, err := db.ExecContext(context.Background(),
		database.Rebind(db.Dialect(), "UPDATE jobs SET status = ? WHERE id = ?"), status, id); err != nil {
		t.Fatal(err)
	}
}

// A retry calls the model again, so it takes a slot of the rolling quota like
// a new job; a retry that is refused takes none.
func TestRetryTakesAQuotaSlot(t *testing.T) {
	t.Parallel()

	_, db := limitsApp(t)
	ctx := context.Background()
	now := time.Now()

	row := newJob(studio.StatusQueued)
	if err := jobs.CreateWithQuota(ctx, db, &row, 2, now); err != nil {
		t.Fatal(err)
	}

	// Still queued: busy, and no slot is spent.
	if err := jobs.RequeueWithQuota(ctx, db, row.ID, row.UserID, 2, now); !errors.Is(err, jobs.ErrBusy) {
		t.Fatalf("queued job: got %v, want busy", err)
	}

	if n := renderSlots(t, db); n != 1 {
		t.Fatalf("%d slots after a refused retry, want 1", n)
	}

	setStatus(t, db, row.ID, studio.StatusReady)

	if err := jobs.RequeueWithQuota(ctx, db, row.ID, row.UserID, 2, now); err != nil {
		t.Fatalf("second slot: %v", err)
	}

	setStatus(t, db, row.ID, studio.StatusReady)

	if err := jobs.RequeueWithQuota(ctx, db, row.ID, row.UserID, 2, now); !errors.Is(err, jobs.ErrQuota) {
		t.Fatalf("third render in the window: got %v, want the quota error", err)
	}

	cur, err := orm.QueryOf[models.Job](db).Find(ctx, row.ID)
	if err != nil {
		t.Fatal(err)
	}

	if cur.Status != studio.StatusReady {
		t.Fatalf("status %q after a refused retry, want ready", cur.Status)
	}
}

func TestParallelRetriesStayInsideTheQuota(t *testing.T) {
	_, db := limitsApp(t)
	ctx := context.Background()
	now := time.Now()

	var rows [4]models.Job

	for i := range rows {
		rows[i] = newJob(studio.StatusReady)
		rows[i].CreatedUnix = now.UnixMilli()

		if err := orm.Create(ctx, db, &rows[i]); err != nil {
			t.Fatal(err)
		}
	}

	var ok atomic.Int32

	inParallel(len(rows)*3, func(i int) {
		r := rows[i%len(rows)]
		if jobs.RequeueWithQuota(ctx, db, r.ID, r.UserID, 3, now) == nil {
			ok.Add(1)
		}
	})

	if ok.Load() != 3 || renderSlots(t, db) != 3 {
		t.Fatalf("%d retries passed with %d slots, want 3 and 3", ok.Load(), renderSlots(t, db))
	}
}
