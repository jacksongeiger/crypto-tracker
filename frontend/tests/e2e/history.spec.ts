import { test, expect } from "@playwright/test";

test("/news/history renders list with at least one brief", async ({ page }) => {
  await page.goto("/news/history", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: /Brief History/i })).toBeVisible();
  // Either we have brief cards, or we hit the empty state. With a populated
  // DB (verified prior to this test running) we expect cards.
  const cards = page.locator("a[href^='/news/history/']");
  await expect(cards.first()).toBeVisible({ timeout: 10_000 });
});

test("clicking a history card navigates to the brief detail page", async ({ page }) => {
  await page.goto("/news/history", { waitUntil: "networkidle" });
  const firstCard = page.locator("a[href^='/news/history/']").first();
  const href = await firstCard.getAttribute("href");
  expect(href).toMatch(/^\/news\/history\/[0-9a-f-]{36}$/);
  await firstCard.click();
  await expect(page).toHaveURL(/\/news\/history\/[0-9a-f-]{36}$/);
  await expect(page.getByText(/Historical · viewing brief from/i)).toBeVisible();
  // The brief page should include the Summary section the home page uses
  await expect(page.getByText(/TL;DR/i)).toBeVisible();
});

test("history link in nav dropdown leads to /news/history", async ({ page }) => {
  await page.goto("/news/overview");
  await page.getByRole("button", { name: /^news$/i }).click();
  await page.getByRole("menuitem", { name: /^history$/i }).click();
  await expect(page).toHaveURL(/\/news\/history(?:\?.*)?$/);
  await expect(page.getByRole("heading", { name: /Brief History/i })).toBeVisible();
});

test("nonexistent brief id 404s", async ({ page }) => {
  await page.goto("/news/history/00000000-0000-0000-0000-000000000000", {
    waitUntil: "networkidle",
  });
  await expect(page.getByText(/This page could not be found/i)).toBeVisible({
    timeout: 10_000,
  });
});
