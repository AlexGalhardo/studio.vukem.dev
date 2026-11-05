package routes

import (
	"github.com/AlexGalhardo/vukem"
	"github.com/AlexGalhardo/vukem/auth"
	"github.com/AlexGalhardo/vukem/router"

	"github.com/AlexGalhardo/vukem-studio/app/accounts"
	"github.com/AlexGalhardo/vukem-studio/app/controllers"
)

// Jobs registers the brief, the library, and the download.
func Jobs(r *router.Router, app *vukem.App) error {
	acc, err := accounts.New(app)
	if err != nil {
		return err
	}

	h := controllers.NewJobController(app, acc)
	private := []router.Middleware{auth.Required(acc.Web), auth.Verified(acc.Web)}

	r.Get("/jobs", h.Index).Name("jobs.index").Use(private...)
	r.Get("/jobs/create", h.Create).Name("jobs.create").Use(private...)
	r.Post("/jobs", h.Store).Name("jobs.store").Use(private...)
	r.Get("/jobs/{job}", h.Show).Name("jobs.show").Use(private...)
	r.Post("/jobs/{job}/retry", h.Retry).Name("jobs.retry").Use(private...)
	r.Get("/jobs/{job}/download", h.Download).Name("jobs.download").Use(private...)
	r.Get("/jobs/{job}/captions.srt", h.Captions).Name("jobs.captions").Use(private...)
	r.Post("/jobs/{job}/pack", h.Pack).Name("jobs.pack").Use(private...)

	return nil
}
