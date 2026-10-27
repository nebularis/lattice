// SPDX-License-Identifier: MPL-2.0
// The author's journey through the studio, against the fake service in fake-service.ts.

import { expect, test, type Page } from "@playwright/test";
import { FakeService } from "./fake-service";

const PROFILE = "https://example.org/lending#LoanApplicationStrongProfile";

async function lendingWorkspace(page: Page, fake: FakeService): Promise<string> {
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Lending Loan/ }).click();
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
  // The baseline's outcome scheme is vocabulary, so the sample saves that too.
  expect(fake.saves.map((s) => [s.name, s.ifMatch]).sort()).toEqual([
    ["persistence", '"0"'],
    ["vocabulary", '"0"'],
  ]);
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

const SECTOR = "https://example.org/lattice/eligibility/eligible-sector";
const CREDIT = "https://example.org/lattice/eligibility/minimum-credit-condition";

async function eligibilityWorkspace(page: Page, fake: FakeService): Promise<string> {
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Lending eligibility/ }).click();
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  return [...fake.workspaces.keys()][0];
}

test("an eligibility sample is sorted into vocabulary, quantification and eligibility, each saved from revision 0", async ({ page }) => {
  const fake = new FakeService();
  const ws = await eligibilityWorkspace(page, fake);
  const w = fake.workspaces.get(ws)!;
  expect(w.graphs.vocabulary).toContain("voc:SchemeBinding");
  expect(w.graphs.quantification).toContain("qnt:RangeSet");
  expect(w.graphs.eligibility).toContain("elg:IntervalCondition");
  expect(w.graphs.eligibility).not.toContain("qnt:Bound");
  expect(fake.saves.map((s) => [s.name, s.ifMatch]).sort()).toEqual([
    ["eligibility", '"0"'],
    ["quantification", '"0"'],
    ["vocabulary", '"0"'],
  ]);
});

test("a scheme contract's resolutions are a table of segments and scopes, and trying a moment picks one cell", async ({ page }) => {
  const fake = new FakeService();
  const ws = await eligibilityWorkspace(page, fake);
  await page.goto(`/#/w/${ws}/vocabulary/${encodeURIComponent("https://example.org/lattice/eligibility/sector-contract")}`);
  const table = page.getByRole("table", { name: "Resolution table" });
  await expect(table.getByRole("columnheader", { name: "From 2026-01-01" })).toBeVisible();
  await expect(table.getByRole("row", { name: /Lender B/ })).toContainText("Lender B sector codes");
  await page.getByLabel("Resolution time").fill("2026-06-01T12:00");
  await page.locator(".try").getByRole("checkbox").check();
  await expect(page.getByRole("status", { name: "Resolution" })).toContainText("Resolves to Lender B sector codes by binding lender-b-binding");
  await page.getByLabel("Resolution time").fill("2025-06-01T12:00");
  await expect(page.getByRole("status", { name: "Resolution" })).toContainText("as the contract's fallback");
});

test("a concept condition shows each concept's decision and decides a new test against its expectation", async ({ page }) => {
  const fake = new FakeService();
  const ws = await eligibilityWorkspace(page, fake);
  await page.goto(`/#/w/${ws}/eligibility/${encodeURIComponent(SECTOR)}`);
  const expansion = page.getByRole("region", { name: "Decision by concept" });
  await expect(expansion.getByText("1 permitted")).toBeVisible();
  await expect(expansion.getByText("1 denied")).toBeVisible();
  const tests = page.getByRole("region", { name: "Tests" });
  await expect(tests.getByRole("row", { name: /q-retail/ })).toContainText("Permitted");
  await tests.getByPlaceholder("A candidate concept").fill("Textil");
  await tests.getByPlaceholder("A candidate concept").press("Enter");
  await tests.getByLabel("Expect", { exact: true }).selectOption("Permitted");
  await tests.getByRole("button", { name: "Add test" }).click();
  await expect.poll(() => fake.submitted.filter((s) => s.target === "eligibility").pop()?.body ?? "").toContain("cst:expectedDecision elg:Permitted");
  await expect(tests.getByText("1 fail")).toBeVisible();
  await expect(tests.getByLabel("fails")).toBeVisible();
});

test("an interval test writes its candidate as a point range set, and the number line marks it", async ({ page }) => {
  const fake = new FakeService();
  const ws = await eligibilityWorkspace(page, fake);
  await page.goto(`/#/w/${ws}/eligibility/${encodeURIComponent(CREDIT)}`);
  await expect(page.getByRole("img", { name: "Ranges on a number line" })).toBeVisible();
  const tests = page.getByRole("region", { name: "Tests" });
  await tests.getByLabel("Candidate value").fill("650");
  await tests.getByLabel("Expect", { exact: true }).selectOption("Denied");
  await tests.getByRole("button", { name: "Add test" }).click();
  await expect.poll(() => fake.submitted.filter((s) => s.target === "eligibility").pop()?.body ?? "").toContain('qnt:numericValue "650"^^xsd:decimal');
  await expect(tests.getByText("1 pass")).toBeVisible();
  await expect(page.getByRole("region", { name: "Required values" }).getByText("650 outside")).toBeVisible();
  expect(fake.submitted.filter((s) => s.target === "eligibility").pop()!.body).toContain("elg:candidateRangeSet");
});

test("a scheme's concepts are added as a tree, and a binding's validity is written as a temporal scope", async ({ page }) => {
  const fake = new FakeService();
  const ws = await eligibilityWorkspace(page, fake);
  await page.goto(`/#/w/${ws}/vocabulary/${encodeURIComponent("https://example.org/lattice/eligibility/industry-classification")}`);
  const concepts = page.getByRole("region", { name: "Concepts" });
  await concepts.getByRole("button", { name: "Narrower" }).first().click();
  await concepts.getByLabel("New concept").fill("Bakery");
  await concepts.getByRole("button", { name: "Add concept" }).click();
  await expect(concepts.getByRole("button", { name: "Bakery", exact: true })).toBeVisible();
  await expect.poll(() => fake.submitted.filter((s) => s.target === "vocabulary").pop()?.body ?? "").toMatch(/skos:prefLabel "Bakery"@en/);

  await page.goto(`/#/w/${ws}/vocabulary/${encodeURIComponent("https://example.org/lattice/eligibility/lender-b-binding")}`);
  await page.getByLabel("Valid to").fill("2027-01-01T00:00");
  await expect.poll(() => fake.submitted.filter((s) => s.target === "vocabulary").pop()?.body ?? "").toContain('fnd:validTo "2027-01-01T00:00:00Z"^^xsd:dateTime');
});

test("testing a profile's composed decision is marked as under construction", async ({ page }) => {
  const fake = new FakeService();
  const ws = await eligibilityWorkspace(page, fake);
  await page.goto(`/#/w/${ws}/eligibility/${encodeURIComponent("https://example.org/lattice/eligibility/profile-a")}`);
  await expect(page.getByRole("note")).toContainText("Under construction");
});
