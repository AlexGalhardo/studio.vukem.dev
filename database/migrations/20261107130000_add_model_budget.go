package migrations

import "github.com/AlexGalhardo/vukem/schema"

// model_budget is the lock row and model_spend the reserved worst-case cost of
// each model call, for the global rolling daily budget.
func m20261107130000AddModelBudget() schema.Migration {
	return schema.Migration{
		ID: "20261107130000_add_model_budget",
		Up: func(s *schema.Schema) error {
			if err := s.Create("model_budget", func(t *schema.Table) {
				t.ID()
				t.BigInteger("touched_at").Default(0)
			}); err != nil {
				return err
			}

			return s.Create("model_spend", func(t *schema.Table) {
				t.ID()
				t.BigInteger("micros").Default(0)
				t.BigInteger("created_unix").Default(0)
				t.Index("created_unix")
			})
		},
		Down: func(s *schema.Schema) error {
			if err := s.DropIfExists("model_spend"); err != nil {
				return err
			}

			return s.DropIfExists("model_budget")
		},
	}
}
