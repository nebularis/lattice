// SPDX-License-Identifier: MPL-2.0
// The studio against the real service, worker, Fuseki and RabbitMQ: a workspace from a sample,
// a refusal the compiler finds while the author edits, and a compilation's SPARQL. Run with the
// stack up (the service's README), as `yarn workspace @lattice/config-studio run test:stack`.

import { expect, test } from "@playwright/test";

const PROFILE = "https://example.org/lending#LoanApplicationStrongProfile";

test("an author edits, sees the compiler's refusal, fixes it and compiles", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Lending Loan/ }).click();
  await page.getByLabel("Name").fill(`Stack test ${Date.now()}`);
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  const ws = page.url().split("/w/")[1];
  await expect(page.getByRole("status")).not.toHaveText("Validating", { timeout: 30_000 });

  await page.goto(`/#/w/${ws}/persistence/${encodeURIComponent(PROFILE)}`);
  const privacy = page.getByRole("region", { name: "Privacy" });
  await privacy.getByRole("button", { name: "Privacy" }).click();
  await privacy.getByRole("button", { name: "Personal data", exact: true }).click();
  await privacy.getByRole("button", { name: "No erasure", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText(/violation/, { timeout: 30_000 });
  await expect(page.locator(".editor")).toContainText("no lawful erasure path");

  await privacy.getByRole("button", { name: "Crypto shred", exact: true }).click();
  await expect(page.getByRole("status")).not.toHaveText(/violation|Validating/, { timeout: 30_000 });
  await page.keyboard.press("ControlOrMeta+s");
  await expect(page.getByRole("button", { name: "Saved" })).toBeDisabled();

  await page.goto(`/#/w/${ws}/build`);
  await page.getByRole("button", { name: "Compile persistence" }).click();
  await expect(page.getByLabel("Job state")).toContainText("Succeeded", { timeout: 60_000 });
  await expect(page.getByRole("option", { name: "compiled-profile.ttl" })).toBeVisible();
  await page.getByRole("option", { name: "cas-replace.rq" }).click();
  await expect(page.locator("main .code")).toContainText("DELETE");
});

test("an author tests an interval condition and reads how a contract resolves, against the real engines", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Lending eligibility/ }).click();
  await page.getByLabel("Name").fill(`Stack eligibility ${Date.now()}`);
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  const ws = page.url().split("/w/")[1];

  await page.goto(`/#/w/${ws}/eligibility/${encodeURIComponent("https://example.org/lattice/eligibility/minimum-credit-condition")}`);
  const tests = page.getByRole("region", { name: "Tests" });
  await expect(tests.getByRole("row", { name: /question-1/ })).toContainText("Permitted", { timeout: 30_000 });
  await tests.getByLabel("Candidate value").fill("650");
  await tests.getByLabel("Expect", { exact: true }).selectOption("Permitted");
  await tests.getByRole("button", { name: "Add test" }).click();
  await expect(tests.getByLabel("fails")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole("status").first()).toHaveText(/violation/);
  await tests.getByLabel("Expected decision").first().selectOption("Denied");
  await expect(tests.getByText("0 fail")).toBeVisible({ timeout: 30_000 });

  await page.goto(`/#/w/${ws}/eligibility/${encodeURIComponent("https://example.org/lattice/eligibility/eligible-sector")}`);
  await expect(page.getByRole("region", { name: "Decision by concept" })).toContainText("2 permitted", { timeout: 30_000 });

  await page.goto(`/#/w/${ws}/vocabulary/${encodeURIComponent("https://example.org/lattice/eligibility/sector-contract")}`);
  const table = page.getByRole("table", { name: "Resolution table" });
  await expect(table.getByRole("row", { name: /Lender B/ })).toContainText("Lender B sector codes", { timeout: 30_000 });
});
