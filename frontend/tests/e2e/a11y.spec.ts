import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const PATHS = ["/news/overview", "/news/policy", "/dashboard"];

for (const path of PATHS) {
  test(`a11y: ${path} has no critical or serious axe violations`, async ({
    page,
  }) => {
    await page.goto(path, { waitUntil: "networkidle", timeout: 60_000 });
    const { violations } = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const blockers = violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    if (blockers.length) {
      const summary = blockers
        .map((v) => {
          const targets = v.nodes
            .slice(0, 3)
            .map((n) => `    target: ${n.target.join(" ")}\n    summary: ${n.failureSummary?.replace(/\n/g, " ")}`)
            .join("\n");
          return `${v.id} (${v.impact}): ${v.help}\n${targets}`;
        })
        .join("\n\n");
      throw new Error(`a11y violations on ${path}:\n${summary}`);
    }
    expect(blockers.length).toBe(0);
  });
}

test("keyboard nav: News dropdown opens via keyboard", async ({ page }) => {
  await page.goto("/news/overview");
  // Focus the wordmark, then tab to News
  await page.getByRole("link", { name: /crypto-tracker home/i }).focus();
  await page.keyboard.press("Tab");
  const newsBtn = page.getByRole("button", { name: /^news$/i });
  await expect(newsBtn).toBeFocused();
  await page.keyboard.press("Enter");
  // dropdown should open and show menu items
  await expect(
    page.getByRole("menuitem", { name: /^policy$/i }),
  ).toBeVisible();
});
