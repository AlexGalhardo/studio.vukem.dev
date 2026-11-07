package jobs

import (
	"context"
	"strconv"
	"time"

	"github.com/AlexGalhardo/vukem/database"

	"github.com/AlexGalhardo/vukem-studio/app/studio"
)

// DefaultDailyBudgetCents is the rolling 24-hour model budget when
// STUDIO_DAILY_BUDGET_CENTS is unset. Zero disables the budget.
const DefaultDailyBudgetCents = 500

// DailyBudgetCents reads STUDIO_DAILY_BUDGET_CENTS.
func DailyBudgetCents(get func(string) string) int {
	if v := get("STUDIO_DAILY_BUDGET_CENTS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n >= 0 {
			return n
		}
	}

	return DefaultDailyBudgetCents
}

// ReserveModelSpend adds micros (USD millionths, the worst case of one model
// call) to the rolling 24 hours if the total stays within limitMicros. The
// check and the insert share one transaction behind a lock row (BEGIN
// IMMEDIATE on SQLite, a row lock on PostgreSQL), so parallel calls cannot
// all pass on the same remaining budget. A call that fails afterwards keeps
// its reservation: the budget is a guard, not an invoice. Zero disables it.
func ReserveModelSpend(ctx context.Context, db *database.DB, micros, limitMicros int64, now time.Time) error {
	if limitMicros <= 0 {
		return nil
	}

	now = now.UTC()

	return db.Tx(ctx, func(tx *database.Tx) error {
		if _, err := tx.ExecContext(ctx, database.Rebind(tx.Dialect(),
			"INSERT INTO model_budget (id, touched_at) VALUES (1, ?) ON CONFLICT (id) DO NOTHING"), now.UnixMilli()); err != nil {
			return err
		}

		if _, err := tx.ExecContext(ctx, database.Rebind(tx.Dialect(),
			"UPDATE model_budget SET touched_at = ? WHERE id = 1"), now.UnixMilli()); err != nil {
			return err
		}

		var spent int64
		if err := tx.QueryRowContext(ctx, database.Rebind(tx.Dialect(),
			"SELECT COALESCE(SUM(micros), 0) FROM model_spend WHERE created_unix >= ?"),
			now.Add(-24*time.Hour).UnixMilli()).Scan(&spent); err != nil {
			return err
		}

		if spent+micros > limitMicros {
			return studio.ErrOverBudget
		}

		_, err := tx.ExecContext(ctx, database.Rebind(tx.Dialect(),
			"INSERT INTO model_spend (micros, created_unix) VALUES (?, ?)"), micros, now.UnixMilli())

		return err
	})
}
