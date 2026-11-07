package accounts

import (
	"context"

	"github.com/AlexGalhardo/vukem/database"
	"github.com/AlexGalhardo/vukem/orm"

	"github.com/AlexGalhardo/vukem-studio/app/models"
)

// updatePassword stores a new hash for the user inside tx. Social sign-in uses
// it to replace the password of an unverified account whose address Google
// proves, so nobody who registered it first keeps access.
func (a *Accounts) updatePassword(ctx context.Context, tx database.Executor, id int64, password string) error {
	h, err := a.Hasher.Make(password)
	if err != nil {
		return err
	}

	_, err = orm.QueryOf[models.User](tx).Where("id", id).Update(ctx, orm.Set{"password": h})

	return err
}
