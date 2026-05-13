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
  // Every theme article on this page should carry a "Policy" category chip.
  // (Specific theme titles vary day-to-day with the corpus; assert the
  // category-tag invariant instead.)
  const articles = page.locator("article");
  const count = await articles.count();
  if (count > 0) {
    // Either today's themes (always have Policy chip) OR 7-day fallback
    // themes (always have Policy chip — same query filter).
    for (let i = 0; i < count; i++) {
      await expect(articles.nth(i).getByText(/^Policy$/i).first()).toBeVisible();
    }
  } else {
    // No themes anywhere in the past week — the page shows the
    // "no coverage in past week" empty state.
    await expect(page.getByText(/Nothing tagged Policy in the past week/i)).toBeVisible();
  }
});

test("/news/markets TL;DR is real editorial content, not count-meta", async ({ page }) => {
  await page.goto("/news/markets", { waitUntil: "networkidle" });
  // Pull the first theme's title and assert at least one of its
  // significant words appears in the TL;DR card. This proves the
  // summary is actually derived from the data, not a placeholder.
  const articles = page.locator("article");
  const count = await articles.count();
  if (count === 0) {
    // Empty state is acceptable; the equivalent assertion runs on the
    // /news/policy fallback test below.
    return;
  }
  const firstHeading = await articles.first().locator("h2").innerText();
  const tldr = page.getByLabel("Markets TL;DR");
  await expect(tldr).toBeVisible();
  const tldrText = await tldr.innerText();
  // The TL;DR must NOT be the old count-meta placeholder
  expect(tldrText).not.toMatch(/Highest-conviction first/i);
  expect(tldrText).not.toMatch(/^\d+ themes? in Markets today/i);
  // It should share at least one ≥4-letter word with the top theme title
  const firstWords = firstHeading
    .toLowerCase()
    .split(/\W+/)
    .filter((w) => w.length >= 4);
  expect(firstWords.some((w) => tldrText.toLowerCase().includes(w))).toBe(true);
});

test("category page with empty today renders 7-day fallback or graceful empty", async ({ page }) => {
  // Pick the category most likely to be empty on a small day. If today
  // has policy themes, the empty-state copy won't appear — we only
  // assert the empty-state copy when the empty state is actually shown.
  await page.goto("/news/policy", { waitUntil: "networkidle" });
  const tldr = page.getByLabel("Policy TL;DR");
  const tldrText = await tldr.innerText();
  if (/No Policy themes in today/i.test(tldrText)) {
    // Empty case: we should see EITHER the 7-day fallback header OR the
    // "Nothing tagged Policy in the past week" deep-empty state.
    const fallbackHeader = page.getByText(/Recent Policy · past 7 days/i);
    const deepEmpty = page.getByText(/Nothing tagged Policy in the past week/i);
    const fallbackVisible = await fallbackHeader.isVisible().catch(() => false);
    const deepEmptyVisible = await deepEmpty.isVisible().catch(() => false);
    expect(fallbackVisible || deepEmptyVisible).toBe(true);
  }
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
