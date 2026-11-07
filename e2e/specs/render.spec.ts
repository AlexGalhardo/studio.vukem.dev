import { expect, test } from "@playwright/test";

import { fillBrief, signIn } from "./helpers";

test("an encoder that dies fails the job and offers no download", async ({ page, context }) => {
  await signIn(page);
  await page.goto("/jobs/create");
  await fillBrief(page);
  await page.getByRole("button", { name: "Render" }).click();

  await expect(page).toHaveURL(/\/jobs\/\d+$/);
  await expect(page.getByText("failed", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Download MP4" })).toHaveCount(0);

  const res = await context.request.get(`${new URL(page.url()).pathname}/download`, { headers: { Accept: "application/json" } });
  expect(res.status()).toBe(404);
});
