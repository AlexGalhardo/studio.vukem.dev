// Package jobs holds the queued jobs.
package jobs

import (
	"time"

	vukem "github.com/AlexGalhardo/vukem"
	"github.com/AlexGalhardo/vukem/queue"
)

// All lists the job handlers, built from the app so they reach its
// database, clock and mailer; vukem make:job appends here and names the
// parameter "app" with the first handler that needs it.
func All(app *vukem.App) []queue.Registration {
	return []queue.Registration{
		// One attempt. A failed encode is stored on the row; the operator
		// re-runs it. A queue retry would race the same output path.
		queue.Handle(handleRender(app), queue.Retries(0), queue.Timeout(2*time.Minute)),
	}
}
