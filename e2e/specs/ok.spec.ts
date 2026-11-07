import { expect, test } from "@playwright/test";

import { fillBrief, signIn } from "./helpers";

const privatePages = ["/", "/dashboard", "/jobs", "/jobs/create", "/jobs/1", "/jobs/1/download", "/jobs/1/captions.srt"];

test.describe("signed out", () => {
  for (const path of privatePages) {
    test(`${path} redirects to /login`, async ({ page }) => {
      await page.goto(path);
      await expect(page).toHaveURL(/\/login$/);
    });
  }

  test("login page has one sign-in control", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("link", { name: "Continue with Google" })).toHaveCount(1);
    await expect(page.locator("input[type=password]")).toHaveCount(0);
  });

  test("API answers 401 JSON, not a redirect", async ({ request }) => {
    for (const path of ["/jobs", "/jobs/1"]) {
      const res = await request.get(path, { headers: { Accept: "application/json" }, maxRedirects: 0 });
      expect(res.status(), path).toBe(401);
    }

    const post = await request.post("/jobs", { headers: { Accept: "application/json" }, data: {}, maxRedirects: 0 });
    expect(post.status()).toBe(401);
  });

  test("health check answers 200", async ({ request }) => {
    expect((await request.get("/up")).status()).toBe(200);
  });
});

test.describe("signed in", () => {
  test("sidebar links and logout", async ({ page }) => {
    await signIn(page);
    await expect(page.getByRole("navigation", { name: "Dashboard" })).toBeVisible();

    await page.getByRole("navigation", { name: "Dashboard" }).getByRole("link").nth(1).click();
    await expect(page).toHaveURL(/\/jobs/);

    await page.getByRole("button", { name: "Log out" }).click();
    await expect(page).toHaveURL(/\/login$/);
    await page.goto("/jobs");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("an empty brief shows field errors and creates nothing", async ({ page }) => {
    await signIn(page);
    await page.goto("/jobs/create");
    await page.getByRole("button", { name: "Render" }).click();

    await expect(page.locator("p.text-red-600").first()).toBeVisible();
    await expect(page).toHaveURL(/\/jobs\/create$/);
  });

  test("brief to ready job to a playable download", async ({ page, context }) => {
    await signIn(page);
    await page.goto("/jobs/create");
    await fillBrief(page);
    await page.getByRole("button", { name: "Render" }).click();

    await expect(page).toHaveURL(/\/jobs\/\d+$/);
    await expect(page.getByText("ready", { exact: true })).toBeVisible({ timeout: 60_000 });

    const href = await page.getByRole("link", { name: "Download MP4" }).getAttribute("href");
    const res = await context.request.get(href as string);
    expect(res.status()).toBe(200);
    expect(res.headers()["content-type"]).toContain("video/mp4");
    expect((await res.body()).length).toBeGreaterThan(1000);

    await page.goto("/jobs");
    await expect(page.getByRole("link", { name: "Saturday market" }).first()).toBeVisible();
  });

  test("API validation: unknown skill, bad ratio, oversized and missing input", async ({ page, context }) => {
    await signIn(page);

    const brief = {
      goal: "A goal", audience: "neighbors", subject: "market", duration: 6, ratio: "9:16",
      style_skill: "traco-simples", language: "en", facts: "", voice: "none",
    };
    const post = (data: object) => context.request.post("/jobs", { headers: { Accept: "application/json" }, data: { ...brief, ...data } });

    expect((await post({ style_skill: "no-such-skill" })).status()).toBe(422);
    expect((await post({ ratio: "2:1" })).status()).toBe(422);
    expect((await post({ duration: 99999 })).status()).toBe(422);
    expect((await post({ goal: "" })).status()).toBe(422);
    expect((await post({ goal: "x".repeat(100_000) })).status()).toBe(422);
  });

  test("a job that does not exist is a 404", async ({ page, context }) => {
    await signIn(page);

    for (const path of ["/jobs/99999", "/jobs/99999/download"]) {
      expect((await context.request.get(path, { headers: { Accept: "application/json" } })).status(), path).toBe(404);
    }
  });
});
