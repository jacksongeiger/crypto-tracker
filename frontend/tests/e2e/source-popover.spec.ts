import { test, expect } from "@playwright/test";

// Regression test for the popover dedupe + badge fix. Until that fix, a
// theme with N signals from the same source displayed the source name N
// times and the badge said "+N". After the fix, each source name appears
// at most once and the badge counts UNIQUE sources different from primary.
test("/news/overview popover dedupes corroborating source names", async ({ page }) => {
  await page.goto("/news/overview");
  await expect(page.getByText(/Daily Brief/i).first()).toBeVisible();

  const articles = page.locator("article");
  const articleCount = await articles.count();
  if (articleCount === 0) {
    test.skip(true, "no themes in the current brief");
    return;
  }

  // Find the first theme whose source chip has a "+N" badge — i.e. has at
  // least one corroborator. The dedupe-vs-naive-count regression only
  // shows up when corroborators exist.
  let target: number | null = null;
  for (let i = 0; i < articleCount; i++) {
    const chip = articles.nth(i).getByRole("button", { name: /corroborating source/i });
    if ((await chip.count()) > 0) {
      target = i;
      break;
    }
    // Fallback: any "primary" chip with a "+" badge
    const chipText = await articles.nth(i).locator('button:has-text("primary")').first().textContent().catch(() => null);
    if (chipText && /\+\d/.test(chipText)) {
      target = i;
      break;
    }
  }
  if (target === null) {
    test.skip(true, "no themes with corroborators in the current brief");
    return;
  }

  const article = articles.nth(target);
  const primaryButton = article.locator('button:has-text("primary")').first();
  await primaryButton.click();

  const dialog = page.getByRole("dialog", { name: /corroborating sources/i });
  await expect(dialog).toBeVisible();

  // Each list item is one UNIQUE source name. Pull text, then assert no
  // name appears twice across items (which would mean dedupe failed).
  const items = dialog.getByRole("listitem");
  const itemCount = await items.count();
  expect(itemCount).toBeGreaterThan(0);

  const names: string[] = [];
  for (let i = 0; i < itemCount; i++) {
    const text = (await items.nth(i).innerText()).trim();
    // Strip the "(N signals)" suffix if present
    const name = text.replace(/\s*\(\d+\s*signals?\)\s*$/i, "").trim();
    names.push(name);
  }
  const unique = new Set(names);
  expect(unique.size).toBe(names.length);

  // Badge text uses "source"/"sources", never bare integers. And the
  // number matches the count of unique non-primary names.
  const badgeText = (await primaryButton.innerText()).trim();
  const badgeMatch = badgeText.match(/\+(\d+)\s+sources?/);
  expect(badgeMatch, `badge should read "+N source(s)", got: ${badgeText}`).not.toBeNull();
  const badgeCount = Number(badgeMatch![1]);

  // Primary source name appears as the bold span just before "+N"
  const primaryName = (await primaryButton.locator("span.font-medium").innerText()).trim();
  const independentCount = names.filter((n) => n !== primaryName).length;
  expect(badgeCount).toBe(independentCount);
});
