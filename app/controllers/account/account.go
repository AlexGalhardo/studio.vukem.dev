// Package account holds the login page, logout and dashboard handlers,
// rendered with Inertia pages in resources/js/pages. Google is the only
// sign-in (routes/social.go).
package account

import (
	"github.com/AlexGalhardo/vukem/inertia"
	"github.com/AlexGalhardo/vukem/web"

	"github.com/AlexGalhardo/vukem-studio/app/accounts"
)

// Handlers serves the account pages.
type Handlers struct {
	a *accounts.Accounts
}

// New returns the handlers.
func New(a *accounts.Accounts) *Handlers { return &Handlers{a: a} }

// ShowLogin renders the login page.
func (*Handlers) ShowLogin(c *web.Ctx) error { return inertia.Render(c, "Auth/Login", nil) }

// Logout signs the user out and rotates the history encryption key.
func (h *Handlers) Logout(c *web.Ctx) error {
	if err := h.a.Web.Logout(c); err != nil {
		return err
	}

	inertia.ClearHistory(c)

	return c.Redirect("/login")
}

// Dashboard is the first page after login; the user arrives as the shared
// auth.user prop.
func (*Handlers) Dashboard(c *web.Ctx) error { return inertia.Render(c, "Dashboard", nil) }
