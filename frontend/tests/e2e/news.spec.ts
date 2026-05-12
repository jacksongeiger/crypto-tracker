import { test, expect } from "@playwright/test";

test("/news/overview renders themes from all categories", async ({ page }) => {
  await page.goto("/news/overview");
  await expect(page.getByText(/Daily Brief/i).first()).toBeVisible();
  await expect(page.getByText(/TL;DR/i)).toBeVisible();
  // Themes section header
  await expect(page.getByText(/^Themes \(/i).first()).toBeVisible();
});

test("/news/policy filters to policy-tagged themes only", async ({ page }) => {
  await page.goto("/news/policy", { waitUntil: "networkidle" });
  await expect(page.getByText(/News · Policy/i).first()).toBeVisible();
  // The CLARITY Act theme is tagged policy in our seeded data
  await expect(page.getByText(/CLARITY Act/i).first()).toBeVisible({
    timeout: 10_000,
  });
});

test("/news/markets and /news/policy show different themes", async ({ page }) => {
  await page.goto("/news/markets");
  const marketsText = await page.locator("article").allInnerTexts();
  await page.goto("/news/policy");
  const policyText = await page.locator("article").allInnerTexts();
  // At least one differing title indicates the filter is doing real work
  expect(marketsText.join("\n")).not.toEqual(policyText.join("\n"));
});

test("invalid category 404s", async ({ page }) => {
  // With streaming + loading.tsx the initial HTTP response is 200; the 404
  // resolves later in the stream. Assert by rendered content.
  await page.goto("/news/not-a-real-category", { waitUntil: "networkidle" });
  await expect(page.getByText(/This page could not be found/i)).toBeVisible({
    timeout: 10_000,
  });
});

test("category page primary-article links have hrefs", async ({ page }) => {
  await page.goto("/news/overview");
  const links = page.getByRole("link", { name: /read primary article/i });
  const count = await links.count();
  expect(count).toBeGreaterThan(0);
  for (let i = 0; i < count; i++) {
    const href = await links.nth(i).getAttribute("href");
    expect(href).toMatch(/^https?:\/\//);
  }
});
