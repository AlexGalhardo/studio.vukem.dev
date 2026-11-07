package controllers

import (
	"errors"
	"github.com/AlexGalhardo/vukem/errs"
	"github.com/AlexGalhardo/vukem/queue"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"strconv"

	"github.com/AlexGalhardo/vukem"
	"github.com/AlexGalhardo/vukem/inertia"
	"github.com/AlexGalhardo/vukem/orm"
	"github.com/AlexGalhardo/vukem/web"
	"github.com/AlexGalhardo/vukem/z"

	"github.com/AlexGalhardo/vukem-studio/app/accounts"
	"github.com/AlexGalhardo/vukem-studio/app/jobs"
	"github.com/AlexGalhardo/vukem-studio/app/models"
	"github.com/AlexGalhardo/vukem-studio/app/requests"
	"github.com/AlexGalhardo/vukem-studio/app/studio"
)

// JobController is the brief, the library, the download, and the publish pack.
type JobController struct {
	app *vukem.App
	acc *accounts.Accounts
}

// NewJobController returns a JobController.
func NewJobController(app *vukem.App, acc *accounts.Accounts) *JobController {
	return &JobController{app: app, acc: acc}
}

// Index lists the signed-in user's jobs.
func (h *JobController) Index(c *web.Ctx) error {
	user, err := h.user(c)
	if err != nil {
		return err
	}

	db, err := h.app.DB()
	if err != nil {
		return err
	}

	rows, err := orm.QueryOf[models.Job](db).Where("user_id", user.ID).OrderBy("id", orm.Desc).Get(c.Context())
	if err != nil {
		return err
	}

	items := make([]map[string]any, 0, len(rows))
	for _, row := range rows {
		items = append(items, map[string]any{
			"id":          row.ID,
			"subject":     row.Subject,
			"status":      row.Status,
			"duration":    row.Duration,
			"style_skill": row.StyleSkill,
			"ratio":       row.Ratio,
		})
	}

	if c.WantsJSON() {
		return c.JSON(http.StatusOK, map[string]any{"data": items})
	}

	return inertia.Render(c, "Jobs/Index", inertia.Props{"jobs": items})
}

// Create shows the brief form.
func (h *JobController) Create(c *web.Ctx) error {
	return inertia.Render(c, "Jobs/Create", inertia.Props{
		"styles": studio.Styles,
		"ratios": []string{"9:16", "1:1", "4:5", "16:9"},
	})
}

// Store validates the brief, stores the compiled prompt, and renders.
func (h *JobController) Store(c *web.Ctx) error {
	user, err := h.user(c)
	if err != nil {
		return err
	}

	in, err := web.Parse(c, requests.BriefSchema)
	if err != nil {
		return err
	}

	db, err := h.app.DB()
	if err != nil {
		return err
	}

	brief := studio.Brief{
		Goal: in.Goal, Audience: in.Audience, Subject: in.Subject, Duration: in.Duration,
		Ratio: in.Ratio, StyleSkill: in.StyleSkill, Language: in.Language,
		Facts: studio.SplitLines(in.Facts), Links: in.Links, CallToAction: in.CallToAction,
		Voice: in.Voice, MusicLicense: in.MusicLicense,
	}

	row := models.Job{
		UserID: user.ID, Status: studio.StatusQueued,
		Goal: brief.Goal, Audience: brief.Audience, Subject: brief.Subject, Duration: brief.Duration,
		Ratio: brief.Ratio, StyleSkill: brief.StyleSkill, Language: brief.Language,
		Facts: in.Facts, Links: brief.Links, CallToAction: brief.CallToAction,
		Voice: brief.Voice, MusicLicense: brief.MusicLicense,
		Prompt:  studio.Compile(brief, studio.LoadSkill(brief.StyleSkill)),
		ModelID: jobs.PlannerFor(h.app).ID(),
	}

	if err := jobs.CreateWithQuota(c.Context(), db, &row, jobs.JobsPerDay(h.app.Source.Get), h.app.Now()); err != nil {
		if errors.Is(err, jobs.ErrQuota) {
			return z.FieldError("goal", err.Error())
		}

		return err
	}

	if in.Voice == studio.VoiceUpload {
		if err := saveVoice(jobs.RootFor(h.app), row.ID, in.VoiceFile); err != nil {
			return err
		}
	}

	q, err := h.app.Queue()
	if err != nil {
		return err
	}

	if err := q.Dispatch(c.Context(), jobs.Render{JobID: row.ID}, queue.Unique(jobs.UniqueKey(row.ID, row.Attempts))); err != nil {
		return err
	}

	saved, err := orm.QueryOf[models.Job](db).Find(c.Context(), row.ID)
	if err != nil {
		return err
	}

	if c.WantsJSON() {
		return c.Created("/jobs/"+strconv.FormatInt(saved.ID, 10), saved)
	}

	switch saved.Status {
	case studio.StatusReady:
		inertia.Flash(c, "success", "The video is ready.")
	case studio.StatusFailed:
		inertia.Flash(c, "success", "The video failed the check.")
	default:
		inertia.Flash(c, "success", "The video is queued.")
	}

	return c.RedirectRoute("jobs.show", "job", saved.ID)
}

