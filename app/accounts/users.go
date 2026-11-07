package accounts

import (
	"context"
	"strconv"

	"github.com/AlexGalhardo/vukem/auth"
	"github.com/AlexGalhardo/vukem/database"
	"github.com/AlexGalhardo/vukem/orm"

	"github.com/AlexGalhardo/vukem-studio/app/models"
)

// revokeAccess deletes userID's remember-me tokens, revokes its API tokens
// and bumps its session version, using ex (a.DB or the transaction in
// progress).
func (a *Accounts) revokeAccess(ctx context.Context, ex database.Executor, userID int64) error {
	id := strconv.FormatInt(userID, 10)

	del := "DELETE FROM remember_tokens WHERE user_id = " + ex.Dialect().Placeholder(1)
	if _, err := ex.ExecContext(ctx, del, id); err != nil {
		return err
	}

	// Revoked, not deleted: the tokens stay listed with revoked_at.
	tokens := auth.NewTokens(ex)
	tokens.Now = a.Tokens.Now
	tokens.Log = a.Tokens.Log

	if err := tokens.RevokeAll(ctx, id); err != nil {
		return err
	}

	return a.bumpSessionVersion(ctx, ex, userID)
}

// MarkVerified sets email_verified_at using ex (a.DB, or the transaction
// in progress: SQLite has a single writer connection).
func (a *Accounts) MarkVerified(ctx context.Context, ex database.Executor, u *models.User) error {
	if u.EmailVerified() {
		return nil
	}

	u.EmailVerifiedAt = orm.NullTime{}
	u.EmailVerifiedAt.V, u.EmailVerifiedAt.Valid = a.now().UTC(), true

	set := orm.Set{"email_verified_at": u.EmailVerifiedAt.V}

	_, err := orm.QueryOf[models.User](ex).Where("id", u.ID).Update(ctx, set)

	return err
}
