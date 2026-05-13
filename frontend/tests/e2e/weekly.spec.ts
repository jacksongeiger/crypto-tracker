import { test, expect } from "@playwright/test";

test("/news/weekly renders the roundup or the below-minimum empty state", async ({ page }) => {
  await page.goto("/news/weekly", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: /This Week/i })).toBeVisible();
  await expect(page.getByLabel(/This Week TL;DR/i)).toBeVisible();
  const summary = await page.getByLabel(/This Week TL;DR/i).innerText();
  // Either the brand opener (roundup live) or the truthful below-min copy.
  const okOpener =
    /This week's crypto coverage/i.test(summary) ||
    /needs at least \d+ briefs/i.test(summary);
  expect(okOpener).toBe(true);
});

test("Weekly entry is reachable from the News dropdown", async ({ page }) => {
  await page.goto("/news/overview");
  await page.getByRole("button", { name: /^news$/i }).click();
  await page.getByRole("menuitem", { name: /^weekly$/i }).click();
  await expect(page).toHaveURL(/\/news\/weekly$/);
  await expect(page.getByRole("heading", { name: /This Week/i })).toBeVisible();
});

test("Weekly highlights link back to their source brief", async ({ page }) => {
  await page.goto("/news/weekly", { waitUntil: "networkidle" });
  // If we have any highlights, each should expose a "View full brief" link
  // pointing at /news/history/<uuid>.
  const links = page.locator("a", { hasText: /View full brief from/i });
  const count = await links.count();
  if (count === 0) {
    // Below-minimum or empty state — acceptable.
    return;
  }
  for (let i = 0; i < count; i++) {
    const href = await links.nth(i).getAttribute("href");
    expect(href).toMatch(/^\/news\/history\/[0-9a-f-]{36}$/);
  }
});
