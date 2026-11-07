package jobs

import (
	"context"
	"errors"
	"fmt"
	"strconv"
	"time"

	"github.com/AlexGalhardo/vukem/database"
	"github.com/AlexGalhardo/vukem/orm"

	"github.com/AlexGalhardo/vukem-studio/app/models"
	"github.com/AlexGalhardo/vukem-studio/app/studio"
)

// MaxAttempts is how many times one job may be rendered, re-runs included.
const MaxAttempts = 5

// DefaultJobsPerDay is the rolling 24-hour limit when STUDIO_MAX_JOBS_PER_DAY
// is unset. Zero means unlimited.
const DefaultJobsPerDay = 20

// Errors the controller maps to a field message.
var (
	ErrQuota     = errors.New("daily job limit reached")
	ErrBusy      = errors.New("this video is already rendering or queued")
	ErrExhausted = errors.New("this video has used all its attempts")
)

// JobsPerDay reads STUDIO_MAX_JOBS_PER_DAY.
func JobsPerDay(get func(string) string) int {
	if v := get("STUDIO_MAX_JOBS_PER_DAY"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n >= 0 {
			return n
		}
	}

	return DefaultJobsPerDay
}

// CreateWithQuota inserts row if the user has fewer than limit jobs in the
// last 24 hours. Both steps share one transaction, behind a per-user lock:
// the lock row is touched first (BEGIN IMMEDIATE on SQLite, a row lock on
// PostgreSQL), so parallel submits queue up and each sees the previous
// insert. The window compares integer epoch milliseconds, because the stored
// text of a timestamp column differs per driver.
func CreateWithQuota(ctx context.Context, db *database.DB, row *models.Job, limit int, now time.Time) error {
	now = now.UTC()
	row.CreatedUnix = now.UnixMilli()

	return db.Tx(ctx, func(tx *database.Tx) error {
		if limit > 0 {
			if err := takeQuota(ctx, tx, row.UserID, limit, now); err != nil {
				return err
			}

			if err := recordRender(ctx, tx, row.UserID, now); err != nil {
				return err
			}
		}

		return orm.Create(ctx, tx, row)
	})
}

func takeQuota(ctx context.Context, tx *database.Tx, userID int64, limit int, now time.Time) error {
	if _, err := tx.ExecContext(ctx, database.Rebind(tx.Dialect(),
		"INSERT INTO job_quotas (user_id, touched_at) VALUES (?, ?) ON CONFLICT (user_id) DO NOTHING"), userID, now.UnixMilli()); err != nil {
		return err
	}

	if _, err := tx.ExecContext(ctx, database.Rebind(tx.Dialect(),
		"UPDATE job_quotas SET touched_at = ? WHERE user_id = ?"), now.UnixMilli(), userID); err != nil {
		return err
	}

	var n int
	if err := tx.QueryRowContext(ctx, database.Rebind(tx.Dialect(),
		"SELECT COUNT(*) FROM job_renders WHERE user_id = ? AND created_unix >= ?"),
		userID, now.Add(-24*time.Hour).UnixMilli()).Scan(&n); err != nil {
		return err
	}

	if n >= limit {
		return fmt.Errorf("%w (%d per 24 hours)", ErrQuota, limit)
	}

	return nil
}

// Claim moves a queued job to rendering and counts the attempt, in one
// conditional UPDATE. Only the worker whose UPDATE changes the row proceeds,
// so a duplicate delivery cannot render (or bill) the job twice.
func Claim(ctx context.Context, db *database.DB, id int64, now time.Time) (bool, error) {
	res, err := db.ExecContext(ctx, database.Rebind(db.Dialect(),
		"UPDATE jobs SET status = ?, failure = '', attempts = attempts + 1, updated_at = ? WHERE id = ? AND status = ?"),
		studio.StatusRendering, now.UTC(), id, studio.StatusQueued)
	if err != nil {
		return false, err
	}

	n, err := res.RowsAffected()

	return n == 1, err
}

// Requeue puts a finished job (ready or failed) back in the queue. One
// conditional UPDATE decides: parallel retries re-queue it at most once, and
// none can pass MaxAttempts. The caller dispatches only when it returns nil.
func Requeue(ctx context.Context, db *database.DB, id int64, now time.Time) error {
	return requeueOn(ctx, db, id, now)
}

func requeueOn(ctx context.Context, ex database.Executor, id int64, now time.Time) error {
	res, err := ex.ExecContext(ctx, database.Rebind(ex.Dialect(),
		"UPDATE jobs SET status = ?, updated_at = ? WHERE id = ? AND status IN (?, ?) AND attempts < ?"),
		studio.StatusQueued, now.UTC(), id, studio.StatusReady, studio.StatusFailed, MaxAttempts)
	if err != nil {
		return err
	}

	if n, err := res.RowsAffected(); err != nil {
		return err
	} else if n == 1 {
		return nil
	}

	cur, err := orm.QueryOf[models.Job](ex).Find(ctx, id)
	if err != nil {
		return err
	}

	if cur.Status == studio.StatusRendering || cur.Status == studio.StatusQueued {
		return ErrBusy
	}

	return ErrExhausted
}

// UniqueKey is the queue uniqueness key of one render attempt.
func UniqueKey(id int64, attempts int) string {
	return "studio.render:" + strconv.FormatInt(id, 10) + ":" + strconv.Itoa(attempts)
}

// RequeueWithQuota is Requeue for a user's own job, and it takes a slot of the
// same rolling 24-hour quota as a new job: a retry calls the model again. The
// slot and the conditional update share one transaction behind the per-user
// lock, so a refused retry (busy, exhausted) consumes nothing. A limit of
// zero is unlimited.
func RequeueWithQuota(ctx context.Context, db *database.DB, id, userID int64, limit int, now time.Time) error {
	now = now.UTC()

	return db.Tx(ctx, func(tx *database.Tx) error {
		if limit > 0 {
			if err := takeQuota(ctx, tx, userID, limit, now); err != nil {
				return err
			}
		}

		if err := requeueOn(ctx, tx, id, now); err != nil {
			return err
		}

		if limit > 0 {
			return recordRender(ctx, tx, userID, now)
		}

		return nil
	})
}

func recordRender(ctx context.Context, tx *database.Tx, userID int64, now time.Time) error {
	_, err := tx.ExecContext(ctx, database.Rebind(tx.Dialect(),
		"INSERT INTO job_renders (user_id, created_unix) VALUES (?, ?)"), userID, now.UnixMilli())

	return err
}
