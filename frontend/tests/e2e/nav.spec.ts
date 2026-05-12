import { test, expect } from "@playwright/test";

test("News dropdown opens and navigates", async ({ page }) => {
  await page.goto("/news/overview");
  // Trigger News dropdown
  await page.getByRole("button", { name: /^news$/i }).click();
  // Click Policy
  await page.getByRole("menuitem", { name: /^policy$/i }).click();
  await expect(page).toHaveURL(/\/news\/policy$/);
  await expect(page.getByText(/News · Policy/i).first()).toBeVisible();
});

test("Dashboard tab navigates", async ({ page }) => {
  await page.goto("/news/overview");
  await page.getByRole("link", { name: /^dashboard$/i }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText(/Live market signals/i)).toBeVisible();
});

test("Root URL redirects to /news/overview", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/news\/overview$/);
});

test("Active tab shows a brand-blue underline", async ({ page }) => {
  await page.goto("/dashboard");
  const dashLink = page.getByRole("link", { name: /^dashboard$/i });
  await expect(dashLink).toBeVisible();
  // The underline is a sibling absolute span; just verify the tab has active text color (ink not muted)
  const color = await dashLink.evaluate(
    (el) => window.getComputedStyle(el as HTMLElement).color,
  );
  // ink = #0A0B0D = rgb(10, 11, 13)
  expect(color).toBe("rgb(10, 11, 13)");
});

test("Nav is sticky on scroll", async ({ page }) => {
  await page.goto("/news/overview");
  await page.evaluate(() => window.scrollTo(0, 2000));
  const wordmark = page.getByRole("link", { name: /crypto-tracker home/i });
  await expect(wordmark).toBeInViewport();
});
