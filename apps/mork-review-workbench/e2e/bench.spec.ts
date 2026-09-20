import { expect, test } from "@playwright/test";

test("records a reshape choice without exposing technical internals", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "ARR derivation evidence" })).toBeVisible();
  await page.getByRole("button", { name: "Reshape" }).click();
  await expect(page.getByText("Structural feedback only. Projection statistics remain unchanged.")).toBeVisible();
  await expect(page.getByText("MCN, lint diagnostics, and pack internals are restricted to engineering roles.")).toBeVisible();
  await expect(page.getByText("secret")).toHaveCount(0);
});

test("shows calibration-gated bulk confirmation and named-axiom reopening", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Bulk confirm unavailable" })).toBeDisabled();
  await expect(page.getByText("New named axiom reopens approvals approval-14 and approval-21.")).toBeVisible();
  await expect(page.getByText("No source syntax")).toBeVisible();
  await expect(page.getByText("Engineering review required")).toBeVisible();
  await expect(page.getByText("Replayable events")).toBeVisible();
});