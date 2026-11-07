package jobs

import (
	"context"

	"github.com/AlexGalhardo/vukem/database"
	"github.com/AlexGalhardo/vukem/orm"

	"github.com/AlexGalhardo/vukem-studio/app/models"
	"github.com/AlexGalhardo/vukem-studio/app/studio"
)

// SaveRun stores what the worker owns. It never writes status-claim columns
// that Claim and Requeue own (attempts) nor the publish pack, so a stale read
// cannot undo another writer.
func SaveRun(ctx context.Context, db *database.DB, st studio.State) error {
	_, err := orm.QueryOf[models.Job](db).Where("id", st.ID).Update(ctx, orm.Set{
		"status":       st.Status,
		"failure":      st.Failure,
		"script":       st.Script,
		"plan_json":    st.PlanJSON,
		"raw_model":    st.RawModel,
		"sidecar_json": st.Sidecar,
		"model_id":     st.ModelID,
		"prompt":       st.Prompt,
	})

	return err
}

// SavePack stores the publish pack columns only.
func SavePack(ctx context.Context, db *database.DB, id int64, platform, title, description, hashtags string) error {
	_, err := orm.QueryOf[models.Job](db).Where("id", id).Update(ctx, orm.Set{
		"pack_platform":    platform,
		"pack_title":       title,
		"pack_description": description,
		"pack_hashtags":    hashtags,
	})

	return err
}
