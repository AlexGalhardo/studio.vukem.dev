package migrations

import "github.com/AlexGalhardo/vukem/schema"

func m20261105010355CreateUsersTable() schema.Migration {
	return schema.Migration{
		ID: "20261105010355_create_users_table",
		Up: func(s *schema.Schema) error {
			return s.Create("users", func(t *schema.Table) {
				t.ID()
				t.String("name")
				t.String("email").Unique()
				t.String("password")
				t.Timestamp("email_verified_at").Nullable()
				// Bumped to end every session of the user (Accounts.RevokeOtherSessions).
				t.BigInteger("session_version").Default(0)
				t.Timestamps()
			})
		},
		Down: func(s *schema.Schema) error { return s.DropIfExists("users") },
	}
}
