import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.route("**/api/**", async (route) => {
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Optional test source unavailable." }),
    });
  });
});

test("Settings overlays and restores the current workspace without changing its URL", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/labs");
  await expect(page.getByRole("link", { name: /Logo lab/ })).toBeVisible();
  const originalUrl = page.url();

  await page.locator(".activity-bar").getByRole("button", { name: "Settings" }).click();

  const dialog = page.getByRole("dialog", { name: "Settings" });
  await expect(dialog).toBeVisible();
  await expect(page).toHaveURL(originalUrl);
  await expect(page.locator(".labs-route")).toBeVisible();
  await expect(page.locator(".shell")).toHaveAttribute("inert", "");
  await expect(dialog.getByRole("link", { name: /General/ })).toHaveAttribute(
    "aria-current",
    "page",
  );

  await dialog.getByRole("link", { name: /Models/ }).click();
  await expect(page).toHaveURL(originalUrl);
  await expect(dialog.getByRole("link", { name: /Models/ })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(page.locator(".labs-route")).toBeVisible();

  await dialog.getByRole("button", { name: "Close settings" }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page).toHaveURL(originalUrl);
  await expect(page.getByRole("link", { name: /Logo lab/ })).toBeVisible();
});

test("Settings remains contained and closable on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/labs");
  await page.locator(".activity-bar").getByRole("button", { name: "Settings" }).click();

  const dialog = page.getByRole("dialog", { name: "Settings" });
  await expect(dialog).toBeVisible();
  const geometry = await dialog.evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
    height: element.getBoundingClientRect().height,
  }));
  expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.clientWidth);
  expect(geometry.height).toBe(844);

  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(page).toHaveURL(/\/labs$/);
});

test("a direct Settings URL closes to the default workspace", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/settings/iam");
  await expect(page.getByRole("dialog", { name: "Settings" })).toBeVisible();

  await page.keyboard.press("Escape");

  await expect(page.getByRole("dialog", { name: "Settings" })).toHaveCount(0);
  await expect(page).toHaveURL(/\/overview$/);
});
