package migrations

import "github.com/AlexGalhardo/vukem/schema"

func m20261105120000CreateJobsTable() schema.Migration {
	return schema.Migration{
		ID: "20261105120000_create_jobs_table",
		Up: func(s *schema.Schema) error {
			return s.Create("jobs", func(t *schema.Table) {
				t.ID()
				t.ForeignID("user_id").Constrained("users").CascadeOnDelete().Index()
				t.String("status")
				t.Text("goal")
				t.Text("audience")
				t.Text("subject")
				t.Integer("duration")
				t.String("ratio")
				t.String("style_skill")
				t.String("language")
				t.Text("facts")
				t.Text("links")
				t.Text("call_to_action")
				t.String("voice")
				t.Text("music_license")
				t.Text("prompt")
				t.String("model_id")
				t.Text("plan_json")
				t.Text("raw_model")
				t.Text("script")
				t.Text("failure")
				t.Text("sidecar_json")
				t.String("pack_platform")
				t.Text("pack_title")
				t.Text("pack_description")
				t.Text("pack_hashtags")
				t.Timestamps()
			})
		},
		Down: func(s *schema.Schema) error { return s.DropIfExists("jobs") },
	}
}
