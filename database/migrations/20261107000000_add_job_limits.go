package migrations

import "github.com/AlexGalhardo/vukem/schema"

// Adds the attempt counter and the integer creation time to jobs, and one
// lock row per user for the rolling job quota.
func m20261107000000AddJobLimits() schema.Migration {
	return schema.Migration{
		ID: "20261107000000_add_job_limits",
		Up: func(s *schema.Schema) error {
			if err := s.Table("jobs", func(t *schema.Table) {
				t.Integer("attempts").Default(0)
				t.BigInteger("created_unix").Default(0)
			}); err != nil {
				return err
			}

			return s.Create("job_quotas", func(t *schema.Table) {
				t.ID()
				t.ForeignID("user_id").Constrained("users").CascadeOnDelete()
				t.BigInteger("touched_at").Default(0)
				t.UniqueIndex("user_id")
			})
		},
		Down: func(s *schema.Schema) error {
			if err := s.DropIfExists("job_quotas"); err != nil {
				return err
			}

			return s.Table("jobs", func(t *schema.Table) { t.DropColumn("attempts", "created_unix") })
		},
	}
}
