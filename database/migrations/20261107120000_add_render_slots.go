package migrations

import "github.com/AlexGalhardo/vukem/schema"

// job_renders holds one row per render slot (a created job or a retry) for the
// rolling quota. Existing jobs get one slot each so the window does not reset.
func m20261107120000AddRenderSlots() schema.Migration {
	return schema.Migration{
		ID: "20261107120000_add_render_slots",
		Up: func(s *schema.Schema) error {
			if err := s.Create("job_renders", func(t *schema.Table) {
				t.ID()
				t.ForeignID("user_id").Constrained("users").CascadeOnDelete()
				t.BigInteger("created_unix").Default(0)
				t.Index("user_id", "created_unix")
			}); err != nil {
				return err
			}

			return s.Raw("INSERT INTO job_renders (user_id, created_unix) SELECT user_id, created_unix FROM jobs")
		},
		Down: func(s *schema.Schema) error { return s.DropIfExists("job_renders") },
	}
}
