// Package migrations holds the schema migrations.
package migrations

import "github.com/AlexGalhardo/vukem/schema"

// All lists the migrations in order; vukem make:migration appends here.
func All() []schema.Migration {
	return []schema.Migration{
		m20260101000000CreatePostsTable(),
		m20261105010355CreateUsersTable(),
		m20261105010356CreateAuthTables(),
		m20261105010357CreateSocialAccountsTable(),
	}
}
