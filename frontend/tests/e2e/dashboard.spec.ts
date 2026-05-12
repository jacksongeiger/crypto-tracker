import { test, expect } from "@playwright/test";

test.describe("dashboard", () => {
  test("renders header + sections within reasonable time", async ({ page }) => {
    await page.goto("/dashboard", { waitUntil: "networkidle", timeout: 60_000 });
    await expect(page.getByText(/Live market signals/i)).toBeVisible();
    await expect(page.getByText(/^Live prices$/i)).toBeVisible({
      timeout: 15_000,
    });
  });

  test("price strip shows at least one $-prefixed number", async ({ page }) => {
    await page.goto("/dashboard", { waitUntil: "networkidle", timeout: 60_000 });
    // First $-formatted USD number in the strip
    await expect(page.locator("text=/\\$[0-9,]/").first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test("fear & greed card shows a classification label", async ({ page }) => {
    await page.goto("/dashboard", { waitUntil: "networkidle", timeout: 60_000 });
    await expect(page.getByText(/Fear & Greed Index/i)).toBeVisible({
      timeout: 15_000,
    });
    // any of the five classifications
    await expect(
      page.locator(
        "text=/Extreme Fear|Fear|Neutral|Greed|Extreme Greed/",
      ).first(),
    ).toBeVisible({ timeout: 15_000 });
  });

  // NOTE: server-side fetches can't be intercepted by page.route because the
  // request originates from the Next.js server, not the browser. Error-card
  // rendering for individual data sources is covered by the per-source unit
  // tests (data-sources.test.ts) which mock global.fetch directly.
});
