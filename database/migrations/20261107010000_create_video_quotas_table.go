package migrations

import "github.com/AlexGalhardo/vukem/schema"

// video_quotas holds one counter row per user and UTC day, incremented with
// a conditional UPDATE so parallel submits cannot pass the daily limit.
func m20261107010000CreateVideoQuotasTable() schema.Migration {
	return schema.Migration{
		ID: "20261107010000_create_video_quotas_table",
		Up: func(s *schema.Schema) error {
			return s.Create("video_quotas", func(t *schema.Table) {
				t.ID()
				t.ForeignID("user_id").Constrained("users").CascadeOnDelete()
				t.String("day")
				t.Integer("used").Default(0)
				t.UniqueIndex("user_id", "day")
			})
		},
		Down: func(s *schema.Schema) error { return s.DropIfExists("video_quotas") },
	}
}
