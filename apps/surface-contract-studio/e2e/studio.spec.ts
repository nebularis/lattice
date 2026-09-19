import { expect, test } from "@playwright/test";

test("authors a Promotion path and opens the technical inspection view", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Subscription currency" })).toBeVisible();
  await page.getByRole("button", { name: "Add path step" }).click();
  await expect(page.getByPlaceholder("namespace:property")).toHaveCount(4);
  await page.getByRole("button", { name: "Technical view" }).click();
  await expect(page.getByText("Generated declaration preview")).toBeVisible();
  await page.getByRole("button", { name: "Save draft" }).click();
  await expect(page.getByRole("button", { name: "Saved draft" })).toBeVisible();
});

test("shows Index population and closure controls", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: /Job family lookup/ }).click();
  await expect(page.getByText("Population and closure")).toBeVisible();
  await expect(page.getByLabel("Include `skos:broader` closure")).toBeChecked();
});

test("shows Projection staging evidence without an activation control", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Annual recurring revenue/ }).click();
  await expect(page.getByText("MORK Technical Inspector")).toBeVisible();
  await expect(page.getByText("mork/staging/arr-r-001")).toBeVisible();
  await expect(page.getByText("Mapping activation is governed by the MORK workflow and cannot be requested here.")).toBeVisible();
});
