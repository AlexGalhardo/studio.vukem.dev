package migrations

import "github.com/AlexGalhardo/vukem/schema"

func m20261107000000CreateVideosTable() schema.Migration {
	return schema.Migration{
		ID: "20261107000000_create_videos_table",
		Up: func(s *schema.Schema) error {
			return s.Create("videos", func(t *schema.Table) {
				t.ID()
				t.ForeignID("user_id").Constrained("users").CascadeOnDelete()
				t.String("status").Default("queued")
				t.String("stage").Default("")
				t.Integer("progress").Default(0)
				t.Integer("attempts").Default(0)
				t.String("title").Default("")
				t.Text("brief")
				t.String("skill_id")
				t.String("model_id")
				t.Text("prompt")
				t.Text("plan").Default("")
				t.Text("raw_response").Default("")
				t.Text("error").Default("")
				t.String("output_path").Default("")
				t.Text("sidecar").Default("")
				t.BigInteger("input_tokens").Default(0)
				t.BigInteger("output_tokens").Default(0)
				t.BigInteger("cost_micros").Default(0)
				t.Timestamps()
				t.Index("user_id", "created_at")
			})
		},
		Down: func(s *schema.Schema) error { return s.DropIfExists("videos") },
	}
}
