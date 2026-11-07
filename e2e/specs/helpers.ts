import { expect, type Page } from "@playwright/test";

export async function signIn(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByRole("link", { name: "Continue with Google" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

export async function fillBrief(page: Page, over: Record<string, string> = {}): Promise<void> {
  const values: Record<string, string> = {
    Goal: "Visit the harbor",
    Audience: "neighbors",
    "Offer or subject": "Saturday market",
    "Duration (seconds)": "6",
    ...over,
  };

  for (const [label, value] of Object.entries(values)) await page.getByLabel(label).fill(value);
}
