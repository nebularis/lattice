// SPDX-License-Identifier: MPL-2.0
// The author's journey through the studio, against the fake service in fake-service.ts.

import { expect, test, type Page } from "@playwright/test";
import { FakeService } from "./fake-service";

const PROFILE = "https://example.org/lending#LoanApplicationStrongProfile";

async function lendingWorkspace(page: Page, fake: FakeService): Promise<string> {
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Lending/ }).click();
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  return [...fake.workspaces.keys()][0];
}

test("a sample is sorted into baseline and persistence, and the overview shows the class's profile", async ({ page }) => {
  const fake = new FakeService();
  const ws = await lendingWorkspace(page, fake);
  const w = fake.workspaces.get(ws)!;
  expect(w.label).toBe("Lending");
  expect(w.graphs.baseline).toContain("LoanApplication");
  expect(w.graphs.baseline).not.toContain("DataAccessProfile");
  expect(w.graphs.persistence).toContain("dal:DataAccessProfile");
  expect(fake.saves.map((s) => [s.name, s.ifMatch])).toEqual([["persistence", '"0"']]);
  const row = page.getByRole("row", { name: /^Loan application/ });
  await expect(row.getByRole("button", { name: /Data access profile: Named graph boundary · Optimistic/ })).toBeVisible();
  await expect(page.getByText("1/6")).toBeVisible();
});

test("a field's options and their meanings come from the ontology, and a change is validated unsaved", async ({ page }) => {
  const fake = new FakeService();
  const ws = await lendingWorkspace(page, fake);
  await page.goto(`/#/w/${ws}/persistence/${encodeURIComponent(PROFILE)}`);
  const boundary = page.getByRole("region", { name: "Aggregate boundary" });
  await expect(boundary.getByRole("button", { name: "Named graph boundary", pressed: true })).toBeVisible();
  await expect(boundary.getByText("The aggregate root's IRI names a dedicated graph")).toBeVisible();

  const privacy = page.getByRole("region", { name: "Privacy" });
  await privacy.getByRole("button", { name: "Privacy" }).click();
  await privacy.getByRole("button", { name: "Personal data", exact: true }).click();
  await privacy.getByRole("button", { name: "No erasure", exact: true }).click();

  await expect(page.getByRole("status")).toHaveText("1 violation");
  await expect(privacy.getByText("Personal data has no lawful erasure path.")).toBeVisible();
  const validation = fake.submitted.filter((s) => s.kind === "validate").pop()!;
  expect(validation.target).toBe("persistence");
  expect(validation.body).toContain("dal:erasureStrategy dal:NoErasure");
  expect(fake.workspaces.get(ws)!.graphs.persistence).not.toContain("NoErasure");
});

test("undo and redo step through edits, and save sends the revision it read", async ({ page }) => {
  const fake = new FakeService();
  const ws = await lendingWorkspace(page, fake);
  await page.goto(`/#/w/${ws}/persistence/${encodeURIComponent(PROFILE)}`);
  const shards = page.getByRole("textbox", { name: "Meta shards", exact: true });
  await expect(shards).toHaveValue("64");
  await shards.fill("16");
  await shards.press("Enter");
  await expect(page.getByRole("button", { name: "Save" })).toBeEnabled();
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(shards).toHaveValue("64");
  await expect(page.getByRole("button", { name: "Saved" })).toBeDisabled();
  await page.getByRole("button", { name: "Redo" }).click();
  await expect(shards).toHaveValue("16");
  await page.keyboard.press("ControlOrMeta+s");
  await expect(page.getByRole("button", { name: "Saved" })).toBeDisabled();
  const save = fake.saves.pop()!;
  expect(save.ifMatch).toBe('"1"');
  expect(save.body).toContain('dal:metaShards "16"^^xsd:long');
});

test("a save that lost to another author shows the difference and keeps mine on request", async ({ page }) => {
  const fake = new FakeService();
  const ws = await lendingWorkspace(page, fake);
  await page.goto(`/#/w/${ws}/persistence/${encodeURIComponent(PROFILE)}`);
  const shards = page.getByRole("textbox", { name: "Meta shards", exact: true });
  await shards.fill("8");
  await shards.press("Enter");
  fake.saveElsewhere(ws, "persistence", fake.workspaces.get(ws)!.graphs.persistence + "\n<https://example.org/x> <https://example.org/y> \"theirs\" .\n");
  await page.getByRole("button", { name: "Save" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("changed since you loaded it");
  await expect(dialog.getByLabel("Differences")).toContainText('"theirs"');
  await dialog.getByRole("button", { name: "Keep mine" }).click();
  await expect(dialog).toBeHidden();
  const last = fake.saves.pop()!;
  expect(last.ifMatch).toBe('"2"');
  expect(last.body).not.toContain("theirs");
  expect(fake.workspaces.get(ws)!.revisions.persistence).toBe(3);
});

test("a promotion made from the overview gets a carrier, and its read path is built hop by hop", async ({ page }) => {
  const fake = new FakeService();
  await lendingWorkspace(page, fake);
  await page.getByRole("row", { name: /^Loan application/ }).getByRole("button", { name: "Promotion" }).click();
  await expect(page.getByText("carrier Loan application")).toBeVisible();
  const path = page.getByRole("region", { name: "Read path" });
  await path.getByRole("combobox").fill("decis");
  await path.getByRole("combobox").press("Enter");
  await expect(path.getByText("One forward hop is written as srf:readProperty.")).toBeVisible();
  await path.getByRole("combobox").fill("outc");
  await path.getByRole("combobox").press("Enter");
  await expect(path.getByText("2 hops are written as srf:PathStep nodes.")).toBeVisible();
  await path.getByRole("button", { name: "Reverse direction" }).first().click();
  // Validation follows each edit after a pause, so wait for the one that saw the reversal.
  await expect.poll(() => fake.submitted.filter((s) => s.target === "surface").pop()?.body ?? "").toContain("srf:stepDirection srf:Inverse");
  expect(fake.submitted.filter((s) => s.target === "surface").pop()!.body).not.toContain("srf:readProperty");
});

test("a compile follows the job's states and shows what the compiler produced", async ({ page }) => {
  const fake = new FakeService();
  const ws = await lendingWorkspace(page, fake);
  await page.goto(`/#/w/${ws}/build`);
  await page.getByRole("button", { name: "Compile persistence" }).click();
  await expect(page.getByLabel("Job state")).toContainText("Succeeded");
  await expect(page.getByText("Compiled", { exact: true })).toBeVisible();
  await expect(page.getByRole("option", { name: "cas-replace.rq" })).toBeVisible();
  await expect(page.locator("main .code")).toContainText("SELECT ?s WHERE");
  expect(fake.submitted.find((s) => s.kind === "compile")!.body).toContain("dal:DataAccessProfile");
});

test("the command palette jumps to a class of the baseline", async ({ page }) => {
  const fake = new FakeService();
  await lendingWorkspace(page, fake);
  await page.keyboard.press("ControlOrMeta+k");
  await page.getByPlaceholder("Go to a view, a node or a class").fill("guarant");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Guarantor", level: 2 })).toBeVisible();
  await expect(page.getByText("Subclass of Party")).toBeVisible();
});
