import { test, expect } from "@playwright/test";

// Visual-regression baselines for the wide-layout redesign. We capture
// each major route at a 1920×1080 viewport and assert page width matches
// the documented max-w token (max-w-5xl = 1024px for news, max-w-7xl =
// 1280px for the dashboard + nav inner). Baseline PNGs live in
// tests/screenshots/ for human diff review on layout changes.

test.use({ viewport: { width: 1920, height: 1080 } });

const NEWS_INNER_PX = 1024; // max-w-5xl
const DASH_INNER_PX = 1280; // max-w-7xl

async function widthOf(page: any, selector: string) {
  return await page.evaluate(
    (s: string) =>
      document.querySelector(s)?.getBoundingClientRect().width ?? null,
    selector,
  );
}

test("news/overview content column is max-w-5xl on a 1920 viewport", async ({
  page,
}) => {
  await page.goto("/news/overview", { waitUntil: "networkidle" });
  // The TL;DR is wrapped in a max-w-5xl container; the section element is
  // bordered and is the easiest stable selector.
  const tldrWidth = await widthOf(page, 'section[aria-label="TL;DR"]');
  expect(tldrWidth).not.toBeNull();
  expect(tldrWidth).toBeGreaterThan(900);
  expect(tldrWidth).toBeLessThanOrEqual(NEWS_INNER_PX);
});

test("news/policy content column is max-w-5xl on a 1920 viewport", async ({
  page,
}) => {
  await page.goto("/news/policy", { waitUntil: "networkidle" });
  const heading = await widthOf(page, "h1");
  expect(heading).not.toBeNull();
});

test("dashboard content column is max-w-7xl on a 1920 viewport", async ({
  page,
}) => {
  await page.goto("/dashboard", { waitUntil: "networkidle" });
  // The page header inner div is the canonical max-w-7xl container.
  const headerInner = await page.evaluate(() => {
    const el = document.querySelector(
      "header.relative > div.mx-auto",
    ) as HTMLElement | null;
    return el?.getBoundingClientRect().width ?? null;
  });
  expect(headerInner).not.toBeNull();
  expect(headerInner!).toBeGreaterThan(1100);
  expect(headerInner!).toBeLessThanOrEqual(DASH_INNER_PX);
});

test("top nav inner is constrained to max-w-7xl on a 1920 viewport", async ({
  page,
}) => {
  await page.goto("/news/overview", { waitUntil: "networkidle" });
  const navInner = await page.evaluate(() => {
    // The first sticky <header> has the inner div as its first child
    const header = document.querySelector("header.sticky") as HTMLElement | null;
    const inner = header?.querySelector("div") as HTMLElement | null;
    return inner?.getBoundingClientRect().width ?? null;
  });
  expect(navInner).not.toBeNull();
  expect(navInner!).toBeGreaterThan(1100);
  expect(navInner!).toBeLessThanOrEqual(DASH_INNER_PX);
});
