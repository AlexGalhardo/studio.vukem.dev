package migrations

import "github.com/AlexGalhardo/vukem/schema"

// video_quotas holds one lock row per user. Creating a job touches the row
// first, which takes the write lock (BEGIN IMMEDIATE on SQLite, a row lock on
// PostgreSQL), so counting the last 24 hours and inserting the job is atomic.
func m20261107010000CreateVideoQuotasTable() schema.Migration {
	return schema.Migration{
		ID: "20261107010000_create_video_quotas_table",
		Up: func(s *schema.Schema) error {
			return s.Create("video_quotas", func(t *schema.Table) {
				t.ID()
				t.ForeignID("user_id").Constrained("users").CascadeOnDelete()
				t.Timestamp("touched_at")
				t.UniqueIndex("user_id")
			})
		},
		Down: func(s *schema.Schema) error { return s.DropIfExists("video_quotas") },
	}
}