// Show reads one job the user owns, including the stored prompt.
func (h *JobController) Show(c *web.Ctx) error {
	row, err := h.find(c)
	if err != nil {
		return err
	}

	if c.WantsJSON() {
		return c.JSON(http.StatusOK, row)
	}

	return inertia.Render(c, "Jobs/Show", inertia.Props{
		"job":       row,
		"download":  row.Status == studio.StatusReady,
		"platforms": studio.Platforms(),
	})
}

// Retry renders the job again. The previous ready file stays until the new one passes.
func (h *JobController) Retry(c *web.Ctx) error {
	row, err := h.find(c)
	if err != nil {
		return err
	}

	db, err := h.app.DB()
	if err != nil {
		return err
	}

	if err := jobs.RequeueWithQuota(c.Context(), db, row.ID, row.UserID, jobs.JobsPerDay(h.app.Source.Get), h.app.Now()); err != nil {
		if errors.Is(err, jobs.ErrBusy) || errors.Is(err, jobs.ErrExhausted) {
			return errs.Wrap(http.StatusConflict, err)
		}

		if errors.Is(err, jobs.ErrQuota) {
			return errs.Wrap(http.StatusTooManyRequests, err)
		}

		return err
	}

	q, err := h.app.Queue()
	if err != nil {
		return err
	}

	if err := q.Dispatch(c.Context(), jobs.Render{JobID: row.ID}, queue.Unique(jobs.UniqueKey(row.ID, row.Attempts))); err != nil {
		return err
	}

	if c.WantsJSON() {
		return c.JSON(http.StatusOK, map[string]any{"id": row.ID})
	}

	return c.RedirectRoute("jobs.show", "job", row.ID)
}

// Download sends the MP4 only when the job is ready.
func (h *JobController) Download(c *web.Ctx) error {
	row, err := h.find(c)
	if err != nil {
		return err
	}

	if row.Status != studio.StatusReady {
		return orm.ErrNotFound
	}

	dir := filepath.Join(jobs.RootFor(h.app), strconv.FormatInt(row.ID, 10))

	return c.Download(os.DirFS(dir), "output.mp4", "studio-"+strconv.FormatInt(row.ID, 10)+".mp4")
}

// Captions sends the cue file for a job the user owns.
func (h *JobController) Captions(c *web.Ctx) error {
	row, err := h.find(c)
	if err != nil {
		return err
	}

	dir := filepath.Join(jobs.RootFor(h.app), strconv.FormatInt(row.ID, 10))

	return c.Download(os.DirFS(dir), "captions.srt", "studio-"+strconv.FormatInt(row.ID, 10)+".srt")
}

// Pack stores a publish pack after the platform limits and the caption file pass.
// It does not post to a network.
func (h *JobController) Pack(c *web.Ctx) error {
	row, err := h.find(c)
	if err != nil {
		return err
	}

	in, err := web.Parse(c, requests.PackSchema)
	if err != nil {
		return err
	}

	if row.Status != studio.StatusReady {
		return z.FieldError("platform", "Render the video before building a publish pack.")
	}

	dir := filepath.Join(jobs.RootFor(h.app), strconv.FormatInt(row.ID, 10))

	srt, err := os.ReadFile(filepath.Join(dir, "captions.srt"))
	if err != nil {
		return z.FieldError("description", "The caption file is missing.")
	}

	if err := studio.SRTError(string(srt), float64(row.Duration)); err != nil {
		return err
	}

	db, err := h.app.DB()
	if err != nil {
		return err
	}

	row.PackPlatform = in.Platform
	row.PackTitle = in.Title
	row.PackDescription = in.Description
	row.PackHashtags = in.Hashtags

	// Only the pack columns: a whole-row write of this earlier read would undo a
	// claim or requeue that happened since.
	if err := jobs.SavePack(c.Context(), db, row.ID, in.Platform, in.Title, in.Description, in.Hashtags); err != nil {
		return err
	}

	if c.WantsJSON() {
		return c.JSON(http.StatusOK, row)
	}

	inertia.Flash(c, "success", "Publish pack saved. Nothing was posted.")

	return c.RedirectRoute("jobs.show", "job", row.ID)
}

func (h *JobController) user(c *web.Ctx) (models.User, error) {
	return h.acc.Web.User(c)
}

func (h *JobController) find(c *web.Ctx) (models.Job, error) {
	user, err := h.user(c)
	if err != nil {
		return models.Job{}, err
	}

	id, err := c.ParamInt("job")
	if err != nil {
		return models.Job{}, err
	}

	db, err := h.app.DB()
	if err != nil {
		return models.Job{}, err
	}

	return orm.QueryOf[models.Job](db).Where("user_id", user.ID).Find(c.Context(), id)
}

func saveVoice(root string, id int64, file *multipart.FileHeader) error {
	dir := filepath.Join(root, strconv.FormatInt(id, 10))
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}

	src, err := file.Open()
	if err != nil {
		return err
	}

	defer src.Close()

	dst, err := os.Create(filepath.Join(dir, "upload.wav"))
	if err != nil {
		return err
	}

	defer dst.Close()

	_, err = io.Copy(dst, src)

	return err
}
