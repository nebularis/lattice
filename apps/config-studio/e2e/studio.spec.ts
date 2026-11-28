// SPDX-License-Identifier: MPL-2.0
// The author's journey through the studio, against the fake service in fake-service.ts.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test, type Locator, type Page } from "@playwright/test";
import { FakeService, STAGED_FIRST, STAGED_SECOND } from "./fake-service";
import { FIXTURE as SAMPLE_FIXTURE, type Recorded as SampleRuns } from "./sampleRuns";
import { EX, FACILITY, FIXTURE, ROOT, STEPS, type Recorded } from "./journey";

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
  await expect(page.getByRole("listbox", { name: "Artefacts" })).toBeVisible();
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
  await expect(page.getByRole("region", { name: "Superclasses" })).toContainText("Party");
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

const FORM = "https://example.org/lattice/wording/facility-form/";

async function builderWorkspace(page: Page, fake: FakeService): Promise<string> {
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Contract builder/ }).click();
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  return [...fake.workspaces.keys()][0];
}

test("a builder sample is sorted into library, assembly and the layers a form reads", async ({ page }) => {
  const fake = new FakeService();
  const ws = await builderWorkspace(page, fake);
  const w = fake.workspaces.get(ws)!;
  expect(w.graphs.library).toContain("wrd:Wording");
  expect(w.graphs.assembly).toContain("cst:Assembly");
  expect(w.graphs.assembly).toContain("wrd:VariableValue");
  expect(w.graphs.eligibility).toContain("elg:IntervalCondition");
  expect(w.graphs.library).not.toContain("wrd:VariableValue");
  expect(fake.saves.map((s) => [s.name, s.ifMatch]).sort()).toEqual([
    ["assembly", '"0"'],
    ["eligibility", '"0"'],
    ["library", '"0"'],
    ["meaning", '"0"'],
    ["quantification", '"0"'],
    ["review", '"0"'],
    ["vocabulary", '"0"'],
  ]);
  // The roles are the party layer's, so they stay in the baseline.
  expect(w.graphs.baseline).toContain("pty:Role");
  expect(w.graphs.meaning).toContain("ins:Obligation");
  expect(w.graphs.review).toContain("cst:Proposal");
});

test("the library is an outline of each form, and an element opens in the shape-driven editor", async ({ page }) => {
  const fake = new FakeService();
  await builderWorkspace(page, fake);
  await page.getByRole("button", { name: "Builder" }).click();
  await expect(page.getByRole("button", { name: "Builder" })).toHaveAttribute("aria-pressed", "true");
  const tree = page.getByRole("tree", { name: "Library" });
  // Order by rank key: sections 5, 9 and 12, and 5.1, 5.2, 5.3 within section 5.
  const ids = await tree.locator(".outline-row .outline-id").allTextContents();
  expect(ids.slice(0, 8)).toEqual(["5", "5.1", "5.2", "5.2A", "5.2B", "5.3", "9", "9.1"]);
  await expect(tree.getByRole("treeitem", { name: /5\.2 .*Slot, 2 variants/ })).toBeVisible();
  await expect(tree.getByRole("treeitem", { name: /5\.2B .*Variation/ })).toBeVisible();
  await expect(tree.getByRole("treeitem", { name: /5\.1 .*Mandatory/ })).toBeVisible();
  await expect(tree.getByRole("treeitem", { name: /5\.3 .*Optional/ })).toBeVisible();
  await expect(tree.getByRole("treeitem", { name: /9\.1 .*Conditional.*Condition: when syndicated/ })).toBeVisible();
  await expect(tree.getByRole("treeitem", { name: /lender-count.*Governing/ })).toBeVisible();
  await expect(tree.getByRole("treeitem", { name: /permitted-jurisdictions.*Embedded/ })).toBeVisible();

  await tree.getByRole("treeitem", { name: /5\.3 / }).click();
  await expect(page.getByRole("heading", { name: "5.3", level: 2 })).toBeVisible();
  await expect(page.locator(".editor .iri")).toHaveText(FORM + "cl-5-3");
  await expect(page.getByRole("treeitem", { name: /5\.3 / })).toHaveAttribute("aria-selected", "true");
  // The same shared inspector shows the node's Turtle.
  await expect(page.locator("aside").getByText("Read-only: edit through the forms.")).toBeVisible();
});

test("an assembly chooses options and sets values, and assembling shows the findings and the document", async ({ page }) => {
  const fake = new FakeService();
  const ws = await builderWorkspace(page, fake);
  await page.goto(`/#/w/${ws}/assembly`);
  const list = page.locator(".list");
  await list.getByText("Syndicated, three lenders, UK and Ireland").click();

  const choices = page.getByRole("region", { name: "Choices" });
  await expect(choices.getByRole("checkbox")).toHaveCount(3);
  await expect(choices.getByRole("checkbox", { name: /5\.2B/ })).toBeChecked();
  await expect(choices.getByRole("checkbox", { name: /5\.2A/ })).not.toBeChecked();
  await choices.getByRole("checkbox", { name: /5\.3/ }).check();

  const values = page.getByRole("region", { name: "Values" });
  await expect(values.getByLabel("lender-count")).toHaveValue(/^3(\.0)?$/);
  await values.getByLabel("lender-count").fill("4");
  await values.getByLabel("lender-count").press("Enter");
  await expect(values.getByText("Written as xsd:decimal")).toBeVisible();
  await expect(values.getByText("United Kingdom")).toBeVisible();

  await page.getByRole("button", { name: "Assemble" }).click();
  const outcome = page.getByRole("region", { name: "Assemble outcome" });
  await expect(outcome.getByText("1 of 2 assembled")).toBeVisible();
  const submitted = fake.submitted.find((s) => s.kind === "assemble")!;
  expect(submitted.target).toBe("assembly");
  // The edited assembly, unsaved, with the library and the conditions beside it.
  expect(submitted.body).toContain("cst:choice");
  expect(submitted.body).toContain("cst:choice ex:cl-5-2b, ex:cl-5-3");
  expect(submitted.body).toMatch(/wrd:literalValue "4"\^\^xsd:decimal|wrd:literalValue 4\b/);
  expect(submitted.body).toContain("wrd:Wording");
  expect(submitted.body).toContain("elg:IntervalCondition");

  // The refused assembly gives a finding with its stage, and a link to the variable it names.
  const findings = outcome.getByRole("list", { name: "Findings" });
  await expect(findings).toContainText("the value of lender-count is Undetermined");
  await expect(findings.getByText("decide", { exact: true })).toBeVisible();
  // The assembly that gave a record gives its document, readably, with the value shown.
  const document = outcome.getByRole("region", { name: "Assembled Syndicated, three lenders, UK and Ireland" });
  await expect(document.getByRole("heading", { name: "Syndicated, three lenders, UK and Ireland" })).toBeVisible();
  await expect(document.getByRole("heading", { name: "Section 12" })).toBeVisible();
  await expect(document.getByText("Each interest period is three months.")).toBeVisible();
  await expect(document.locator("mark.doc-var")).toHaveText("United Kingdom, Ireland");
  await expect(outcome.getByRole("region", { name: /Assembled No lender count/ })).toHaveCount(0);
  await document.getByRole("button", { name: "View record" }).click();
  await expect(document.locator(".code")).toContainText("wrd:AssembledWording");

  await findings.getByRole("button", { name: /gv-lender-count/ }).click();
  await expect(page).toHaveURL(new RegExp(`/library/${encodeURIComponent(FORM + "gv-lender-count")}`));
  await expect(page.getByRole("treeitem", { name: /lender-count/ })).toHaveAttribute("aria-selected", "true");
});

test("a new assembly is written with a record per value, and saves to the assembly graph", async ({ page }) => {
  const fake = new FakeService();
  const ws = await builderWorkspace(page, fake);
  await page.goto(`/#/w/${ws}/assembly`);
  await page.locator(".list-head").getByRole("button", { name: "Add" }).click();
  await expect(page.getByRole("heading", { name: "Assembly 3", level: 2 })).toBeVisible();
  await expect(page.getByLabel("Form")).toHaveValue(FORM + "form");
  const choices = page.getByRole("region", { name: "Choices" });
  await choices.getByRole("checkbox", { name: /5\.2A/ }).check();
  const values = page.getByRole("region", { name: "Values" });
  await values.getByLabel("lender-count").fill("2");
  await values.getByLabel("lender-count").press("Enter");
  await page.keyboard.press("ControlOrMeta+s");
  await expect(page.getByRole("button", { name: "Saved" })).toBeDisabled();
  const save = fake.saves.filter((s) => s.name === "assembly").pop()!;
  expect(save.ifMatch).toBe('"1"');
  expect(save.body).toContain("cst:assembles");
  expect(save.body).toMatch(/wrd:literalValue "2"\^\^xsd:decimal|wrd:literalValue 2\b/);
  expect(save.body).toContain("wrd:forVariable ex:gv-lender-count");
  // A library save did not happen: only the assembly changed.
  expect(fake.saves.filter((s) => s.name === "library")).toHaveLength(1);
});

test("the meaning view reads each clause's stated meaning, edits a template, enters meaning by hand and reviews a proposal", async ({ page }) => {
  const fake = new FakeService();
  const ws = await builderWorkspace(page, fake);
  await page.getByRole("button", { name: "Builder" }).click();
  await page.getByRole("link", { name: /^Meaning/ }).click();
  const tree = page.getByRole("tree", { name: "Meaning" });

  // 5.1 states an obligation, read in plain words with roles shown as roles. 12.1 has none, and 5.3 has a proposal waiting.
  await expect(tree.getByRole("treeitem", { name: /5\.1 .*Borrower must Pay Lender/ })).toBeVisible();
  await expect(tree.getByRole("treeitem", { name: /9\.1 .*Agent must Provide service Lender/ })).toBeVisible();
  await expect(tree.getByRole("treeitem", { name: /12\.1 .*No stated meaning/ })).toBeVisible();
  await expect(tree.getByRole("treeitem", { name: /5\.3 .*No stated meaning.*Proposal waiting/ })).toBeVisible();

  // The clause shows its term, and what the term reads is derived from its templates.
  await tree.getByRole("treeitem", { name: /5\.1 / }).click();
  await expect(page.getByRole("heading", { name: "5.1", level: 2 })).toBeVisible();
  const stated = page.getByRole("region", { name: "Stated meaning" });
  await expect(stated.getByText("Borrower must Pay Lender")).toBeVisible();
  const reads = page.getByRole("region", { name: /What the term reads/ });
  await expect(reads.getByText("Borrower", { exact: true })).toBeVisible();
  await expect(reads.getByText("Lender", { exact: true })).toBeVisible();
  await expect(reads.getByText("Pay", { exact: true })).toBeVisible();

  // A template opens in the shape-driven editor on the meaning part.
  await stated.getByRole("button", { name: "Edit" }).click();
  await expect(page.locator(".editor .iri").last()).toHaveText("https://example.org/lattice/studio/meaning/pay-interest");
  await expect(page.getByRole("region", { name: "Properties" }).getByText("ins:obligor")).toBeVisible();
  await page.getByRole("button", { name: /^Back to clause 5\.1/ }).click();

  // Manual entry on 12.1 makes a proposal confirmed at once, and states the term the clause lacked.
  await tree.getByRole("treeitem", { name: /12\.1 / }).click();
  await expect(page.getByRole("heading", { name: "12.1", level: 2 })).toBeVisible();
  const entry = page.getByRole("region", { name: "Manual entry" });
  await entry.getByLabel("Relation kind").selectOption({ label: "Obligation" });
  await entry.getByLabel("Obligor").selectOption({ label: "Borrower" });
  await entry.getByLabel("Obligee").selectOption({ label: "Lender" });
  await entry.getByLabel("Activity").selectOption({ label: "Report" });
  await expect(entry.getByText("Borrower must Report Lender")).toBeVisible();
  await entry.getByRole("button", { name: "Confirm entry" }).click();
  await expect(tree.getByRole("treeitem", { name: /12\.1 .*Borrower must Report Lender/ })).toBeVisible();
  await page.keyboard.press("ControlOrMeta+s");
  await expect(page.getByRole("button", { name: "Saved" })).toBeDisabled();
  const meaningSave = fake.saves.filter((s) => s.name === "meaning").pop()!;
  const reviewSave = fake.saves.filter((s) => s.name === "review").pop()!;
  expect(meaningSave.body).toContain("ins:expressedIn ex:cl-12-1");
  expect(reviewSave.body).toContain('cst:proposer "manual"');
  expect(reviewSave.body).toContain("cst:decision cst:Confirm");
  expect(reviewSave.body).toContain("cst:span ex:cl-12-1");
  expect(reviewSave.body).toContain("cst:payload");
  // The live validation of the meaning part sent the library beside it, and the review part's answers no findings.
  await expect.poll(() => fake.submitted.filter((s) => s.target === "meaning").pop()?.body ?? "").toContain("wrd:Wording");
  expect(fake.submitted.some((s) => s.kind === "validate" && s.target === "review")).toBe(true);

  // 5.3 has a proposal waiting. Confirming it writes its payload into the meaning part.
  await tree.getByRole("treeitem", { name: /5\.3 / }).click();
  const card = page.getByRole("region", { name: "Proposal by sentence-forms for 5.3" });
  await expect(card.getByText("Borrower must Report Lender")).toBeVisible();
  await expect(card.getByRole("button")).toContainText(["Confirm", "Retarget", "Decline", "Defer"]);
  await card.getByRole("button", { name: "Confirm", exact: true }).click();
  await expect(page.getByRole("region", { name: "Proposal by sentence-forms for 5.3" })).toHaveCount(0);
  await expect(tree.getByRole("treeitem", { name: /5\.3 .*Borrower must Report Lender/ })).toBeVisible();
  await expect(tree.getByRole("treeitem", { name: /5\.3 .*Proposal waiting/ })).toHaveCount(0);
  await page.keyboard.press("ControlOrMeta+s");
  await expect(page.getByRole("button", { name: "Saved" })).toBeDisabled();
  expect(fake.workspaces.get(ws)!.graphs.meaning).toContain("m:term-5-3 a ins:Template, ins:Term");
  const confirmed = fake.saves.filter((s) => s.name === "review").pop()!;
  expect(confirmed.body).toMatch(/cst:decision cst:Confirm/);
  expect(confirmed.body).toContain("cst:decidedAt");
});

test("the propose control adds a proposer's proposals for review, and shows why a proposer could not run", async ({ page }) => {
  const fake = new FakeService();
  await builderWorkspace(page, fake);
  await page.getByRole("button", { name: "Builder" }).click();
  await page.getByRole("link", { name: /^Meaning/ }).click();
  const tree = page.getByRole("tree", { name: "Meaning" });
  const bar = page.getByRole("group", { name: "Propose" });

  // The sentence-form proposer proposes a permission for 12.1 and finds nothing for 5.2A.
  await bar.getByLabel("Proposer").selectOption({ label: "Sentence forms" });
  await bar.getByRole("button", { name: "Propose" }).click();
  const outcome = page.getByRole("status", { name: "Propose outcome" });
  await expect(outcome.getByText("1 proposal added from sentence-forms")).toBeVisible();
  await expect(outcome.getByText("No candidate for clause 5.2A")).toBeVisible();
  const submitted = fake.submitted.find((s) => s.kind === "propose")!;
  expect(submitted.target).toBe("sentence-forms");
  expect(submitted.body).toContain("wrd:Wording");
  await expect(tree.getByRole("treeitem", { name: /12\.1 .*Proposal waiting/ })).toBeVisible();

  // The reviewer sees what the proposal rests on, and confirms it.
  await tree.getByRole("treeitem", { name: /12\.1 / }).click();
  const card = page.getByRole("region", { name: "Proposal by sentence-forms for 12.1" });
  await expect(card.getByText("Borrower may Report Lender")).toBeVisible();
  await expect(card.getByText("may operate in")).toBeVisible();
  await expect(card.getByText("Proposer version: sentence-forms 1")).toBeVisible();
  await card.getByRole("button", { name: "Confirm", exact: true }).click();
  await expect(tree.getByRole("treeitem", { name: /12\.1 .*Borrower may Report Lender/ })).toBeVisible();

  // A proposer that cannot run says why.
  await bar.getByLabel("Proposer").selectOption({ label: "Language model" });
  await bar.getByRole("button", { name: "Propose" }).click();
  await expect(bar.getByText("no language model is configured")).toBeVisible();
});

test("the instrument view shows terms in their tier and regimes as state machines, and dry-runs a term's conditions", async ({ page }) => {
  const fake = new FakeService();
  await builderWorkspace(page, fake);
  await page.getByRole("button", { name: "Builder" }).click();
  await page.getByRole("link", { name: /^Instrument/ }).click();
  const tree = page.getByRole("tree", { name: "Instrument" });

  // The stated tier holds 9.1's term with its relation, and the bound tier says why it is empty.
  await expect(tree.getByRole("treeitem", { name: /9\.1 .*Agent must Provide service Lender/ })).toBeVisible();
  await expect(tree.getByText("Bound meaning comes only from instantiating an assembled wording")).toBeVisible();

  // The regime is drawn with its states, its initial state and a transition labelled by its trigger, and gates the obligation.
  const regime = page.getByRole("region", { name: "Regime facility regime" });
  await expect(regime.getByRole("button", { name: "State In force, initial" })).toBeVisible();
  await expect(regime.getByRole("button", { name: "State Notice period" })).toBeVisible();
  await expect(regime.getByRole("button", { name: "State Terminated" })).toBeVisible();
  await expect(regime.getByRole("button", { name: "Transition: Breach of Agent must Provide service Lender" })).toBeVisible();
  await expect(regime.getByRole("button", { name: "Transition: Expiry" })).toBeVisible();
  await expect(regime.getByLabel("Gating in facility regime").getByRole("button", { name: "Agent must Provide service Lender" })).toBeVisible();

  // A state opens in the shape-driven editor.
  await regime.getByRole("button", { name: "State Notice period" }).click();
  await expect(page.locator(".editor .iri")).toHaveText("https://example.org/lattice/studio/meaning/fr-notice");

  // A term reads its condition, and a dry run decides it over the number given, then deletes the job.
  await tree.getByRole("treeitem", { name: /9\.1 / }).click();
  await expect(page.getByRole("region", { name: "What the term reads" }).getByText("more than one lender")).toBeVisible();
  const dry = page.getByRole("region", { name: "Dry run" });
  await expect(dry.getByRole("note")).toContainText("Stepping a regime over sample events is not available yet");
  await dry.getByRole("button", { name: "Run" }).click();
  const outcome = dry.getByRole("status", { name: "Dry run outcome" });
  await expect(outcome.getByText("Undetermined")).toBeVisible();
  await expect(outcome.getByText("No sample fact for when-syndicated-more-than-one-lender")).toBeVisible();
  await dry.getByLabel("Number for when syndicated more than one lender").fill("3");
  await dry.getByRole("button", { name: "Run" }).click();
  await expect(outcome.getByText("Permitted")).toBeVisible();
  const submitted = fake.submitted.filter((s) => s.kind === "dry-run");
  expect(submitted.map((s) => s.target)).toEqual(["meaning", "meaning"]);
  expect(submitted[1].body).toContain("cst:DryRun");
  expect(submitted[1].body).toMatch(/cst:number\s+"3"\^\^xsd:decimal/);
  expect(submitted[1].body).toContain("wrd:Wording");
  const dryRuns = [...fake.jobs].filter(([, j]) => j.kind === "dry-run").map(([id]) => id);
  expect(dryRuns).toHaveLength(2);
  await expect.poll(() => dryRuns.every((id) => fake.deletedJobs.includes(id))).toBe(true);
  // Nothing was saved into any part.
  expect(fake.workspaces.get([...fake.workspaces.keys()][0])!.graphs.meaning).not.toContain("DryRun");
});

test("leaving a workspace ends the waiting on its validations, and coming back leaves no more of them than before", async ({ page }) => {
  // RC5 of plan studio-worker-liveness. A held validation never ends, as one behind a long job does not. Each mount of the workspace
  // submits its validations, and the old mount's closures used to go on polling and leave their jobs, so they stacked.
  const fake = new FakeService();
  fake.hold.add("validate");
  const ws = await lendingWorkspace(page, fake);
  const open = () => [...fake.jobs.entries()].filter(([id, j]) => j.kind === "validate" && !fake.deletedJobs.includes(id)).length;
  await page.waitForTimeout(1500);
  const first = open();
  expect(first).toBeGreaterThan(0);
  await page.goto("/#/");
  await page.waitForTimeout(500);
  expect(open()).toBe(0);
  await page.goto(`/#/w/${ws}`);
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await page.waitForTimeout(1500);
  expect(open()).toBe(first);
});

test("a proposal by a language model that is running when the author leaves the workspace is picked up when they return", async ({ page }) => {
  const fake = new FakeService();
  fake.hold.add("propose:language-model");
  fake.modelConfigured = true;
  await builderWorkspace(page, fake);
  const open = async () => {
    await page.getByRole("button", { name: "Builder" }).click();
    await page.getByRole("link", { name: /^Meaning/ }).click();
    return page.getByRole("group", { name: "Propose" });
  };
  let bar = await open();
  await bar.getByLabel("Proposer").selectOption({ label: "Language model" });
  await bar.getByRole("button", { name: "Propose" }).click();
  await expect(bar.getByRole("button", { name: "Propose" })).toBeDisabled();
  const proposals = () => fake.submitted.filter((s) => s.kind === "propose").length;
  expect(proposals()).toBe(1);

  // The author leaves, and the workspace's views go. The proposal is the store's, and goes on.
  await page.goto("/#/");
  await page.getByRole("button", { name: /Contract builder|Open/ }).first().click().catch(() => undefined);
  await page.goto(`/#/w/${[...fake.workspaces.keys()][0]}`);
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  bar = await open();
  await expect(bar.getByRole("button", { name: "Propose" })).toBeDisabled();
  expect(proposals(), "the view submitted the proposal again").toBe(1);

  // The proposal ends, and the view applies its proposals as if it had waited all along.
  fake.hold.clear();
  await expect(page.getByRole("status", { name: "Propose outcome" }).getByText("proposal added from language-model")).toBeVisible({ timeout: 15_000 });
});

test("a queue no worker consumes is reported to the author, who can dismiss it, and a new warning shows", async ({ page }) => {
  const fake = new FakeService();
  fake.warnings = ["No worker consumes lattice.studio.jobs.long, so proposals by a language model and publications wait. Start one with `mise run studio:worker-long`."];
  await lendingWorkspace(page, fake);
  const warning = page.getByRole("status").filter({ hasText: "The studio has warnings" });
  await expect(warning).toContainText("No worker consumes lattice.studio.jobs.long");
  await warning.getByRole("button", { name: "Dismiss" }).click();
  await expect(warning).toHaveCount(0);
});

test("mapping mode lists every scheme of the workspace, selects one by its row and has no scheme select", async ({ page }) => {
  const fake = new FakeService();
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Policies from XML and JSON/ }).click();
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  const ws = [...fake.workspaces.keys()][0];
  await page.goto(`/#/w/${ws}/mapping`);

  const list = page.getByRole("navigation", { name: "Mapping schemes" });
  const rows = list.getByRole("button");
  await expect(rows).toHaveCount(2);
  await expect(rows.nth(0)).toHaveAttribute("aria-current", "true");
  await expect(rows.nth(1)).not.toHaveAttribute("aria-current", "true");
  await expect(page.getByRole("combobox", { name: "Mapping scheme" })).toHaveCount(0);
  // Both schemes are named Scheme, so what each holds tells them apart.
  const tree = page.getByRole("tree");
  await expect(tree).toBeVisible();
  const before = await tree.textContent();

  await rows.nth(1).click();
  await expect(rows.nth(1)).toHaveAttribute("aria-current", "true");
  await expect(rows.nth(0)).not.toHaveAttribute("aria-current", "true");
  await expect(tree).toBeVisible();
  await expect.poll(() => tree.textContent()).not.toBe(before);
  await expect(page.getByRole("combobox", { name: "Mapping scheme" })).toHaveCount(0);
});

test("the mapping canvas draws a node for each mapping, offers its menus and opens a mapping's card on a click", async ({ page }) => {
  const fake = new FakeService();
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Policies from XML and JSON/ }).click();
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  const ws = [...fake.workspaces.keys()][0];
  await page.goto(`/#/w/${ws}/mapping`);

  // The tree names a mapping of the scheme, and the canvas must show a node with the same name.
  const first = page.getByRole("tree").getByRole("treeitem").first();
  await expect(first).toBeVisible();
  const label = (await first.locator("text").first().textContent())!.trim();
  expect(label).not.toBe("");
  await page.getByRole("group", { name: "Drawing" }).getByRole("button", { name: "Canvas" }).click();
  const mappings = page.locator(".react-flow__node-mapping");
  await expect(mappings.first()).toBeVisible();
  expect(await mappings.count()).toBeGreaterThan(0);
  await expect(mappings.filter({ hasText: label }).first()).toBeVisible();

  const pane = page.locator(".react-flow__pane");
  await pane.click({ button: "right", position: { x: 5, y: 5 } });
  const menu = page.getByRole("menu");
  await expect(menu.getByRole("menuitem", { name: "Add a root datum" })).toBeVisible();
  await expect(menu.getByRole("menuitem", { name: "Lay the scheme out again" })).toBeVisible();
  await page.keyboard.press("Escape");
  await page.locator(".react-flow__pane").click({ position: { x: 5, y: 5 } });
  await expect(menu).toHaveCount(0);

  await mappings.filter({ hasText: label }).first().click();
  await expect(page.getByRole("region", { name: `Mapping ${label}` })).toBeVisible();
});

test("the ontology drawing shows the classes of the baseline, what the shapes state, and selects a class on a click", async ({ page }) => {
  const fake = new FakeService();
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Facility agreement/ }).click();
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  const ws = [...fake.workspaces.keys()][0];
  await page.goto(`/#/w/${ws}/baseline`);

  await page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Diagram" }).click();
  const diagram = page.getByRole("region", { name: "Ontology diagram" });
  const nodes = diagram.locator(".react-flow__node-cls");
  await expect(nodes.filter({ hasText: "Facility" }).first()).toBeVisible();
  // The sample's baseline declares twelve classes, and fifteen properties link them, two of which have the facility as their domain and their range.
  const status = diagram.getByRole("status");
  await expect(status).toHaveText("12 classes and 15 links drawn.");
  // Each is drawn as a loop on its class, the edge leaving and entering the facility on the same side, across the layout's flow.
  const loop = diagram.locator(".react-flow__edge").filter({ has: page.locator("title", { hasText: "ex:refinancesInChain, from Facility to Facility" }) });
  await expect(loop).toHaveCount(1);
  await expect(loop.locator("path.react-flow__edge-path")).toHaveAttribute("d", /./);
  await expect(diagram.locator(".onto-edge-label").filter({ hasText: "ex:refinancesInChain" })).toBeVisible();
  await expect(diagram.getByRole("group", { name: "Ontology view" }).getByRole("button", { name: "Classes and properties" })).toHaveAttribute("aria-pressed", "true");

  // The facility's shape states four of those links, so none is added and four name the shape.
  await diagram.getByLabel("Include shapes").check();
  await expect(status).toHaveText("12 classes and 15 links, 4 stated by shapes drawn.");
  await expect(diagram.locator(".onto-edge-label.dashed")).toHaveCount(0);
  await expect(diagram.locator(".react-flow__edge title").filter({ hasText: "stated by ex:FacilityShape" })).toHaveCount(4);

  await diagram.getByRole("group", { name: "Ontology view" }).getByRole("button", { name: "Class hierarchy" }).click();
  await expect(diagram.getByLabel("Include shapes")).toHaveCount(0);
  await expect(status).toHaveText("12 classes and 3 links drawn.");
  await diagram.getByRole("group", { name: "Ontology view" }).getByRole("button", { name: "Classes and properties" }).click();

  await nodes.filter({ hasText: "Drawdown" }).first().click();
  await expect(page.locator('.list-item[aria-selected="true"]')).toContainText("Drawdown");
  await expect(page.getByRole("region", { name: "Ontology diagram" }).getByRole("status")).toContainText("around Drawdown");
  await expect(diagram.getByLabel("Hops around the selected class")).toBeEnabled();
});

const OWL_HEAD = "@prefix owl: <http://www.w3.org/2002/07/owl#> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n";
const IMPORT_A = "https://example.org/ont/a";
const IMPORT_B = "https://example.org/ont/b";
const ontology = (iri: string) => ({ mimeType: "text/turtle", buffer: Buffer.from(`${OWL_HEAD}<${iri}> a owl:Ontology .\n<${iri}#T> a owl:Class ; rdfs:label "T" .\n`) });
const catalog = (entries: Record<string, string>) => ({
  mimeType: "application/xml",
  buffer: Buffer.from(
    `<?xml version="1.0" encoding="UTF-8"?>\n<catalog prefer="public" xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">\n${Object.entries(entries)
      .map(([name, uri]) => `<uri name="${name}" uri="${uri}"/>`)
      .join("\n")}\n</catalog>\n`,
  ),
});

/** A workspace from the author's own Turtle, whose baseline ontology imports each of `imports`, open on the Baseline view. */
async function importingWorkspace(page: Page, fake: FakeService, imports: string[]): Promise<string> {
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Your own Turtle/ }).click();
  await page.locator("#ws-name").fill("Imports");
  const baseline = `${OWL_HEAD}<https://example.org/ont/base> a owl:Ontology ; owl:imports ${imports.map((i) => `<${i}>`).join(", ")} .\n<https://example.org/ont/base#Thing> a owl:Class ; rdfs:label "Thing" .\n`;
  await page.locator('input[type="file"]').setInputFiles({ name: "base.ttl", mimeType: "text/turtle", buffer: Buffer.from(baseline) });
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  const ws = [...fake.workspaces.keys()][0];
  await page.goto(`/#/w/${ws}/baseline`);
  return ws;
}

test("the imports of the baseline are listed as missing, the plan shows how each resolves, and confirming holds the resolved ones in one request", async ({ page }) => {
  const fake = new FakeService();
  const ws = await importingWorkspace(page, fake, [IMPORT_A, IMPORT_B]);
  const list = page.getByRole("region", { name: "Ontologies" });
  await expect(list.getByText("missing", { exact: true })).toHaveCount(2);
  await expect(list.getByText("2 imports are not held.")).toBeVisible();
  await expect(list.locator(".onto-row.missing").first()).toHaveAttribute("title", /Imported by https:\/\/example.org\/ont\/base/);

  await page.getByRole("button", { name: "Import ontologies" }).click();
  const dialog = page.getByRole("dialog", { name: "Import ontologies" });
  await dialog.getByLabel("Files", { exact: true }).setInputFiles([
    { name: "a.ttl", ...ontology(IMPORT_A) },
    { name: "unrelated.ttl", ...ontology("https://example.org/ont/unrelated") },
    { name: "catalog-v001.xml", ...catalog({ [IMPORT_B]: "b.ttl" }) },
  ]);
  await expect(dialog.getByLabel("Chosen files")).toContainText("catalog-v001.xml");
  await dialog.getByRole("button", { name: "Show the plan" }).click();

  const plan = dialog.getByRole("table", { name: "Import plan" });
  await expect(plan.getByRole("row")).toHaveCount(3);
  await expect(plan.getByRole("row", { name: /ont\/a/ })).toContainText("from a dropped file");
  await expect(plan.getByRole("row", { name: /ont\/a/ })).toContainText("a.ttl");
  await expect(plan.getByRole("row", { name: /ont\/b/ })).toContainText("missing");
  await expect(dialog.getByLabel("Problems with the plan")).toContainText("The catalog maps https://example.org/ont/b to b.ttl, which was not dropped.");
  await expect(dialog.getByRole("status")).toHaveText("1 to hold now, 0 already held, 1 missing.");
  // nothing is held, or shown as held, before the author confirms
  expect(fake.holds).toHaveLength(0);
  await expect(list.getByText("held", { exact: true })).toHaveCount(0);

  await dialog.getByRole("button", { name: "Hold 1 import" }).click();
  await expect(dialog).toHaveCount(0);
  expect(fake.holds).toHaveLength(1);
  expect(fake.holds[0].labels).toEqual([IMPORT_A]);
  expect(fake.workspaces.get(ws)!.imports.map((i) => i.ontology)).toEqual([IMPORT_A]);
  // the saved baseline is untouched by importing
  expect(fake.saves.filter((s) => s.name === "baseline")).toHaveLength(0);
  await expect(list.getByText("held", { exact: true })).toHaveCount(1);
  await expect(list.getByText("example.org/ont/a", { exact: true })).toBeVisible();
  await expect(list.getByText("missing", { exact: true })).toHaveCount(1);
  await expect(list.getByText("1 import is not held.")).toBeVisible();
});

test("a catalog that maps an import to a file with an unrelated name resolves it, and the plan names the path", async ({ page }) => {
  const fake = new FakeService();
  const ws = await importingWorkspace(page, fake, [IMPORT_A]);
  await page.getByRole("button", { name: "Import ontologies" }).click();
  const dialog = page.getByRole("dialog", { name: "Import ontologies" });
  await dialog.getByLabel("Files", { exact: true }).setInputFiles([
    { name: "file-7.ttl", ...ontology(IMPORT_A) },
    { name: "catalog-v001.xml", ...catalog({ [IMPORT_A]: "file-7.ttl" }) },
  ]);
  await dialog.getByRole("button", { name: "Show the plan" }).click();
  const row = dialog.getByRole("table", { name: "Import plan" }).getByRole("row", { name: /ont\/a/ });
  await expect(row).toContainText("from the catalog");
  await expect(row).toContainText("file-7.ttl");
  await expect(dialog.getByLabel("Problems with the plan")).toHaveCount(0);
  await dialog.getByRole("button", { name: "Hold 1 import" }).click();
  await expect(dialog).toHaveCount(0);
  expect(fake.workspaces.get(ws)!.imports.map((i) => i.label)).toEqual([IMPORT_A]);
  await expect(page.getByRole("region", { name: "Ontologies" }).getByText("missing", { exact: true })).toHaveCount(0);
});

test("a fence job that fails holds nothing, names the file and keeps the dialog open", async ({ page }) => {
  const fake = new FakeService();
  const ws = await importingWorkspace(page, fake, [IMPORT_A, IMPORT_B]);
  await page.getByRole("button", { name: "Import ontologies" }).click();
  const dialog = page.getByRole("dialog", { name: "Import ontologies" });
  await dialog.getByLabel("Files", { exact: true }).setInputFiles([
    { name: "a.ttl", ...ontology(IMPORT_A) },
    { name: "broken.ttl", mimeType: "text/turtle", buffer: Buffer.from("this is { not turtle") },
    { name: "catalog-v001.xml", ...catalog({ [IMPORT_B]: "broken.ttl" }) },
  ]);
  await dialog.getByRole("button", { name: "Show the plan" }).click();
  await expect(dialog.getByRole("status")).toHaveText("2 to hold now, 0 already held, 0 missing.");
  await dialog.getByRole("button", { name: "Hold 2 imports" }).click();

  const table = dialog.getByRole("table", { name: "Documents being held" });
  await expect(table.getByRole("row", { name: /broken\.ttl/ })).toContainText("failed");
  await expect(table.getByRole("row", { name: /a\.ttl/ })).toContainText(/digested|failed/);
  await expect(dialog.getByRole("alert")).toContainText("nothing was held");
  await expect(dialog).toBeVisible();
  expect(fake.holds).toHaveLength(0);
  expect(fake.workspaces.get(ws)!.imports).toHaveLength(0);
  await expect(page.getByRole("region", { name: "Ontologies" }).getByText("missing", { exact: true })).toHaveCount(2);
  await dialog.getByRole("button", { name: "Back to the plan" }).click();
  await expect(dialog.getByRole("button", { name: "Hold 2 imports" })).toBeEnabled();
});

test("an import only LATTICE's documents give is resolved with no file given, and confirming holds it and the one it imports", async ({ page }) => {
  const fake = new FakeService();
  const ws = await importingWorkspace(page, fake, [STAGED_FIRST]);
  const list = page.getByRole("region", { name: "Ontologies" });
  await expect(list.getByText("missing", { exact: true })).toHaveCount(1);

  await page.getByRole("button", { name: "Import ontologies" }).click();
  const dialog = page.getByRole("dialog", { name: "Import ontologies" });
  await dialog.getByRole("button", { name: "Show the plan" }).click();

  const plan = dialog.getByRole("table", { name: "Import plan" });
  await expect(plan.getByRole("row")).toHaveCount(3);
  await expect(plan.getByRole("row", { name: /^example\.org\/lattice\/staged\/alpha/ })).toContainText("from LATTICE's documents");
  await expect(plan.getByRole("row", { name: /^example\.org\/lattice\/staged\/beta/ })).toContainText("from LATTICE's documents");
  await expect(dialog.getByRole("status")).toHaveText("2 to hold now, 0 already held, 0 missing.");
  expect(fake.holds).toHaveLength(0);

  await dialog.getByRole("button", { name: "Hold 2 imports" }).click();
  await expect(dialog).toHaveCount(0);
  expect(fake.holds).toHaveLength(1);
  expect(fake.holds[0].labels.sort()).toEqual([STAGED_FIRST, STAGED_SECOND]);
  expect(fake.workspaces.get(ws)!.imports.map((i) => i.ontology).sort()).toEqual([STAGED_FIRST, STAGED_SECOND]);
  await expect(list.getByText("held", { exact: true })).toHaveCount(2);
  await expect(list.getByText("missing", { exact: true })).toHaveCount(0);
});

test("the import graph draws the workspace's ontology, a held import and a missing import, and hides the controls of the classes view", async ({ page }) => {
  const fake = new FakeService();
  await importingWorkspace(page, fake, [IMPORT_A, IMPORT_B]);
  await page.getByRole("button", { name: "Import ontologies" }).click();
  const dialog = page.getByRole("dialog", { name: "Import ontologies" });
  await dialog.getByLabel("Files", { exact: true }).setInputFiles([{ name: "a.ttl", ...ontology(IMPORT_A) }]);
  await dialog.getByRole("button", { name: "Show the plan" }).click();
  await dialog.getByRole("button", { name: "Hold 1 import" }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Ontologies" }).getByText("held", { exact: true })).toHaveCount(1);

  await page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Diagram" }).click();
  const diagram = page.getByRole("region", { name: "Ontology diagram" });
  await expect(diagram.getByLabel("Include shapes")).toBeVisible();
  await expect(diagram.getByLabel("Hops around the selected class")).toBeVisible();
  await diagram.getByRole("group", { name: "Ontology view" }).getByRole("button", { name: "Import graph" }).click();

  const nodes = diagram.locator(".react-flow__node-imp");
  await expect(nodes).toHaveCount(3);
  await expect(nodes.filter({ hasText: "workspace ontology" })).toContainText("example.org/ont/base");
  await expect(nodes.filter({ hasText: "held import" })).toContainText("example.org/ont/a");
  await expect(nodes.filter({ hasText: "missing import" })).toContainText("example.org/ont/b");
  await expect(diagram.getByRole("status")).toHaveText("1 ontology of the workspace, 1 import held, 1 missing, 0 schemes.");
  // The base ontology imports both, so two solid edges are drawn and none is derived.
  await expect(diagram.locator(".react-flow__edge title").filter({ hasText: "imports" })).toHaveCount(2);
  await expect(diagram.locator(".react-flow__edge title").filter({ hasText: "Derived from the terms used" })).toHaveCount(0);
  // The shapes and hops controls belong to the classes view.
  await expect(diagram.getByLabel("Include shapes")).toHaveCount(0);
  await expect(diagram.getByLabel("Hops around the selected class")).toHaveCount(0);

  // A click on the missing import opens the import dialog.
  await nodes.filter({ hasText: "missing import" }).click();
  await expect(page.getByRole("dialog", { name: "Import ontologies" })).toBeVisible();
});

// --- What the canvas kit does when a node is dragged, a page is reloaded, a link is dropped or a menu item is chosen (SVA-O5) ---

interface Xy {
  x: number;
  y: number;
}

const centreOf = async (target: Locator): Promise<Xy> => {
  const box = (await target.boundingBox())!;
  return { x: box.x + box.width / 2, y: box.y + box.height / 2 };
};

/** A drag with the mouse in steps, since React Flow starts a drag or a connection only from real pointer movement. `held` runs before the button is released. */
async function dragMouse(page: Page, from: Xy, to: Xy, held?: () => Promise<void>): Promise<void> {
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move((from.x + to.x) / 2, (from.y + to.y) / 2, { steps: 6 });
  await page.mouse.move(to.x, to.y, { steps: 12 });
  await held?.();
  await page.mouse.up();
}

/** A node's place in the flow, from its transform, which does not change with the zoom or the pane. */
const flowPlace = (node: Locator): Promise<Xy> =>
  node.evaluate((el) => {
    const m = /translate\((-?[\d.e+-]+)px,\s*(-?[\d.e+-]+)px\)/.exec((el as HTMLElement).style.transform);
    return { x: Number(m![1]), y: Number(m![2]) };
  });

/** The end of an edge's drawn path on the screen, from its start or from its end. */
const pathEnd = (edge: Locator, end: "start" | "end"): Promise<Xy> =>
  edge.locator("path.react-flow__edge-path").evaluate((p, which) => {
    const path = p as SVGPathElement;
    const at = path.getPointAtLength(which === "end" ? path.getTotalLength() : 0);
    const m = path.getScreenCTM()!;
    return { x: m.a * at.x + m.c * at.y + m.e, y: m.b * at.x + m.d * at.y + m.f };
  }, end);

const pathOf = (edge: Locator): Promise<string | null> => edge.locator("path.react-flow__edge-path").getAttribute("d");

/** How far a point is from a box, zero within it. */
const distanceTo = (p: Xy, box: { x: number; y: number; width: number; height: number }) =>
  Math.hypot(Math.max(box.x - p.x, 0, p.x - (box.x + box.width)), Math.max(box.y - p.y, 0, p.y - (box.y + box.height)));

/** A point on the screen that lies on the edge's own path and on nothing else, found where no node or label covers it. */
const pointOnEdge = async (page: Page, id: string): Promise<Xy> => {
  await page.locator(".react-flow__pane").scrollIntoViewIfNeeded();
  return page.evaluate((edgeId) => {
    const group = [...document.querySelectorAll(".react-flow__edge")].find((e) => e.getAttribute("data-id") === edgeId)!;
    const path = group.querySelector("path.react-flow__edge-path") as SVGPathElement;
    const length = path.getTotalLength();
    const m = path.getScreenCTM()!;
    for (const t of [0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8, 0.1, 0.9]) {
      const at = path.getPointAtLength(length * t);
      const x = m.a * at.x + m.c * at.y + m.e;
      const y = m.b * at.x + m.d * at.y + m.f;
      if (document.elementFromPoint(x, y)?.closest(".react-flow__edge") === group) return { x, y };
    }
    throw new Error(`no free point on the edge ${edgeId}`);
  }, id);
};

/** Answers the next dialog of the page and keeps what it said. */
function answerNext(page: Page, answer: string | false): { message: string } {
  const seen = { message: "" };
  page.once("dialog", async (dialog) => {
    seen.message = dialog.message();
    await (answer === false ? dialog.dismiss() : dialog.accept(answer || undefined));
  });
  return seen;
}

async function openDiagramOfFacility(page: Page, fake: FakeService): Promise<Locator> {
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Facility agreement/ }).click();
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  const ws = [...fake.workspaces.keys()][0];
  await page.goto(`/#/w/${ws}/baseline`);
  return showDiagram(page);
}

async function showDiagram(page: Page): Promise<Locator> {
  await page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Diagram" }).click();
  const diagram = page.getByRole("region", { name: "Ontology diagram" });
  await expect(diagram.locator(".react-flow__node-cls").first()).toBeVisible();
  return diagram;
}

test("a dragged class takes its edges and their labels with it, and the edges still end on it", async ({ page }) => {
  const fake = new FakeService();
  const diagram = await openDiagramOfFacility(page, fake);
  const facility = diagram.locator(".react-flow__node-cls").filter({ hasText: "Facility" });
  // Facility is the source of four links and the target of one, besides the loop on itself.
  const links = [
    { title: "ex:drawnUnder, from Drawdown to Facility", end: "end" as const },
    { title: "ex:borrower, from Facility to Borrower", end: "start" as const },
    { title: "ex:arrangedBy, from Facility to Branch", end: "start" as const },
    { title: "ex:hasDrawdown, from Facility to Drawdown", end: "start" as const },
    { title: "ex:lender, from Facility to Lender", end: "start" as const },
  ];
  const edge = (title: string) => diagram.locator(".react-flow__edge").filter({ has: page.locator("title", { hasText: title }) });
  const label = (title: string) => diagram.locator(`.onto-edge-label[title="${title}"]`);
  const before = await Promise.all(links.map(async (l) => ({ d: await pathOf(edge(l.title)), at: await label(l.title).getAttribute("style") })));
  const start = await centreOf(facility);
  const placeBefore = await flowPlace(facility);

  // The edges and labels follow the class while the button is held, not only once it is let go.
  const follows = async () => {
    await expect.poll(async () => (await flowPlace(facility)).y).toBeGreaterThan(placeBefore.y + 100);
    for (const [n, l] of links.entries()) {
      await expect.poll(() => pathOf(edge(l.title)), `the path of ${l.title}`).not.toBe(before[n].d);
      await expect.poll(() => label(l.title).getAttribute("style"), `the label of ${l.title}`).not.toBe(before[n].at);
      // The edge still meets the class, whichever end of the edge it is.
      const box = (await facility.boundingBox())!;
      const end = await pathEnd(edge(l.title), l.end);
      expect(distanceTo(end, box), `${l.title} ends ${distanceTo(end, box)} px from the dragged class`).toBeLessThanOrEqual(3);
    }
  };
  await dragMouse(page, start, { x: start.x + 40, y: start.y + 120 }, follows);
  await follows();
  const moved = (await facility.boundingBox())!;
  expect(moved.y - (start.y - moved.height / 2)).toBeGreaterThan(40);
});

test("a class the author moved stays where it was left after the page is loaded again", async ({ page }) => {
  const fake = new FakeService();
  let diagram = await openDiagramOfFacility(page, fake);
  const facility = () => diagram.locator(".react-flow__node-cls").filter({ hasText: "Facility" });
  const laid = await flowPlace(facility());
  const start = await centreOf(facility());
  await dragMouse(page, start, { x: start.x - 60, y: start.y + 90 });
  await expect.poll(async () => (await flowPlace(facility())).y).toBeGreaterThan(laid.y + 50);
  const left = await flowPlace(facility());
  expect(left.x).toBeLessThan(laid.x - 40);

  await page.reload();
  await expect(page.getByRole("group", { name: "Detail pane" })).toBeVisible();
  diagram = await showDiagram(page);
  await expect.poll(() => flowPlace(facility())).toEqual({ x: expect.closeTo(left.x, 0), y: expect.closeTo(left.y, 0) });
  // The classes nobody moved are where the layout puts them.
  expect(await flowPlace(diagram.locator(".react-flow__node-cls").filter({ hasText: "Drawdown" }))).toEqual({ x: 0, y: 0 });
});

const PROBE = "https://example.org/probe/map#";
const PROBE_SOURCE = "https://example.org/probe/src#";
const PROBE_TTL = `@prefix mork: <http://www.nebularis.org/ontologies/Mork#> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix m: <${PROBE}> . @prefix src: <${PROBE_SOURCE}> .
m:Scheme a mork:MappingScheme ; rdfs:label "Probe scheme" .
src:Policy a mork:DataConcept ; rdfs:label "Policy source" ; mork:path "$.policy" .
src:Cover a mork:DataConcept ; rdfs:label "Cover source" ; mork:path "$.cover" .
m:Policy a mork:Datum ; rdfs:label "Policy" ; mork:mappingScheme m:Scheme ; mork:mappingFor src:Policy .
m:Cover a mork:Datum ; rdfs:label "Cover" ; mork:compositeBroaderMapping m:Policy ; mork:mappingScheme m:Scheme ; mork:mappingFor src:Cover .
m:Holder a mork:DataMapping ; rdfs:label "Holder" ; mork:compositeBroaderMapping m:Policy ; mork:mappingScheme m:Scheme .
m:Status a mork:DataMapping ; rdfs:label "Status" ; mork:mappingScheme m:Scheme ; mork:templateMapping m:Template .
m:Template a mork:DataMapping ; rdfs:label "Template" ; mork:mappingScheme m:Scheme .
`;

/** A workspace holding one mapping scheme with source concepts, a parent link, a template link and a source link, open on its canvas. */
async function openMappingProbe(page: Page, fake: FakeService): Promise<void> {
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Your own Turtle/ }).click();
  await page.locator("#ws-name").fill("Probe");
  await page.locator('input[type="file"]').setInputFiles({ name: "probe.ttl", mimeType: "text/turtle", buffer: Buffer.from(PROBE_TTL) });
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await page.goto(`/#/w/${[...fake.workspaces.keys()][0]}/mapping`);
  await showMappingCanvas(page);
}

async function showMappingCanvas(page: Page): Promise<void> {
  await page.getByRole("group", { name: "Drawing" }).getByRole("button", { name: "Canvas" }).click();
  await expect(page.locator(".react-flow__node-mapping").first()).toBeVisible();
}

const mappingNode = (page: Page, name: string) => page.locator(".react-flow__node-mapping").filter({ has: page.getByText(name, { exact: true }) });
const sourceNode = (page: Page, name: string) => page.locator(".react-flow__node-source").filter({ hasText: name });
const linkEdge = (page: Page, kind: "parent" | "template" | "source", node: string) => page.locator(`.react-flow__edge[data-id="${kind}|${PROBE}${node}"]`);
const ofEdge = (edge: Locator) => edge.getAttribute("aria-label");
const connect = async (page: Page, from: Locator, to: Locator) => dragMouse(page, await centreOf(from.locator(".react-flow__handle.source")), await centreOf(to.locator(".react-flow__handle.target")));
const savedMapping = (fake: FakeService) => fake.saves.filter((s) => s.name === "mapping").pop()?.body ?? "";
const occurrences = (text: string, of: string) => text.split(of).length - 1;

test("a mapping the author moved stays where it was left after a reload, and laying the scheme out again puts it back, for good", async ({ page }) => {
  const fake = new FakeService();
  await openMappingProbe(page, fake);
  const holder = mappingNode(page, "Holder");
  const laid = await flowPlace(holder);
  const start = await centreOf(holder);
  await dragMouse(page, start, { x: start.x + 30, y: start.y + 110 });
  await expect.poll(async () => (await flowPlace(holder)).y).toBeGreaterThan(laid.y + 100);
  const left = await flowPlace(holder);

  await page.reload();
  await showMappingCanvas(page);
  await expect.poll(() => flowPlace(holder)).toEqual({ x: expect.closeTo(left.x, 0), y: expect.closeTo(left.y, 0) });

  await page.locator(".react-flow__pane").click({ button: "right", position: { x: 5, y: 5 } });
  await page.getByRole("menu").getByRole("menuitem", { name: "Lay the scheme out again" }).click();
  await expect.poll(() => flowPlace(holder)).toEqual({ x: expect.closeTo(laid.x, 0), y: expect.closeTo(laid.y, 0) });

  // What was forgotten stays forgotten on the next visit.
  await page.reload();
  await showMappingCanvas(page);
  await expect.poll(() => flowPlace(holder)).toEqual({ x: expect.closeTo(laid.x, 0), y: expect.closeTo(laid.y, 0) });
});

test("a link dropped on a mapping makes it a child or gives it a source, a link that would make a cycle is refused, and undo takes each back", async ({ page }) => {
  const fake = new FakeService();
  await openMappingProbe(page, fake);
  const undo = page.getByRole("button", { name: "Undo" });
  const policy = mappingNode(page, "Policy");
  const cover = mappingNode(page, "Cover");
  const holder = mappingNode(page, "Holder");
  const status = mappingNode(page, "Status");
  await expect(linkEdge(page, "parent", "Status")).toHaveCount(0);
  const parents = occurrences(PROBE_TTL, "compositeBroaderMapping");

  // From a mapping to a mapping makes the first the second's parent.
  await connect(page, policy, status);
  await expect(linkEdge(page, "parent", "Status")).toHaveCount(1);
  expect(await ofEdge(linkEdge(page, "parent", "Status"))).toBe(`Edge from ${PROBE}Policy to ${PROBE}Status`);
  await page.keyboard.press("ControlOrMeta+s");
  await expect.poll(() => occurrences(savedMapping(fake), "compositeBroaderMapping")).toBe(parents + 1);
  await undo.click();
  await expect(linkEdge(page, "parent", "Status")).toHaveCount(0);

  // A mapping has one parent, so a link to one that has a parent moves it.
  expect(await ofEdge(linkEdge(page, "parent", "Holder"))).toBe(`Edge from ${PROBE}Policy to ${PROBE}Holder`);
  await connect(page, cover, holder);
  await expect.poll(() => ofEdge(linkEdge(page, "parent", "Holder"))).toBe(`Edge from ${PROBE}Cover to ${PROBE}Holder`);
  await expect(page.locator('.react-flow__edge[data-id^="parent|"]')).toHaveCount(2);
  await undo.click();
  await expect.poll(() => ofEdge(linkEdge(page, "parent", "Holder"))).toBe(`Edge from ${PROBE}Policy to ${PROBE}Holder`);

  // From a source concept to a mapping says what the mapping maps for.
  await expect(linkEdge(page, "source", "Status")).toHaveCount(0);
  await connect(page, sourceNode(page, "Cover source"), status);
  await expect(linkEdge(page, "source", "Status")).toHaveCount(1);
  expect(await ofEdge(linkEdge(page, "source", "Status"))).toBe(`Edge from ${PROBE_SOURCE}Cover to ${PROBE}Status`);
  await page.keyboard.press("ControlOrMeta+s");
  await expect.poll(() => occurrences(savedMapping(fake), "mappingFor")).toBe(occurrences(PROBE_TTL, "mappingFor") + 1);
  await undo.click();
  await expect(linkEdge(page, "source", "Status")).toHaveCount(0);

  // A link that would make Policy a child of its own child changes nothing, and neither does one dropped on the empty pane.
  const drawn = await page.locator(".react-flow__edge").count();
  await connect(page, cover, policy);
  const pane = (await page.locator(".react-flow__pane").boundingBox())!;
  await dragMouse(page, await centreOf(policy.locator(".react-flow__handle.source")), { x: pane.x + 30, y: pane.y + 30 });
  await expect(linkEdge(page, "parent", "Policy")).toHaveCount(0);
  expect(await ofEdge(linkEdge(page, "parent", "Cover"))).toBe(`Edge from ${PROBE}Policy to ${PROBE}Cover`);
  await expect(page.locator(".react-flow__edge")).toHaveCount(drawn);
});

test("each item of the mapping canvas's menus does what it says", async ({ page }) => {
  const fake = new FakeService();
  await openMappingProbe(page, fake);
  const undo = page.getByRole("button", { name: "Undo" });
  const menu = page.getByRole("menu");
  const item = (name: string) => menu.getByRole("menuitem", { name });
  const policy = mappingNode(page, "Policy");
  const cover = mappingNode(page, "Cover");
  const holder = mappingNode(page, "Holder");
  const mappings = page.locator(".react-flow__node-mapping");
  const parents = page.locator('.react-flow__edge[data-id^="parent|"]');
  await expect(mappings).toHaveCount(5);
  await expect(parents).toHaveCount(2);

  // The menu of a mapping with no parent has no item to detach it, and "Open in the editor" opens its card.
  await policy.click({ button: "right" });
  await expect(menu.getByRole("menuitem")).toHaveText(["Open in the editor", "Add a child datum", "Add a child data mapping", "Delete the mapping"]);
  await item("Open in the editor").click();
  await expect(page.getByRole("region", { name: "Mapping Policy" })).toBeVisible();

  // Deleting asks first, takes the mapping and the links to and from it away, and undo brings them back.
  const asking = answerNext(page, false);
  await policy.click({ button: "right" });
  await item("Delete the mapping").click();
  await expect.poll(() => asking.message).toContain("Delete Policy?");
  await expect(policy).toBeVisible();
  await expect(mappings).toHaveCount(5);
  answerNext(page, "");
  await policy.click({ button: "right" });
  await item("Delete the mapping").click();
  await expect(policy).toHaveCount(0);
  await expect(mappings).toHaveCount(4);
  await expect(linkEdge(page, "source", "Policy")).toHaveCount(0);
  await expect(parents).toHaveCount(0);
  await expect(cover).toBeVisible();
  await undo.click();
  await expect(policy).toBeVisible();
  await expect(mappings).toHaveCount(5);
  await expect(linkEdge(page, "source", "Policy")).toHaveCount(1);
  await expect(parents).toHaveCount(2);

  // An edge's menu removes that link and no other.
  const removeFrom = async (edgeId: string, name: string, on?: Locator) => {
    if (on) await on.click({ button: "right" });
    else await page.mouse.click(...(Object.values(await pointOnEdge(page, edgeId)) as [number, number]), { button: "right" });
    await expect(menu.getByRole("menuitem")).toHaveText([name]);
    await item(name).click();
  };
  await removeFrom(`source|${PROBE}Policy`, "Remove the source link");
  await expect(linkEdge(page, "source", "Policy")).toHaveCount(0);
  await expect(linkEdge(page, "source", "Cover")).toHaveCount(1);
  // The edge between the two is short and its label covers it, so the menu is opened on the label.
  await removeFrom(`template|${PROBE}Status`, "Remove the template link", page.locator(".canvas-edge-label").filter({ hasText: "template" }));
  await expect(linkEdge(page, "template", "Status")).toHaveCount(0);
  await expect(mappingNode(page, "Template")).toBeVisible();
  await removeFrom(`parent|${PROBE}Holder`, "Remove the parent link");
  await expect(linkEdge(page, "parent", "Holder")).toHaveCount(0);
  await expect(holder).toBeVisible();
  await expect(parents).toHaveCount(1);

  // Detaching keeps the mapping and takes its parent link away.
  await cover.click({ button: "right" });
  await item("Detach from its parent").click();
  await expect(linkEdge(page, "parent", "Cover")).toHaveCount(0);
  await expect(cover).toBeVisible();
  await expect(parents).toHaveCount(0);

  // A child data mapping and a child datum are named by the author, a cancelled name adds nothing, and each is drawn under its parent.
  // A new node is laid out where the layout puts it, which may be over one that kept its place, so the nodes to click are used first.
  let asked = answerNext(page, false);
  await cover.click({ button: "right" });
  await item("Add a child datum").click();
  await expect.poll(() => asked.message).toBe("Name the new datum");
  await expect(mappings).toHaveCount(5);

  asked = answerNext(page, "Premium");
  await policy.click({ button: "right" });
  await item("Add a child datum").click();
  await expect(mappings).toHaveCount(6);
  expect(asked.message).toBe("Name the new datum");
  await expect(mappingNode(page, "Premium")).toBeVisible();
  await expect(parents).toHaveCount(1);
  await expect(page.locator(`.react-flow__edge[aria-label^="Edge from ${PROBE}Policy to "]`)).toHaveCount(1);

  asked = answerNext(page, "Rate");
  await cover.click({ button: "right" });
  await item("Add a child data mapping").click();
  await expect(mappings).toHaveCount(7);
  expect(asked.message).toBe("Name the new data mapping");
  await expect(mappingNode(page, "Rate")).toBeVisible();
  await expect(parents).toHaveCount(2);
  await expect(page.locator(`.react-flow__edge[aria-label^="Edge from ${PROBE}Cover to "]`)).toHaveCount(1);

  // The pane's menu adds a root datum, which has no parent, and lays the scheme out again.
  const before = await mappings.count();
  asked = answerNext(page, "Second root");
  await page.locator(".react-flow__pane").click({ button: "right", position: { x: 5, y: 5 } });
  await item("Add a root datum").click();
  await expect(mappings).toHaveCount(before + 1);
  expect(asked.message).toBe("Name the new datum");
  await expect(mappingNode(page, "Second root")).toBeVisible();
  await expect(parents).toHaveCount(2);
  const laid = await flowPlace(policy);
  const start = await centreOf(policy);
  await dragMouse(page, start, { x: start.x + 20, y: start.y + 90 });
  await expect.poll(async () => (await flowPlace(policy)).y).toBeGreaterThan(laid.y + 60);
  const dragged = await flowPlace(policy);
  await page.locator(".react-flow__pane").click({ button: "right", position: { x: 5, y: 5 } });
  await item("Lay the scheme out again").click();
  await expect.poll(() => flowPlace(policy)).not.toEqual(dragged);
  // Every mapping is where the layout puts it, so no two share a place, as a node laid out over another did before.
  const places = await mappings.evaluateAll((els) => els.map((e) => (e as HTMLElement).style.transform));
  expect(new Set(places).size).toBe(places.length);
});

// --- A node an edit adds is drawn clear of the nodes that kept their places, and a label never hides the edge it names (SVA-O7) ---

/** The boxes on the screen of every mapping node, by the name it shows. */
const mappingBoxes = (page: Page) =>
  page.locator(".react-flow__node-mapping").evaluateAll((els) =>
    els.map((el) => {
      const r = el.getBoundingClientRect();
      return { name: (el.textContent ?? "").trim().slice(0, 20), x: r.x, y: r.y, width: r.width, height: r.height };
    }),
  );

/** The pairs of boxes that share an area, by name. */
const overlapping = (boxes: { name: string; x: number; y: number; width: number; height: number }[]) =>
  boxes.flatMap((a, i) => boxes.slice(i + 1).filter((b) => Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x) > 0.5 && Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y) > 0.5).map((b) => `${a.name} over ${b.name}`));

test("a node an edit adds is drawn clear of every mapping that kept its place, so each can be clicked", async ({ page }) => {
  const fake = new FakeService();
  await openMappingProbe(page, fake);
  const menu = page.getByRole("menu");
  const item = (name: string) => menu.getByRole("menuitem", { name });
  const mappings = page.locator(".react-flow__node-mapping");
  const cover = mappingNode(page, "Cover");
  const policy = mappingNode(page, "Policy");
  await expect(mappings).toHaveCount(5);
  expect(await overlapping(await mappingBoxes(page))).toEqual([]);

  // The sequence SVA-O5 met it in. A mapping is detached, and children are added under its old parent and under it.
  await cover.click({ button: "right" });
  await item("Detach from its parent").click();
  await expect(linkEdge(page, "parent", "Cover")).toHaveCount(0);
  answerNext(page, "Premium");
  await policy.click({ button: "right" });
  await item("Add a child datum").click();
  await expect(mappings).toHaveCount(6);
  answerNext(page, "Rate");
  await cover.click({ button: "right" });
  await item("Add a child data mapping").click();
  await expect(mappings).toHaveCount(7);
  answerNext(page, "Second root");
  await page.locator(".react-flow__pane").click({ button: "right", position: { x: 5, y: 5 } });
  await item("Add a root datum").click();
  await expect(mappings).toHaveCount(8);

  // No two nodes share an area, and each, the one a new node would have covered included, opens its card on a click.
  expect(await overlapping(await mappingBoxes(page))).toEqual([]);
  for (const name of ["Policy", "Cover", "Holder", "Status", "Template", "Premium", "Rate", "Second root"]) {
    await mappingNode(page, name).click();
    await expect(page.getByRole("region", { name: `Mapping ${name}` })).toBeVisible();
  }

  // Laying the scheme out again still gives every node the layout's own place, and none shares it.
  const places = await mappings.evaluateAll((els) => els.map((e) => (e as HTMLElement).style.transform));
  await page.locator(".react-flow__pane").click({ button: "right", position: { x: 5, y: 5 } });
  await item("Lay the scheme out again").click();
  expect(await overlapping(await mappingBoxes(page))).toEqual([]);
  expect(new Set(await mappings.evaluateAll((els) => els.map((e) => (e as HTMLElement).style.transform))).size).toBe(places.length);
});

test("the template edge of a mapping is seen beside its label and opens its menu where it is drawn", async ({ page }) => {
  const fake = new FakeService();
  await openMappingProbe(page, fake);
  const edgeId = `template|${PROBE}Status`;
  const label = page.locator(".canvas-edge-label").filter({ hasText: "template" });
  const line = linkEdge(page, "template", "Status").locator("path.react-flow__edge-path");
  await expect(label).toBeVisible();
  const own = (await line.boundingBox())!;
  const text = (await label.boundingBox())!;
  // The label is clear of the edge's own path, the edge being the shorter of the two along its direction.
  expect(Math.min(own.x + own.width, text.x + text.width) - Math.max(own.x, text.x) > 0 && Math.min(own.y + own.height, text.y + text.height) - Math.max(own.y, text.y) > 0).toBe(false);
  expect(Math.max(own.width, own.height)).toBeLessThan(text.height);

  // A right click on the line itself opens the edge's menu, which the label no longer covers.
  const at = await pointOnEdge(page, edgeId);
  expect(at.x < text.x || at.x > text.x + text.width || at.y < text.y || at.y > text.y + text.height).toBe(true);
  await page.mouse.click(at.x, at.y, { button: "right" });
  await expect(page.getByRole("menu").getByRole("menuitem")).toHaveText(["Remove the template link"]);
});

// SVA-B2c. The baseline is validated live, as a configuration part is, and its findings reach the problems drawer.
const problems = (page: Page) => page.getByRole("region", { name: "Problems" });
const baselineBadge = (page: Page) => page.getByRole("navigation", { name: "Workspace" }).getByRole("link", { name: /^Baseline/ }).locator(".dot.warn");
const baselineValidations = (fake: FakeService) => [...fake.jobs.entries()].filter(([, j]) => j.kind === "validate" && j.target === "baseline");

async function holdImportA(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Import ontologies" }).click();
  const dialog = page.getByRole("dialog", { name: "Import ontologies" });
  await dialog.getByLabel("Files", { exact: true }).setInputFiles([{ name: "a.ttl", ...ontology(IMPORT_A) }]);
  await dialog.getByRole("button", { name: "Show the plan" }).click();
  await dialog.getByRole("button", { name: "Hold 1 import" }).click();
  await expect(dialog).toHaveCount(0);
}

test("an import no held document declares is a warning in the problems drawer and on the Baseline entry, and choosing it opens the Baseline view", async ({ page }) => {
  const fake = new FakeService();
  const ws = await importingWorkspace(page, fake, [IMPORT_A]);
  await page.goto(`/#/w/${ws}/overview`);
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  const finding = problems(page).getByRole("listitem").filter({ hasText: "ImportNotHeld" });
  await expect(finding).toHaveCount(1);
  await expect(finding).toContainText(`imports ${IMPORT_A}`);
  await expect(baselineBadge(page)).toHaveCount(1);
  expect(baselineValidations(fake).map(([, j]) => j.body)[0]).toMatch(/owl:imports\s+ont:a/);
  // a warning is a warning in the pill too, never a violation
  await expect(page.getByRole("status")).toHaveText("1 warning");

  await finding.click();
  await expect(page).toHaveURL(new RegExp(`/w/${ws}/baseline$`));
  await expect(page.getByRole("region", { name: "Ontologies" })).toBeVisible();
  // the view's own list says it once, and the finding is not added to the view
  await expect(page.getByRole("region", { name: "Ontologies" }).getByText("missing", { exact: true })).toHaveCount(1);
  await expect(page.getByRole("main").getByText("ImportNotHeld")).toHaveCount(0);
});

test("holding the import takes the warning from the drawer with no edit of the baseline, and releasing it brings the warning back", async ({ page }) => {
  const fake = new FakeService();
  const ws = await importingWorkspace(page, fake, [IMPORT_A]);
  await expect(problems(page).getByText("ImportNotHeld")).toHaveCount(1);
  await expect(baselineBadge(page)).toHaveCount(1);
  const before = baselineValidations(fake).length;

  await holdImportA(page);
  await expect(problems(page).getByText("No problems in any part of the workspace.")).toBeVisible();
  await expect(problems(page).getByText("ImportNotHeld")).toHaveCount(0);
  await expect(baselineBadge(page)).toHaveCount(0);
  expect(baselineValidations(fake).length).toBeGreaterThan(before);
  expect(fake.saves.filter((s) => s.name === "baseline")).toHaveLength(0);

  // the Publish view lists the held imports with a way to release each
  await page.goto(`/#/w/${ws}/publish`);
  await page.getByRole("button", { name: `Release ${IMPORT_A}` }).click();
  await expect(problems(page).getByText("ImportNotHeld")).toHaveCount(1);
  await expect(baselineBadge(page)).toHaveCount(1);
  expect(fake.workspaces.get(ws)!.imports).toHaveLength(0);
  expect(fake.saves.filter((s) => s.name === "baseline")).toHaveLength(0);
});

test("leaving a workspace ends the waiting on the baseline's validation, and coming back leaves no more of them than before", async ({ page }) => {
  const fake = new FakeService();
  fake.hold.add("validate:baseline");
  const ws = await importingWorkspace(page, fake, [IMPORT_A]);
  const open = () => baselineValidations(fake).filter(([id]) => !fake.deletedJobs.includes(id)).length;
  await page.waitForTimeout(1500);
  const first = open();
  expect(first).toBe(1);
  await page.goto("/#/");
  await page.waitForTimeout(500);
  expect(open()).toBe(0);
  await page.goto(`/#/w/${ws}`);
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await page.waitForTimeout(1500);
  expect(open()).toBe(first);
});

// --- The library sample's import graph, the import dialog's drop area, the graphs the state keeps, and the baseline's validation (SVA-B5) ---

async function libraryWorkspace(page: Page, fake: FakeService): Promise<string> {
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Library, with imports/ }).click();
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  const ws = [...fake.workspaces.keys()][0];
  await page.goto(`/#/w/${ws}/baseline`);
  return ws;
}

/** Holds what the baseline imports from LATTICE's documents, with no file given. */
async function holdFromLattice(page: Page, count: number): Promise<void> {
  await page.getByRole("button", { name: "Import ontologies" }).click();
  const dialog = page.getByRole("dialog", { name: "Import ontologies" });
  await dialog.getByRole("button", { name: "Show the plan" }).click();
  await dialog.getByRole("button", { name: `Hold ${count} imports` }).click();
  await expect(dialog).toHaveCount(0);
}

test("the library sample's import graph draws a stated import, a binds edge and an edge derived from a term the baseline uses", async ({ page }) => {
  const fake = new FakeService();
  await libraryWorkspace(page, fake);
  await holdFromLattice(page, 2);
  await expect(page.getByRole("region", { name: "Ontologies" }).getByText("held", { exact: true })).toHaveCount(2);

  await page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Diagram" }).click();
  const diagram = page.getByRole("region", { name: "Ontology diagram" });
  await diagram.getByRole("group", { name: "Ontology view" }).getByRole("button", { name: "Import graph" }).click();

  const nodes = diagram.locator(".react-flow__node-imp");
  await expect(nodes).toHaveCount(4);
  await expect(nodes.filter({ hasText: "workspace ontology" })).toContainText("example.org/library");
  await expect(nodes.filter({ hasText: "held import" })).toHaveCount(2);
  await expect(nodes.filter({ hasText: "held import" }).filter({ hasText: "neuro-semantic/vocabulary" })).toHaveCount(1);
  await expect(nodes.filter({ hasText: "held import" }).filter({ hasText: "neuro-semantic/foundation" })).toHaveCount(1);
  await expect(diagram.getByRole("status")).toHaveText("1 ontology of the workspace, 2 imports held, 0 missing, 1 scheme.");

  const edge = (text: string) => diagram.locator(".react-flow__edge title").filter({ hasText: text });
  // Stated: the baseline imports the vocabulary layer, which imports the foundation layer. The baseline does not import the foundation layer.
  await expect(edge("imports")).toHaveCount(2);
  await expect(edge("example.org/library imports www.nebularis.org/neuro-semantic/vocabulary")).toHaveCount(1);
  await expect(edge("neuro-semantic/vocabulary imports www.nebularis.org/neuro-semantic/foundation")).toHaveCount(1);
  await expect(edge("example.org/library imports www.nebularis.org/neuro-semantic/foundation")).toHaveCount(0);
  // Stated: the scheme contract binds the scheme of the sample's own, drawn from the ontology that declares the property it constrains.
  await expect(edge("lib:SubjectContract binds Subject headings")).toHaveCount(1);
  // Derived: the baseline uses fnd:Governable, which only the foundation layer declares, and no stated edge joins the two.
  await expect(edge("Derived from the terms used")).toHaveCount(1);
  await expect(edge("Derived from the terms used")).toContainText("example.org/library uses terms of www.nebularis.org/neuro-semantic/foundation");
  await expect(diagram.locator(".react-flow__edge").filter({ has: page.locator("title", { hasText: "Derived from the terms used" }) })).toHaveCount(1);
});

test("a drop area on the import dialog adds dropped files as the inputs do, and a drop does not navigate the page", async ({ page }) => {
  const fake = new FakeService();
  await importingWorkspace(page, fake, [IMPORT_A]);
  await page.getByRole("button", { name: "Import ontologies" }).click();
  const dialog = page.getByRole("dialog", { name: "Import ontologies" });
  const area = dialog.getByRole("group", { name: "Drop area" });
  await expect(area).toContainText("Drop Turtle or RDF/XML files here, or a whole folder with its catalog.");
  const prevented = await area.evaluate((el, text) => {
    const data = new DataTransfer();
    data.items.add(new File([text], "a.ttl", { type: "text/turtle" }));
    const over = new DragEvent("dragover", { dataTransfer: data, bubbles: true, cancelable: true });
    el.dispatchEvent(over);
    const drop = new DragEvent("drop", { dataTransfer: data, bubbles: true, cancelable: true });
    el.dispatchEvent(drop);
    return [over.defaultPrevented, drop.defaultPrevented];
  }, `${OWL_HEAD}<${IMPORT_A}> a owl:Ontology .\n`);
  expect(prevented).toEqual([true, true]);
  await expect(dialog.getByRole("list", { name: "Chosen files" })).toContainText("a.ttl");
  await dialog.getByRole("button", { name: "Show the plan" }).click();
  await expect(dialog.getByRole("button", { name: "Hold 1 import" })).toBeEnabled();
});

const PINNED = "https://example.org/published/shared/rev/1-abc";
const SKOS_HEAD = "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n";

/** The pages' requests for a graph the workspace's state loads: a held import's, and a dependency's and its lineage's. */
function graphReads(page: Page): string[] {
  const seen: string[] = [];
  page.on("request", (r) => {
    const u = new URL(r.url());
    if (r.method() === "GET" && (/\/imports\/[0-9a-f]{64}$/.test(u.pathname) || u.pathname === "/api/registry/version" || u.pathname === "/api/registry/lineage")) seen.push(`${u.pathname}${u.search}`);
  });
  return seen;
}

test("the import graph shows a scheme a dependency declares, and opening the diagram asks for no graph the state already loaded", async ({ page }) => {
  const fake = new FakeService();
  fake.published.set(PINNED, `${SKOS_HEAD}<https://example.org/shared#Colours> a skos:ConceptScheme ; skos:prefLabel "Colours"@en .\n`);
  const ws = await importingWorkspace(page, fake, [IMPORT_A]);
  fake.workspaces.get(ws)!.dependsOn = [PINNED];
  const reads = graphReads(page);
  await page.reload();
  await holdImportA(page);
  await expect(page.getByRole("region", { name: "Ontologies" }).getByText("held", { exact: true })).toHaveCount(1);
  await page.waitForLoadState("networkidle");
  // The state has loaded the dependency and the held import by now.
  expect(reads.some((r) => r.startsWith("/api/registry/version"))).toBe(true);
  expect(reads.some((r) => /\/imports\//.test(r))).toBe(true);
  const before = reads.length;

  await page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Diagram" }).click();
  const diagram = page.getByRole("region", { name: "Ontology diagram" });
  await diagram.getByRole("group", { name: "Ontology view" }).getByRole("button", { name: "Import graph" }).click();
  const scheme = diagram.locator(".react-flow__node-imp").filter({ hasText: "concept scheme" });
  await expect(scheme).toHaveCount(1);
  await expect(scheme).toContainText("Colours");
  await expect(diagram.getByRole("status")).toHaveText("1 ontology of the workspace, 1 import held, 0 missing, 1 scheme.");
  await page.waitForLoadState("networkidle");
  expect(reads.length).toBe(before);
});

test("a baseline validation that is running shows as validating in the state pill, as a part's does", async ({ page }) => {
  const fake = new FakeService();
  fake.hold.add("validate:baseline");
  await importingWorkspace(page, fake, [IMPORT_A]);
  await expect(page.getByRole("status").filter({ hasText: "Validating" })).toHaveCount(1);
  await expect(page.getByRole("status").filter({ hasText: "Conforms" })).toHaveCount(0);
});

test("a baseline validation that could not run shows as unavailable in the state pill, as a part's does", async ({ page }) => {
  const fake = new FakeService();
  fake.fail.add("validate:baseline");
  await importingWorkspace(page, fake, [IMPORT_A]);
  const pill = page.getByRole("status").filter({ hasText: "Validation unavailable" });
  await expect(pill).toHaveCount(1);
  await expect(pill).toHaveAttribute("title", "The worker could not run the validation.");
});

test("the overview counts the baseline's violations with the parts'", async ({ page }) => {
  const fake = new FakeService();
  fake.baselineViolation = "The baseline declares a class twice.";
  await importingWorkspace(page, fake, [IMPORT_A]);
  await page.goto(`/#/w/${[...fake.workspaces.keys()][0]}/overview`);
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  const stat = page.locator(".stat").filter({ hasText: "violations" });
  await expect(stat).toContainText("1");
  await expect(page.getByRole("status").filter({ hasText: "1 violation" })).toHaveCount(1);
});

// --- The run pane in mapping mode's dock, on the fake service, which offers no events, so every run waits (SVA-R4) ---

/** A workspace of mapping schemes with an example sample, open on mapping mode with the dock's Sample tab showing. */
async function sampleDock(page: Page, fake: FakeService): Promise<Locator> {
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Policies from XML and JSON/ }).click();
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await page.goto(`/#/w/${[...fake.workspaces.keys()][0]}/mapping`);
  // the dock is open at this viewport's width
  await page.getByRole("tab", { name: "Sample" }).click();
  const pane = page.getByRole("region", { name: "Sample", exact: true });
  await expect(pane).toBeVisible();
  await pane.getByRole("button", { name: /^Use the XML example/ }).click();
  return pane;
}

test("the dock's Sample tab runs nothing until Run is pressed, then shows the run and its parts in order, from the compile job it names", async ({ page }) => {
  const fake = new FakeService();
  fake.runDelayMs = 400;
  const pane = await sampleDock(page, fake);
  const status = pane.getByRole("status", { name: "Sample status" });
  await expect(status).toContainText("Nothing has run yet.");
  expect(fake.runs).toHaveLength(0);
  await expect(pane.getByRole("group", { name: "Sample controls" })).toContainText("Scheme");
  await expect(pane.getByRole("group", { name: "Sample controls" })).toContainText("XML");
  await pane.getByRole("button", { name: "Run" }).click();
  await expect(status).toContainText("Running, 0 parts so far.");
  // the report and an artefact for each of the six mappings the XML scheme writes, as the Java run worker gave them for the XML example
  await expect(status).toContainText("Complete, 7 parts, conforms.");
  expect(fake.runs).toHaveLength(1);
  expect(fake.runs[0]).toMatchObject({ kind: "sample", target: "mapping", wait: true, mediaType: "application/xml" });
  await expect(status).toContainText(`Compile job ${fake.runs[0].job}`);
  const parts = pane.getByRole("list", { name: "Sample parts" }).getByRole("listitem");
  await expect(parts).toHaveCount(7);
  await expect(parts.nth(0).getByRole("region", { name: "Part 1, report" })).toContainText("sh:conforms true");
  await expect(parts.nth(1).getByRole("region", { name: "Part 2, artefact" })).toContainText("application/n-triples");
  await expect(parts.nth(1).getByRole("region", { name: "Part 2, artefact" })).toContainText("urn:example:mapping/xml#Cover");
  await expect(parts.nth(1).getByRole("region", { name: "Part 2, artefact" })).toContainText("0/Cover.nt");
  await expect(parts.nth(5).getByRole("region", { name: "Part 6, artefact" })).toContainText("0/Policy.nt");
});

test("a run the service refuses shows refused with its status and reason, and a 429's Retry-After", async ({ page }) => {
  const fake = new FakeService();
  const pane = await sampleDock(page, fake);
  const status = pane.getByRole("status", { name: "Sample status" });
  fake.runRefusal = 429;
  await pane.getByRole("button", { name: "Run" }).click();
  await expect(status).toContainText("Refused (429). refused with 429 Try again in 3 seconds.");
  fake.runRefusal = 409;
  await pane.getByRole("button", { name: "Run" }).click();
  await expect(status).toContainText("Refused (409). refused with 409");
  await expect(status).not.toContainText("Try again");
  await expect(pane.getByRole("listitem")).toHaveCount(0);
});

test("a run whose last frame is failed shows failed with the run's own message", async ({ page }) => {
  const fake = new FakeService();
  const pane = await sampleDock(page, fake);
  fake.runFailure = "The compile job could not be read, so nothing was run.";
  await pane.getByRole("button", { name: "Run" }).click();
  await expect(pane.getByRole("status", { name: "Sample status" })).toContainText("Failed. The compile job could not be read, so nothing was run.");
});

test("a run that passes its deadline shows incomplete and offers Run again, which then completes", async ({ page }) => {
  const fake = new FakeService();
  const pane = await sampleDock(page, fake);
  const status = pane.getByRole("status", { name: "Sample status" });
  fake.expiredRuns = 1;
  await pane.getByRole("button", { name: "Run", exact: true }).click();
  await expect(status).toContainText("Incomplete, the run did not finish before its deadline.");
  expect(fake.runs).toHaveLength(0);
  await status.getByRole("button", { name: "Run again" }).click();
  await expect(status).toContainText("Complete, 7 parts, conforms.");
  await expect(status.getByRole("button", { name: "Run again" })).toHaveCount(0);
  expect(fake.runs).toHaveLength(1);
});

// --- The sample pane's runs, on the fake service, which answers a run only with the frames a worker gave for that sample (SVA-M3b) ---

const sampleRuns = (): SampleRuns => JSON.parse(readFileSync(join(import.meta.dirname, SAMPLE_FIXTURE), "utf-8")) as SampleRuns;
const recordedRun = (id: string) => sampleRuns().runs.find((r) => r.id === id)!;
/** The engine a recorded run's report names. */
const engineOf = (id: string) => /cst:engine "([^"]+)"/.exec(String((recordedRun(id).frames[0] as { text: string }).text))![1];

/** A workspace of the policies sample open on mapping mode with the Sample tab showing, and every request the page makes to the service's transforms route noted. */
async function policiesPane(page: Page, fake: FakeService, requested: string[] = []): Promise<Locator> {
  page.on("request", (r) => void requested.push(new URL(r.url()).pathname));
  const pane = await sampleDock(page, fake);
  return pane;
}

test("a Turtle sample runs when Run is pressed and not before, and shows its output with the engine the run names", async ({ page }) => {
  const fake = new FakeService();
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Your own Turtle/ }).click();
  await page.locator('input[type="file"]').setInputFiles(join(import.meta.dirname, "../../../tools/mork_rdf/tests/fixtures/catalogue-mapping.ttl"));
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await page.goto(`/#/w/${[...fake.workspaces.keys()][0]}/mapping`);
  await page.getByRole("tab", { name: "Sample" }).click();
  const pane = page.getByRole("region", { name: "Sample", exact: true });
  const forms = pane.getByRole("group", { name: "Compiled form" });
  await expect(forms).toContainText("Not compiled yet");
  // the sample is typed, and the author waits longer than the old automatic rerun did
  await pane.getByRole("textbox", { name: /^Sample source/ }).fill(recordedRun("turtle").sample);
  await expect(pane.getByRole("combobox", { name: "Sample format" })).toHaveValue("text/turtle");
  await page.waitForTimeout(1500);
  expect(fake.runs).toHaveLength(0);
  expect(fake.submitted.filter((s) => s.kind === "compile" || s.kind === "dry-run")).toHaveLength(0);
  await expect(pane.getByRole("status", { name: "Sample status" })).toContainText("Nothing has run yet.");

  await pane.getByRole("button", { name: "Run", exact: true }).click();
  const status = pane.getByRole("status", { name: "Sample status" });
  await expect(status).toContainText("Complete, 10 parts, does not conform.");
  expect(fake.runs).toHaveLength(1);
  expect(fake.runs[0]).toMatchObject({ kind: "sample", mediaType: "text/turtle", body: recordedRun("turtle").sample });
  expect(fake.submitted.filter((s) => s.kind === "compile")).toHaveLength(1);
  // the engine the report names, and the form the compilation wrote
  await expect(pane).toContainText(`Evaluated by ${engineOf("turtle")}.`);
  expect(engineOf("turtle")).toMatch(/^mork_rdf .* on Oxigraph /);
  await expect(forms.getByRole("radio", { name: "SPARQL CONSTRUCT" })).toBeChecked();
  await expect(forms).toContainText("Catalogue.compiled.ttl");
  await expect(forms).toContainText("Runs here");
  // each mapping's output through the explorer, and its count in the tree
  const item = pane.getByRole("region", { name: /^Part \d+, artefact$/ }).filter({ hasText: "0/Map_Title.nt" });
  await expect(item.getByLabel("Output text")).toContainText("tgt:title");
  const tree = page.getByRole("tree", { name: /^Mappings of/ });
  await expect(tree.locator("text:has(title)").first()).toBeVisible();
  await expect(tree.locator('text[data-stale="true"]')).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "Mapping schemes" })).toContainText("triples written");
  await expect(page.getByRole("navigation", { name: "Mapping schemes" })).not.toContainText("out of date");
  await expect(page.getByRole("note", { name: "Counts out of date" })).toHaveCount(0);

  // an edit of the scheme runs nothing and marks the counts, the list and the pane as out of date, and undoing it makes them current again
  page.once("dialog", (d) => void d.accept("Another root"));
  await page.getByRole("button", { name: "Root datum" }).click();
  await expect(page.getByRole("note", { name: "Counts out of date" })).toBeVisible();
  await expect(tree.locator('text[data-stale="true"]').first()).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Mapping schemes" })).toContainText("triples written, out of date");
  await expect(pane.getByRole("note", { name: "Out of date" })).toContainText("out of date until you run again");
  await expect(forms).toContainText("The scheme may have changed since this compilation. Run compiles it again.");
  await page.waitForTimeout(1500);
  expect(fake.runs).toHaveLength(1);
  expect(fake.submitted.filter((s) => s.kind === "compile")).toHaveLength(1);
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(page.getByRole("note", { name: "Counts out of date" })).toHaveCount(0);
  await expect(pane.getByRole("note", { name: "Out of date" })).toHaveCount(0);
});

test("an XML sample runs when Run is pressed and not before, shows its output with the engine named, and an edit of the sample marks the counts out of date", async ({ page }) => {
  const fake = new FakeService();
  const requested: string[] = [];
  const pane = await policiesPane(page, fake, requested);
  const status = pane.getByRole("status", { name: "Sample status" });
  const forms = pane.getByRole("group", { name: "Compiled form" });
  // the XML example belongs to the XML scheme, which the pane lists the forms of
  await expect(pane.getByRole("group", { name: "Sample controls" })).toContainText("m1:Scheme");
  await expect(forms).toContainText("Not compiled yet");
  await expect(pane.getByRole("textbox", { name: "Sample source in XML" })).toHaveValue(recordedRun("xml").sample);
  await page.waitForTimeout(1500);
  expect(fake.runs).toHaveLength(0);
  expect(fake.submitted.filter((s) => s.kind === "compile" || s.kind === "dry-run")).toHaveLength(0);
  await expect(status).toContainText("Nothing has run yet.");

  await pane.getByRole("button", { name: "Run", exact: true }).click();
  await expect(status).toContainText("Complete, 7 parts, conforms.");
  expect(fake.runs).toHaveLength(1);
  expect(fake.runs[0]).toMatchObject({ kind: "sample", mediaType: "application/xml", body: recordedRun("xml").sample });
  await expect(pane).toContainText(`Evaluated by ${engineOf("xml")}.`);
  expect(engineOf("xml")).toMatch(/^Saxon-HE .*XSLT 3\.0$/);
  // the form of the XML scheme, with a runtime, and the output of one mapping
  await expect(forms.getByRole("radio", { name: "XSLT 3.0" })).toBeChecked();
  await expect(forms).toContainText("Scheme.xsl");
  await expect(forms).toContainText("Runs here");
  await expect(forms.getByRole("radio")).toHaveCount(1);
  await expect(pane.getByRole("region", { name: "Part 6, artefact" }).getByLabel("Output text")).toContainText("target:Policy");
  // the counts of the last run are in the tree, current
  const tree = page.getByRole("tree", { name: /^Mappings of/ });
  await expect(tree.locator("text:has(title)").first()).toBeVisible();
  await expect(tree.locator('text[data-stale="true"]')).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "Mapping schemes" })).toContainText("triples written");
  // the studio does not ask the deprecated route to run anything
  expect(requested.filter((p) => p.endsWith("/transforms"))).toEqual([]);

  // an edit of the sample runs nothing and marks the counts as out of date
  const box = pane.getByRole("textbox", { name: "Sample source in XML" });
  await box.fill(`${recordedRun("xml").sample}<!-- edited -->\n`);
  await expect(page.getByRole("note", { name: "Counts out of date" })).toBeVisible();
  await expect(tree.locator('text[data-stale="true"]').first()).toBeVisible();
  await expect(pane.getByRole("note", { name: "Out of date" })).toBeVisible();
  await expect(status).toContainText("Complete, 7 parts, conforms.");
  // the canvas marks its counts the same way
  await page.getByRole("group", { name: "Drawing" }).getByRole("button", { name: "Canvas" }).click();
  await expect(page.locator('.react-flow__node-mapping [data-stale="true"]').first()).toBeVisible();
  await page.getByRole("group", { name: "Drawing" }).getByRole("button", { name: "Tree" }).click();
  await page.waitForTimeout(1500);
  expect(fake.runs).toHaveLength(1);
  // the edited sample is one the fake has no frames for, so its run is the fake's own failure, and the counts of the last run are kept, still out of date
  await pane.getByRole("button", { name: "Run", exact: true }).click();
  await expect(status).toContainText("Failed. The fake service has frames only for the sample runs");
  expect(fake.runs).toHaveLength(2);
  expect(fake.submitted.filter((s) => s.kind === "compile")).toHaveLength(1);
  await expect(page.getByRole("note", { name: "Counts out of date" })).toBeVisible();
  // putting the sample back makes the counts current again
  await box.fill(recordedRun("xml").sample);
  await expect(page.getByRole("note", { name: "Counts out of date" })).toHaveCount(0);
  expect(requested.filter((p) => p.endsWith("/transforms"))).toEqual([]);
});

test("a JSON sample runs the JOLT form, and an RML form shows that it waits on a runtime and offers no Run", async ({ page }) => {
  const fake = new FakeService();
  const pane = await policiesPane(page, fake);
  const status = pane.getByRole("status", { name: "Sample status" });
  const forms = pane.getByRole("group", { name: "Compiled form" });
  // the JSON example belongs to the JSON scheme, so the pane lists that scheme's forms
  await pane.getByRole("button", { name: "Clear" }).click();
  await pane.getByRole("button", { name: /^Use the JSON example/ }).click();
  await expect(pane.getByRole("combobox", { name: "Sample format" })).toHaveValue("application/json");
  await pane.getByRole("button", { name: "Run", exact: true }).click();
  await expect(status).toContainText("Complete, 7 parts, conforms.");
  expect(fake.runs[0]).toMatchObject({ mediaType: "application/json", body: recordedRun("json").sample });
  await expect(pane).toContainText(`Evaluated by ${engineOf("json")}.`);
  await expect(forms.getByRole("radio")).toHaveCount(2);
  await expect(forms.getByRole("radio", { name: "JOLT" })).toBeChecked();
  const rml = forms.getByRole("radio", { name: "RML" });
  await expect(forms).toContainText("mapping.rml.ttl");
  await expect(forms).toContainText("No runtime yet");
  // choosing the RML form says in words why Run is off
  await rml.check();
  await expect(pane.getByRole("button", { name: "Run", exact: true })).toBeDisabled();
  await expect(pane.getByRole("note", { name: "Why Run is off" })).toContainText("Waits on an RML runtime.");
  expect(await pane.innerText()).not.toMatch(/\b[A-Z]{2,}-\d+\b/);
  expect(fake.runs).toHaveLength(1);
  await forms.getByRole("radio", { name: "JOLT" }).check();
  await expect(pane.getByRole("button", { name: "Run", exact: true })).toBeEnabled();
  await expect(pane.getByRole("note", { name: "Why Run is off" })).toHaveCount(0);
});

test("the Sample tab is in mapping mode's dock only", async ({ page }) => {
  const fake = new FakeService();
  await lendingWorkspace(page, fake);
  await expect(page.getByRole("tab", { name: "Turtle" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Sample" })).toHaveCount(0);
});


// --- The page's columns, collapsed and resized by the author and kept in the browser (SVA-U1) ---

const widthOf = async (locator: Locator): Promise<number> => (await locator.boundingBox())!.width;

test("each of the navigation, the list and the dock collapses to a rail and expands again, and the middle takes the room", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const fake = new FakeService();
  await sampleDock(page, fake);
  const columns = [
    { noun: "navigation", box: page.getByRole("navigation", { name: "Workspace" }) },
    { noun: "list", box: page.locator(".col-list") },
    { noun: "dock", box: page.getByRole("complementary", { name: "Inspector" }) },
  ];
  for (const { noun, box } of columns) {
    // the list is inside the main area, so its middle is the pane beside it
    const main = noun === "list" ? page.locator(".detail-pane") : page.locator("main.main");
    const open = await widthOf(main);
    const collapse = page.getByRole("button", { name: `Collapse the ${noun}` });
    await expect(collapse).toHaveAttribute("aria-expanded", "true");
    await collapse.click();
    const expand = page.getByRole("button", { name: `Expand the ${noun}` });
    await expect(expand).toHaveAttribute("aria-expanded", "false");
    await expect(page.getByRole("button", { name: `Collapse the ${noun}` })).toHaveCount(0);
    expect(Math.round(await widthOf(box))).toBe(36);
    expect(await widthOf(main)).toBeGreaterThan(open + 100);
    await expand.click();
    await expect(page.getByRole("button", { name: `Collapse the ${noun}` })).toHaveAttribute("aria-expanded", "true");
    expect(Math.abs((await widthOf(main)) - open)).toBeLessThan(1.5);
  }
  // the header's toggle means the same as the dock's own button
  await page.getByRole("button", { name: "Toggle inspector" }).click();
  await expect(page.getByRole("button", { name: "Expand the dock" })).toHaveAttribute("aria-expanded", "false");
  await expect(page.getByRole("button", { name: "Toggle inspector" })).toHaveAttribute("aria-pressed", "false");
  await page.getByRole("button", { name: "Expand the dock" }).click();
  await expect(page.getByRole("button", { name: "Toggle inspector" })).toHaveAttribute("aria-pressed", "true");
});

test("with the Sample tab open, collapsing the navigation and the scheme list leaves the mapping tree unclipped", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const fake = new FakeService();
  await sampleDock(page, fake);
  const tree = page.getByRole("tree", { name: /^Mappings of/ });
  const container = tree.locator("xpath=..");
  await page.getByRole("button", { name: "Collapse the navigation" }).click();
  await page.getByRole("button", { name: "Collapse the list" }).click();
  await expect(page.getByRole("button", { name: "Expand the list" })).toBeVisible();
  const [t, c] = [(await tree.boundingBox())!, (await container.boundingBox())!];
  expect(t.x + t.width).toBeLessThanOrEqual(c.x + c.width + 0.5);
  expect(await container.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(true);
  // the dock's run pane is whole beside it
  const pane = page.getByRole("region", { name: "Sample", exact: true });
  const [p, d] = [(await pane.boundingBox())!, (await page.getByRole("complementary", { name: "Inspector" }).boundingBox())!];
  expect(p.x + p.width).toBeLessThanOrEqual(d.x + d.width + 0.5);
  expect(c.x + c.width).toBeLessThanOrEqual(d.x + 8);
});

test("dragging the dock's handle resizes it down to its minimum, and its width and a collapsed column are the same after a reload", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const fake = new FakeService();
  await sampleDock(page, fake);
  const dock = page.getByRole("complementary", { name: "Inspector" });
  const handle = page.getByRole("separator", { name: "Resize the dock" });
  const before = await widthOf(dock);
  const at = (await handle.boundingBox())!;
  const [x, y] = [at.x + at.width / 2, at.y + at.height / 2];
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x - 80, y, { steps: 6 });
  await page.mouse.up();
  const wider = await widthOf(dock);
  expect(Math.abs(wider - (before + 80))).toBeLessThan(2);
  const grip = (await handle.boundingBox())!;
  await page.mouse.move(grip.x + grip.width / 2, y);
  await page.mouse.down();
  await page.mouse.move(1400, y, { steps: 8 });
  await page.mouse.up();
  expect(Math.round(await widthOf(dock))).toBe(300);
  await expect(handle).toHaveAttribute("aria-valuenow", "300");
  const again = (await handle.boundingBox())!;
  await page.mouse.move(again.x + again.width / 2, y);
  await page.mouse.down();
  await page.mouse.move(again.x + again.width / 2 - 150, y, { steps: 8 });
  await page.mouse.up();
  const kept = Math.round(await widthOf(dock));
  expect(kept).toBe(450);
  await page.getByRole("button", { name: "Collapse the list" }).click();
  await page.reload();
  await expect(page.getByRole("button", { name: "Expand the list" })).toHaveAttribute("aria-expanded", "false");
  expect(Math.round(await widthOf(page.getByRole("complementary", { name: "Inspector" })))).toBe(kept);
  await expect(page.getByRole("separator", { name: "Resize the dock" })).toHaveAttribute("aria-valuenow", String(kept));
});

test("a handle moves with the arrow keys, Home and End, and a collapsed column takes no focus on Tab", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const fake = new FakeService();
  await sampleDock(page, fake);
  const dock = page.getByRole("separator", { name: "Resize the dock" });
  const list = page.getByRole("separator", { name: "Resize the list" });
  for (const h of [dock, list]) {
    await expect(h).toHaveAttribute("aria-orientation", "vertical");
    await h.focus();
    const min = Number(await h.getAttribute("aria-valuemin"));
    const max = Number(await h.getAttribute("aria-valuemax"));
    expect(max).toBeGreaterThan(min);
    await page.keyboard.press("Home");
    await expect(h).toHaveAttribute("aria-valuenow", String(min));
    await page.keyboard.press("End");
    await expect(h).toHaveAttribute("aria-valuenow", String(max));
    await page.keyboard.press("Home");
  }
  // the arrow that moves a boundary toward the middle shrinks the dock's column and the one away from it grows it
  await dock.focus();
  await page.keyboard.press("ArrowLeft");
  await expect(dock).toHaveAttribute("aria-valuenow", "316");
  await page.keyboard.press("ArrowRight");
  await expect(dock).toHaveAttribute("aria-valuenow", "300");
  await list.focus();
  await page.keyboard.press("ArrowRight");
  await expect(list).toHaveAttribute("aria-valuenow", String(Number(await list.getAttribute("aria-valuemin")) + 16));
  await page.keyboard.press("ArrowLeft");
  await expect(list).toHaveAttribute("aria-valuenow", String(Number(await list.getAttribute("aria-valuemin"))));
  // a collapsed column holds nothing that Tab reaches
  await page.getByRole("button", { name: "Collapse the navigation" }).click();
  await page.getByRole("button", { name: "Collapse the list" }).click();
  await page.getByRole("button", { name: "Collapse the dock" }).click();
  await expect(page.getByRole("navigation", { name: "Workspace" }).getByRole("link")).toHaveCount(0);
  const inside = new Set<string>();
  await page.locator("body").focus();
  for (let i = 0; i < 40; i++) {
    await page.keyboard.press("Tab");
    inside.add(await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      return el?.closest(".col-body, .dock-sample, .nav a") ? "hidden column" : "ok";
    }));
  }
  expect([...inside]).toEqual(["ok"]);
});

test("at 1100 pixels the page has no horizontal scroll bar with every column open and the run pane stacks, and where there is room its controls are left of its displays", async ({ page }) => {
  await page.setViewportSize({ width: 1100, height: 800 });
  const fake = new FakeService();
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Policies from XML and JSON/ }).click();
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await page.goto(`/#/w/${[...fake.workspaces.keys()][0]}/mapping`);
  // the window cannot give the middle its minimum beside an open dock, so the dock starts collapsed
  await expect(page.getByRole("button", { name: "Expand the dock" })).toBeVisible();
  await page.getByRole("button", { name: "Expand the dock" }).click();
  await page.getByRole("tab", { name: "Sample" }).click();
  await expect(page.getByRole("button", { name: "Collapse the navigation" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Collapse the list" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth && document.body.scrollWidth <= window.innerWidth)).toBe(true);
  const controls = page.getByRole("group", { name: "Sample controls" });
  const display = page.getByRole("status", { name: "Sample status" });
  const [c, d] = [(await controls.boundingBox())!, (await display.boundingBox())!];
  expect(c.y + c.height).toBeLessThanOrEqual(d.y + 1);
  // a wide window gives the dock its wide default, and the controls sit beside the displays
  await page.setViewportSize({ width: 1920, height: 1000 });
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByRole("tab", { name: "Sample" }).click();
  const [c2, d2] = [(await page.getByRole("group", { name: "Sample controls" }).boundingBox())!, (await page.getByRole("status", { name: "Sample status" }).boundingBox())!];
  expect(c2.x + c2.width).toBeLessThanOrEqual(d2.x + 1);
  expect(Math.abs(c2.y - d2.y)).toBeLessThan(40);
});

/** Every node of the canvas lies inside its pane, polled since a refit follows the resize. */
async function expectDrawingWhole(page: Page): Promise<void> {
  await expect
    .poll(async () => {
      const pane = (await page.locator(".react-flow").first().boundingBox())!;
      const boxes = await page.locator(".react-flow__node").evaluateAll((els) => els.map((el) => el.getBoundingClientRect().toJSON()));
      return boxes.length > 0 && boxes.every((b) => b.x >= pane.x - 1 && b.y >= pane.y - 1 && b.x + b.width <= pane.x + pane.width + 1 && b.y + b.height <= pane.y + pane.height + 1);
    })
    .toBe(true);
}

test("the mapping canvas and the ontology drawing are whole after a column is collapsed or resized", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const fake = new FakeService();
  await sampleDock(page, fake);
  await page.getByRole("button", { name: "Canvas" }).click();
  await expectDrawingWhole(page);
  const handle = page.getByRole("separator", { name: "Resize the dock" });
  const at = (await handle.boundingBox())!;
  await page.mouse.move(at.x + at.width / 2, 400);
  await page.mouse.down();
  await page.mouse.move(at.x - 200, 400, { steps: 6 });
  await page.mouse.up();
  await expectDrawingWhole(page);
  await page.getByRole("button", { name: "Collapse the dock" }).click();
  await expectDrawingWhole(page);
  await page.getByRole("button", { name: "Collapse the navigation" }).click();
  await expectDrawingWhole(page);
  // the ontology drawing in the Baseline view
  const fake2 = new FakeService();
  const ws = await lendingWorkspace(page, fake2);
  await page.goto(`/#/w/${ws}/baseline`);
  await page.getByRole("button", { name: "Diagram" }).click();
  await expectDrawingWhole(page);
  await page.getByRole("button", { name: "Collapse the list" }).click();
  await expectDrawingWhole(page);
  await page.getByRole("button", { name: "Expand the list" }).click();
  await page.getByRole("button", { name: "Expand the dock" }).click();
  await expectDrawingWhole(page);
});

// --- The output explorer in the run pane, and a canvas that keeps the view its author set (SVA-M4) ---

/** The pane's part, found by its heading's accessible name, after a run in mapping mode has completed. */
async function runSample(page: Page, fake: FakeService): Promise<Locator> {
  const pane = await sampleDock(page, fake);
  await pane.getByRole("button", { name: "Run", exact: true }).click();
  await expect(pane.getByRole("status", { name: "Sample status" })).toContainText("Complete, 7 parts");
  return pane;
}

test("a run's artefact opens as Turtle text, switches to a table that filters and to a graph, and the choice is kept after a reload", async ({ page }) => {
  const fake = new FakeService();
  const pane = await runSample(page, fake);
  const artefact = pane.getByRole("region", { name: "Part 2, artefact" });
  // Turtle text is the default for RDF
  await expect(artefact.getByRole("group", { name: "Rendering" }).getByRole("button", { name: "Text" })).toHaveAttribute("aria-pressed", "true");
  await expect(artefact.getByRole("group", { name: "Text format" }).getByRole("button", { name: "Turtle" })).toHaveAttribute("aria-pressed", "true");
  const text = artefact.getByLabel("Output text");
  await expect(text).toContainText("<urn:lattice:studio:mapping/cover/policies/1/policy/1/cover/1> a target:Cover;");
  await expect(text).not.toContainText("application/n-triples");
  await artefact.getByRole("group", { name: "Text format" }).getByRole("button", { name: "N-Triples" }).click();
  await expect(text).toContainText("<urn:lattice:studio:mapping/cover/policies/1/policy/1/cover/1> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <urn:example:target#Cover> .");
  await expect(artefact.getByRole("button", { name: "Copy" })).toBeVisible();
  await expect(artefact.getByRole("button", { name: "Download" })).toBeVisible();
  // the table, filtered
  await artefact.getByRole("button", { name: "Table", exact: true }).click();
  const table = artefact.getByRole("table", { name: "Triples" });
  await expect(table.getByRole("row")).toHaveCount(9);
  await expect(artefact).toContainText("Showing 8 of 8 rows.");
  await artefact.getByRole("searchbox", { name: "Filter rows" }).fill("nothing like this");
  await expect(table.getByRole("row")).toHaveCount(1);
  await expect(artefact).toContainText("Showing 0 of 0 matching rows, 8 held.");
  await artefact.getByRole("searchbox", { name: "Filter rows" }).fill("coverOf");
  await expect(table.getByRole("row")).toHaveCount(5);
  await expect(table.getByRole("row").nth(1)).toContainText("coverOf");
  // the graph
  await artefact.getByRole("button", { name: "Graph", exact: true }).click();
  await expect(artefact.locator(".react-flow__node").filter({ hasText: "P-1" })).toBeVisible();
  // the choice is kept for the media type
  await page.reload();
  await page.getByRole("tab", { name: "Sample" }).click();
  const again = page.getByRole("region", { name: "Sample", exact: true });
  await again.getByRole("button", { name: "Run", exact: true }).click();
  await expect(again.getByRole("status", { name: "Sample status" })).toContainText("Complete, 7 parts");
  await expect(again.getByRole("region", { name: "Part 2, artefact" }).getByRole("button", { name: "Graph", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(again.getByRole("region", { name: "Part 2, artefact" }).locator(".react-flow__node").filter({ hasText: "P-1" })).toBeVisible();
  // and the report, another media type, is still Turtle text
  await expect(again.getByRole("region", { name: "Part 1, report" }).getByRole("button", { name: "Text", exact: true })).toHaveAttribute("aria-pressed", "true");
});

test("the report part opens as text and its table lists the report's triples", async ({ page }) => {
  const fake = new FakeService();
  const pane = await runSample(page, fake);
  const report = pane.getByRole("region", { name: "Part 1, report" });
  await expect(report.getByRole("button", { name: "Text", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(report.getByLabel("Output text")).toContainText("sh:conforms true");
  await report.getByRole("button", { name: "Table", exact: true }).click();
  const rows = report.getByRole("table", { name: "Triples" }).getByRole("row");
  // the heading row, then the report's triples, which name the engine and the one finding of a scheme the sample is not read by
  await expect(rows).toHaveCount(10);
  await expect(rows.filter({ hasText: "sh:ValidationReport" })).toHaveCount(1);
  await expect(rows.filter({ hasText: "sh:conforms" })).toContainText('"true"^^xsd:boolean');
  await expect(rows.filter({ hasText: "cst:engine" })).toContainText("Saxon-HE 12.5, XSLT 3.0");
});

test("a part whose text does not parse in its media type says so with the parser's message, shows its text and leaves the pane whole", async ({ page }) => {
  const fake = new FakeService();
  fake.runArtefact = "<https://example.org/a> <https://example.org/p> .\n";
  const pane = await runSample(page, fake);
  const artefact = pane.getByRole("region", { name: "Part 2, artefact" });
  await expect(artefact).toContainText("does not parse");
  await expect(artefact).toContainText("Its text is shown as received.");
  await expect(artefact.getByLabel("Output text")).toContainText("<https://example.org/a> <https://example.org/p> .");
  await artefact.getByRole("button", { name: "Table", exact: true }).click();
  await expect(artefact).toContainText("does not parse");
  // the report beside it still reads
  await expect(pane.getByRole("region", { name: "Part 1, report" }).getByLabel("Output text")).toContainText("sh:conforms true");
  await expect(pane.getByRole("status", { name: "Sample status" })).toContainText("Complete, 7 parts");
});

/** The viewport of the first canvas, as React Flow keeps it, and the middle of its pane in the drawing's own coordinates. */
async function viewOf(page: Page): Promise<{ zoom: number; x: number; y: number; centre: { x: number; y: number } }> {
  const [transform, pane] = await Promise.all([page.locator(".react-flow__viewport").first().evaluate((el) => (el as HTMLElement).style.transform), page.locator(".react-flow").first().boundingBox()]);
  const [, x, y, zoom] = /translate\((-?[\d.]+)px,\s*(-?[\d.]+)px\)\s*scale\((-?[\d.]+)\)/.exec(transform)!.map(Number);
  return { zoom, x, y, centre: { x: (pane!.width / 2 - x) / zoom, y: (pane!.height / 2 - y) / zoom } };
}

async function dragDock(page: Page, by: number): Promise<void> {
  const at = (await page.getByRole("separator", { name: "Resize the dock" }).boundingBox())!;
  await page.mouse.move(at.x + at.width / 2, 400);
  await page.mouse.down();
  await page.mouse.move(at.x + at.width / 2 + by, 400, { steps: 6 });
  await page.mouse.up();
}

test("a canvas the author zoomed keeps its zoom and centre when the dock is resized, and is fitted again after the fit button", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const fake = new FakeService();
  await sampleDock(page, fake);
  await page.getByRole("button", { name: "Canvas" }).click();
  await expectDrawingWhole(page);
  const fitted = await viewOf(page);
  // zoom out with the wheel, over the pane, which moves the view
  const pane = (await page.locator(".react-flow").first().boundingBox())!;
  await page.mouse.move(pane.x + pane.width / 2, pane.y + pane.height / 2);
  await page.mouse.wheel(0, 300);
  await expect.poll(async () => (await viewOf(page)).zoom).toBeLessThan(fitted.zoom - 0.05);
  await page.waitForTimeout(400);
  const zoomed = await viewOf(page);
  // narrower and then wider: the author's zoom and the centre of the view stay
  await dragDock(page, -120);
  await page.waitForTimeout(600);
  const narrower = await viewOf(page);
  expect(narrower.zoom).toBeCloseTo(zoomed.zoom, 3);
  expect(Math.abs(narrower.centre.x - zoomed.centre.x)).toBeLessThan(2);
  expect(Math.abs(narrower.centre.y - zoomed.centre.y)).toBeLessThan(2);
  await dragDock(page, 120);
  await page.waitForTimeout(600);
  const back = await viewOf(page);
  expect(back.zoom).toBeCloseTo(zoomed.zoom, 3);
  expect(Math.abs(back.centre.x - zoomed.centre.x)).toBeLessThan(2);
  // the fit button fits it again, and a resize then refits it
  await page.getByRole("button", { name: "fit view" }).first().click();
  await expect.poll(async () => (await viewOf(page)).zoom).toBeCloseTo(fitted.zoom, 2);
  await dragDock(page, -200);
  await expectDrawingWhole(page);
  const refitted = await viewOf(page);
  await page.getByRole("button", { name: "fit view" }).first().click();
  await page.waitForTimeout(400);
  const byButton = await viewOf(page);
  expect(refitted.zoom).toBeCloseTo(byButton.zoom, 2);
  expect(Math.abs(refitted.x - byButton.x)).toBeLessThan(2);
  expect(Math.abs(refitted.y - byButton.y)).toBeLessThan(2);
});

// --- the persistence canvas, the exploded view (SVA-P1) ---------------------------------------------------------------------------------

/** The facility sample's Persistence view, with the canvas chosen. */
async function facilityPersistenceCanvas(page: Page, fake: FakeService): Promise<{ ws: string; canvas: Locator }> {
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Facility agreement/ }).click();
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  const ws = [...fake.workspaces.keys()][0];
  await page.goto(`/#/w/${ws}/persistence`);
  await page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Canvas" }).click();
  return { ws, canvas: page.getByRole("region", { name: "Persistence canvas" }) };
}

const landingNode = (canvas: Locator, kind: string) => canvas.locator(`.landing-node.${kind}`);

test("the persistence view offers a canvas that says there is no compilation and offers one, and draws the facility's aggregate once compiled", async ({ page }) => {
  const fake = new FakeService();
  const { canvas } = await facilityPersistenceCanvas(page, fake);
  // The node list and its editor are still there beside the choice.
  await expect(page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Details" })).toHaveAttribute("aria-pressed", "false");
  await expect(canvas.getByRole("heading", { name: "No persistence compilation yet" })).toBeVisible();
  expect(fake.submitted.filter((s) => s.kind === "compile")).toEqual([]);

  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  await expect(canvas.getByRole("group", { name: "Lens" }).getByRole("button", { name: "Aggregate" })).toHaveAttribute("aria-pressed", "true");
  const compiles = fake.submitted.filter((s) => s.kind === "compile");
  expect(compiles.map((s) => s.target)).toEqual(["persistence"]);

  // The first target is the borrower. Pick the facility.
  const target = canvas.getByRole("combobox", { name: "Target" });
  await expect(target.getByRole("option")).toHaveText(["Borrower", "Facility"]);
  await target.selectOption({ label: "Facility" });
  await expect(landingNode(canvas, "root")).toContainText("Facility");
  await expect(landingNode(canvas, "owned")).toContainText("Drawdown");
  await expect(landingNode(canvas, "reference")).toHaveCount(3);
  // Seven places, each with its kind, its label and its graph or the rule that names it, and one edge from the root to each.
  const places = landingNode(canvas, "place");
  await expect(places).toHaveCount(7);
  for (const text of ["urn:g:facilities", "urn:g:meta/6", "urn:g:txn", "urn:g:keys", "{newRev}/add", "{newRev}/del", "urn:g:txlog/{month}"]) {
    await expect(places.filter({ hasText: text }).first()).toBeVisible();
  }
  await expect(canvas.locator(".react-flow__edge title").filter({ hasText: /^Patch log, the triples added, written to/ })).toHaveCount(1);
  // A referenced edge is dashed and says how it is held, and an owned one is solid.
  const dashed = canvas.locator(".onto-edge-label.dashed");
  await expect(dashed).toHaveCount(3);
  await expect(dashed).toContainText(["arrangedBy · identity", "borrower · identity", "lender · identity"]);
  await expect(canvas.locator(".onto-edge-label:not(.dashed)")).toHaveText(["hasDrawdown"]);
  await expect(canvas.getByText(/job [0-9a-f]{8}/)).toBeVisible();
  await expect(canvas.getByRole("alert")).toHaveCount(0);
});

test("the lenses draw the profile's targets and the scope node's, and a place is read with the operations that write it", async ({ page }) => {
  const fake = new FakeService();
  const { canvas } = await facilityPersistenceCanvas(page, fake);
  const saved = fake.saves.length;
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  const lenses = canvas.getByRole("group", { name: "Lens" });
  await expect(lenses.getByRole("button", { name: "Aggregate" })).toBeVisible();

  await lenses.getByRole("button", { name: "Profile" }).click();
  const profile = canvas.getByRole("combobox", { name: "Profile" });
  await expect(profile.getByRole("option")).toHaveText(["BorrowerAccessProfile", "BorrowerEpoch", "BorrowerIdentity", "BorrowerPrivacy", "FacilityBoundaryProfile", "FacilityConcurrencyProfile", "FacilityEpoch", "FacilityReceiptProfile"]);
  await profile.selectOption({ label: "FacilityEpoch" });
  await expect(landingNode(canvas, "target")).toHaveCount(1);
  await expect(landingNode(canvas, "target")).toContainText("Facility");
  await expect(landingNode(canvas, "root")).toHaveCount(0);
  await expect(landingNode(canvas, "place")).toHaveCount(7);

  await lenses.getByRole("button", { name: "Scope node" }).click();
  const scope = canvas.getByRole("combobox", { name: "Scope node" });
  await expect(scope.getByRole("option")).toHaveText(["BorrowerEntity", "FacilityClass"]);
  await scope.selectOption({ label: "BorrowerEntity" });
  await expect(landingNode(canvas, "target")).toContainText("Borrower");
  await expect(landingNode(canvas, "place")).toHaveCount(5);
  // A borrower keeps no patch log.
  await expect(landingNode(canvas, "place").filter({ hasText: "Patch log" })).toHaveCount(0);

  // Back in the first lens, a click selects a place and shows what writes it. Nothing on the canvas edits.
  await lenses.getByRole("button", { name: "Aggregate" }).click();
  await canvas.getByRole("combobox", { name: "Target" }).selectOption({ label: "Facility" });
  await landingNode(canvas, "place").filter({ hasText: "{newRev}/add" }).click();
  const details = canvas.getByRole("complementary", { name: "Selected node" });
  await expect(details.getByRole("heading", { name: "Patch log, the triples added" })).toBeVisible();
  await expect(details.getByText("{newRev}/add", { exact: true })).toBeVisible();
  await expect(details.getByText("Facility/create-if-absent.rq")).toBeVisible();
  await expect(details.getByText("Facility/cas-replace.rq")).toBeVisible();
  await expect(details.getByText("Facility/replace-whole.rq")).toBeVisible();
  await expect(details.getByText("Facility/tombstone-delete.rq")).toHaveCount(0);
  await expect(details.getByText("cas-replace-composite-property-delta-patch-log-dataset-guard")).toBeVisible();
  // Selecting the root gives its profiles and scope nodes, and a referenced node says how it is held.
  await landingNode(canvas, "root").click();
  await expect(details.getByText("FacilityEpoch")).toBeVisible();
  await landingNode(canvas, "reference").filter({ hasText: "Lender" }).click();
  await expect(details.getByText("Outside the boundary, referenced by identity.")).toBeVisible();
  expect(fake.saves).toHaveLength(saved);
});

test("the canvas says it is out of date after an edit of the persistence part, and is current again after a compilation", async ({ page }) => {
  const fake = new FakeService();
  const { canvas } = await facilityPersistenceCanvas(page, fake);
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  await expect(canvas.getByRole("group", { name: "Lens" })).toBeVisible();
  await expect(canvas.getByRole("alert")).toHaveCount(0);

  // An edit of the persistence part: a new node.
  await page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Details" }).click();
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await page.getByRole("menuitem", { name: /^Class scope/ }).click();
  await page.getByRole("button", { name: "Create" }).click();
  await page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Canvas" }).click();
  await expect(canvas.getByRole("alert")).toContainText("out of date");
  // The picture is still the last compilation's, and compiling sends the edit.
  await expect(landingNode(canvas, "place").first()).toBeVisible();
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  await expect(canvas.getByRole("alert")).toHaveCount(0);
  const compiles = fake.submitted.filter((s) => s.kind === "compile");
  expect(compiles).toHaveLength(2);
  expect(compiles[1].body.length).toBeGreaterThan(compiles[0].body.length);
});

test("a compilation started in the Build view is drawn, and the canvas says it cannot tell whether it is out of date", async ({ page }) => {
  const fake = new FakeService();
  const { ws } = await facilityPersistenceCanvas(page, fake);
  await page.goto(`/#/w/${ws}/build`);
  await page.getByRole("button", { name: "Compile persistence" }).click();
  await expect(page.getByRole("listbox", { name: "Artefacts" })).toBeVisible();
  await page.goto(`/#/w/${ws}/persistence`);
  await page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Canvas" }).click();
  const canvas = page.getByRole("region", { name: "Persistence canvas" });
  await expect(canvas.getByRole("group", { name: "Lens" })).toBeVisible();
  await expect(canvas.getByText(/started elsewhere/)).toBeVisible();
  await expect(landingNode(canvas, "place").first()).toBeVisible();
});

test("the canvas keeps where the author moved a node, for the workspace and the lens", async ({ page }) => {
  const fake = new FakeService();
  const { ws, canvas } = await facilityPersistenceCanvas(page, fake);
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  await canvas.getByRole("combobox", { name: "Target" }).selectOption({ label: "Facility" });
  const root = landingNode(canvas, "root");
  await expect(root).toBeVisible();
  const start = (await root.boundingBox())!;
  await page.mouse.move(start.x + start.width / 2, start.y + 10);
  await page.mouse.down();
  await page.mouse.move(start.x + start.width / 2, start.y + 90, { steps: 6 });
  await page.mouse.up();
  const stored = await page.evaluate((key) => localStorage.getItem(key), `lattice-studio:persistence-canvas:${ws}:aggregate:Facility`);
  expect(Object.keys(JSON.parse(stored!))).toContain("root:Facility");
});

// --- the surface canvas, every kind of contract (SVA-S1) ---------------------------------------------------------------------------

/** The facility sample's Surface view, with the canvas chosen. */
async function facilitySurfaceCanvas(page: Page, fake: FakeService): Promise<{ ws: string; canvas: Locator }> {
  await fake.install(page);
  await page.goto("/");
  await page.getByRole("button", { name: "New workspace" }).first().click();
  await page.getByRole("button", { name: /^Facility agreement/ }).click();
  await page.getByRole("button", { name: "Create workspace" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  const ws = [...fake.workspaces.keys()][0];
  await page.goto(`/#/w/${ws}/surface`);
  await page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Canvas" }).click();
  return { ws, canvas: page.getByRole("region", { name: "Surface canvas" }) };
}

const surfaceNode = (canvas: Locator, kind: string) => canvas.locator(`.surface-node.${kind}`);
const pickContract = (page: Page, name: string) => page.locator(".list-item").filter({ hasText: name }).first().click();

test("the surface canvas draws a selected derivation and join with their statements, targets and lowered schemes, and all contracts as an overview", async ({ page }) => {
  const fake = new FakeService();
  const { canvas } = await facilitySurfaceCanvas(page, fake);
  // With nothing selected, all contracts are an overview, a carrier for each class the eight contracts read from, a node for each contract and the terms
  // they write, and no hop, binding, statement or scheme box. Nothing has been compiled.
  await expect(canvas.getByRole("group", { name: "Contracts shown" }).getByRole("button", { name: "All contracts" })).toHaveAttribute("aria-pressed", "true");
  await expect(surfaceNode(canvas, "carrier")).toHaveCount(4);
  await expect(surfaceNode(canvas, "contract")).toHaveCount(8);
  await expect(surfaceNode(canvas, "target").first()).toBeVisible();
  for (const kind of ["evidence", "statement", "entries", "scheme", "class"]) await expect(surfaceNode(canvas, kind)).toHaveCount(0);
  expect(fake.submitted.filter((s) => s.kind === "compile")).toEqual([]);

  // The derivation, as one line of infix text with its datatype, and its target read from the ontology, which declares it with another range.
  await pickContract(page, "facility-margin");
  await expect(canvas.getByRole("group", { name: "Contracts shown" }).getByRole("button", { name: "facility-margin" })).toHaveAttribute("aria-pressed", "true");
  await expect(surfaceNode(canvas, "carrier")).toHaveCount(1);
  await expect(surfaceNode(canvas, "scheme")).toContainText("no compilation yet");
  await expect(canvas.locator(".onto-edge-label").filter({ hasText: "commitment × margin : decimal" })).toBeVisible();
  await expect(surfaceNode(canvas, "evidence")).toHaveText([/commitment/, /margin/]);
  await expect(canvas.locator(".onto-edge-label.dashed").filter({ hasNotText: "lowered to" })).toHaveCount(0);
  const derived = surfaceNode(canvas, "target").filter({ hasText: "margin weighted commitment" });
  await expect(derived).toContainText("range disagrees");
  await expect(derived).toContainText("range integer");
  await expect(derived).toContainText("the contract states decimal");
  // The form beside it edits the contract as it does today.
  await expect(page.getByRole("heading", { name: "facility-margin" })).toBeVisible();

  // The join, a box for the second carrier, a pair of the key with its comparison, the link with its two rules, both the vocabulary's defaults, and the link declared by no one.
  await pickContract(page, "facility-branch");
  await expect(surfaceNode(canvas, "carrier")).toHaveCount(2);
  await expect(surfaceNode(canvas, "carrier").filter({ hasText: "Second carrier" })).toContainText("Branch");
  await expect(canvas.locator(".onto-edge-label").filter({ hasText: /^=$/ })).toBeVisible();
  const statement = surfaceNode(canvas, "statement");
  await expect(statement).toContainText("one value finds: at most one (default)");
  await expect(statement).toContainText("one instance links: any number (default)");
  const booked = surfaceNode(canvas, "target").filter({ hasText: "bookedAt" });
  await expect(booked).toContainText("not declared in the ontology");
  await expect(booked).toContainText("undeclared");

  // A node on the canvas selects the matching node in the form.
  await surfaceNode(canvas, "evidence").filter({ hasText: "bookingBranchCode" }).click();
  await expect(page).toHaveURL(/fb-code$/);
  await expect(page.getByRole("heading", { name: "Fb code" })).toBeVisible();

  // Compiling reads each scheme from the projections group, with its mappings and its review findings.
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  const scheme = surfaceNode(canvas, "scheme");
  await expect(scheme).toContainText("scheme_facility-branch");
  await expect(scheme).toContainText("2 mappings");
  await expect(scheme).toContainText("MappingReview × 1");
  expect(fake.submitted.filter((s) => s.kind === "compile").map((s) => s.target)).toEqual(["surface"]);
  await expect(canvas.getByRole("alert")).toHaveCount(0);

  // The scheme box opens the scheme in the mapping canvas, read only, in full with its terms and the review finding on the mapping it concerns.
  await scheme.click();
  const dialog = page.getByRole("dialog", { name: /^Lowered scheme/ });
  await expect(dialog.locator(".react-flow__node-mapping")).toHaveCount(2);
  await expect(dialog.locator(".react-flow__node-mapping").filter({ hasText: "node" })).toContainText("MappingReview");
  await expect(dialog.locator(".react-flow__node-mapping").filter({ hasText: "node" })).toContainText("bookedAt");
  await expect(dialog.locator(".react-flow__node-source")).toHaveText([/carrier/, /second/]);
  await dialog.locator(".react-flow__node-mapping").first().click({ button: "right" });
  await expect(page.getByRole("menu")).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
});

test("the overview of all contracts expands the contract selected in the list to its full drawing in place, and leaves the others as overview", async ({ page }) => {
  const fake = new FakeService();
  const { canvas } = await facilitySurfaceCanvas(page, fake);
  await pickContract(page, "facility-refinancing");
  await canvas.getByRole("group", { name: "Contracts shown" }).getByRole("button", { name: "All contracts" }).click();
  // Seven contracts stay overview, and the eighth is drawn with its members path, the member class and its target among them.
  await expect(surfaceNode(canvas, "contract")).toHaveCount(7);
  await expect(canvas.locator(".onto-edge-label.dashed").filter({ hasText: "refinances +" })).toBeVisible();
  await expect(surfaceNode(canvas, "class")).toHaveText([/Members/]);
  await expect(surfaceNode(canvas, "carrier").filter({ hasText: "facility-refinancing" })).toHaveCount(1);
  // Selecting another contract in the overview expands that one, and the first goes back to a node.
  await surfaceNode(canvas, "contract").filter({ hasText: "facility-branch" }).click();
  await expect(page).toHaveURL(/facility-branch-projection$/);
  await expect(surfaceNode(canvas, "class")).toHaveCount(0);
  await expect(surfaceNode(canvas, "statement")).toContainText("one value finds");
  await expect(surfaceNode(canvas, "contract")).toHaveCount(7);
  await expect(surfaceNode(canvas, "contract").filter({ hasText: "facility-refinancing" })).toHaveCount(1);
});

test("the surface canvas draws a promotion over its read path, an index, the promoted properties and the node for each member, and puts a finding on the element it concerns", async ({ page }) => {
  const fake = new FakeService();
  const { canvas } = await facilitySurfaceCanvas(page, fake);
  await pickContract(page, "drawdown-sector");
  // Each hop of the three-hop read path, from the drawdown to the promoted property.
  await expect(canvas.locator(".onto-edge-label").filter({ hasText: /^(drawn under|borrower|borrower sector)$/ })).toHaveCount(3);
  await expect(surfaceNode(canvas, "class")).toHaveText([/Facility/, /Borrower/]);
  await expect(surfaceNode(canvas, "target")).toContainText("drawdown sector");

  await pickContract(page, "borrower-sector");
  await expect(surfaceNode(canvas, "entries")).toContainText("closure over broader");
  await expect(surfaceNode(canvas, "entries")).toContainText("forms: closure relation, membership assertion, nominal class");

  // A node for each member: the members path to the member, the node's class, its identity and what it writes from the member.
  await pickContract(page, "facility-covenant-test");
  await expect(canvas.locator(".onto-edge-label").filter({ hasText: "rdf:rest *" })).toBeVisible();
  await expect(surfaceNode(canvas, "statement")).toContainText("Covenant test");
  await expect(surfaceNode(canvas, "statement")).toContainText("identity: by key (facility reference, the member)");
  await expect(surfaceNode(canvas, "statement")).toContainText("tests covenant ← the member");

  // A closure is marked on its hop and a candidate evidence edge is dashed.
  await pickContract(page, "facility-refinancing");
  await expect(canvas.locator(".onto-edge-label.dashed").filter({ hasText: "refinances +" })).toBeVisible();

  // A finding of the form is placed on the element it concerns. The link a join writes is declared by no baseline, which the form's findings say of the
  // result binding's property, so the edge that writes it carries the finding and the list names it.
  await pickContract(page, "facility-branch");
  await expect(canvas.locator(".onto-edge-label").filter({ hasText: "⚠ bookedAt" })).toBeVisible();
  await expect(canvas.getByRole("complementary", { name: "Findings on the canvas" })).toContainText("bookedAt is not declared in the baseline.");
});

test("the surface canvas says it is out of date after an edit of the surface part, and is current again after a compilation", async ({ page }) => {
  const fake = new FakeService();
  const { canvas } = await facilitySurfaceCanvas(page, fake);
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  await pickContract(page, "facility-margin");
  await expect(surfaceNode(canvas, "scheme").first()).toContainText("mappings");
  await expect(canvas.getByRole("alert")).toHaveCount(0);

  // An edit of the surface part, a new promotion.
  await page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Details" }).click();
  await page.locator('button[aria-haspopup="menu"]', { hasText: "Add" }).click();
  await page.getByRole("menuitem", { name: /^Promotion contract/ }).click();
  await page.getByRole("button", { name: "Create" }).click();
  await page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Canvas" }).click();
  await expect(canvas.getByRole("alert")).toContainText("out of date");
  // The picture still shows the last compilation's scheme, marked, and compiling reads the edit.
  await pickContract(page, "facility-margin");
  await expect(surfaceNode(canvas, "scheme").filter({ hasText: "out of date" }).first()).toBeVisible();
  await expect(surfaceNode(canvas, "scheme").first()).toContainText("mappings");
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  await expect(canvas.getByRole("alert")).toHaveCount(0);
  expect(fake.submitted.filter((s) => s.kind === "compile")).toHaveLength(2);
});

test("a surface compilation started in the Build view is drawn, and the canvas says it cannot tell whether it is out of date", async ({ page }) => {
  const fake = new FakeService();
  const { ws } = await facilitySurfaceCanvas(page, fake);
  await page.goto(`/#/w/${ws}/build`);
  await page.getByRole("button", { name: "Compile surface" }).click();
  await expect(page.getByRole("listbox", { name: "Artefacts" })).toBeVisible();
  await page.goto(`/#/w/${ws}/surface`);
  await page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Canvas" }).click();
  const canvas = page.getByRole("region", { name: "Surface canvas" });
  await expect(canvas.getByText(/started elsewhere/)).toBeVisible();
  await pickContract(page, "facility-margin");
  await expect(surfaceNode(canvas, "scheme").first()).toContainText("mappings");
});

// --- the surface canvas, building a path by clicking (SVA-S1 part 2) ----------------------------------------------------------------

const pathMode = (canvas: Locator) => canvas.getByRole("region", { name: "Path mode" });
const option = (canvas: Locator, property: string, direction: "forward" | "inverse" = "forward") =>
  pathMode(canvas).locator(`.path-option[data-property="https://example.org/lending#${property}"][data-direction="${direction}"]`);
/** The hops of the trail path mode shows, as the names it gives them. */
const trail = (canvas: Locator) => pathMode(canvas).getByRole("list", { name: "Path so far" }).locator(".hop-name");
/** The hops of the form's hop-by-hop control. */
const formHops = (page: Page) => page.getByLabel("Read path", { exact: true }).locator(".edge");

test("a promotion's read path is built by clicking from class to class, and the form's hop-by-hop control shows the same hops at once, and the other way round", async ({ page }) => {
  const fake = new FakeService();
  const { canvas } = await facilitySurfaceCanvas(page, fake);
  await pickContract(page, "drawdown-sector");
  await expect(formHops(page)).toHaveText([/drawn under/, /borrower/, /borrower sector/]);

  // Path mode starts from the carrier of the promotion, at the end of the path so far.
  await surfaceNode(canvas, "carrier").getByRole("button", { name: /^Build the read path/ }).click();
  await expect(trail(canvas)).toHaveText(["drawn under", "borrower", "borrower sector"]);
  // The class reached has its properties, outgoing on one side and incoming on the other, and a datatype property is marked as ending the path.
  for (const _ of [1, 2, 3]) await pathMode(canvas).getByRole("button", { name: "Undo the last hop" }).click();
  await expect(trail(canvas)).toHaveCount(0);
  await expect(formHops(page)).toHaveCount(0);
  await expect(option(canvas, "drawnUnder")).toContainText("Facility");
  await expect(option(canvas, "drawnAmount")).toContainText("ends the path");
  await expect(option(canvas, "hasDrawdown", "inverse")).toContainText("Facility");
  await expect(option(canvas, "drawnAmount", "inverse")).toHaveCount(0);

  // A click on a property adds the hop and moves to the class it reaches. A property of a class above it is offered of the class too.
  await option(canvas, "drawnUnder").click();
  await expect(trail(canvas)).toHaveText(["drawn under"]);
  await expect(formHops(page)).toHaveText([/drawn under/]);
  await expect(option(canvas, "drawnUnder", "inverse")).toContainText("Drawdown");
  await option(canvas, "borrower").click();
  await expect(option(canvas, "legalName")).toContainText("ends the path");
  await option(canvas, "legalName").click();
  await expect(trail(canvas)).toHaveText(["drawn under", "borrower", "legal name"]);
  await expect(formHops(page)).toHaveText([/drawn under/, /borrower/, /legal name/]);
  // A datatype property ends the path, so no property is offered after it.
  await expect(pathMode(canvas).locator(".path-option[data-property]")).toHaveCount(0);

  // An edit in the form shows on the canvas.
  await page.getByRole("button", { name: "Remove the last step" }).click();
  await expect(trail(canvas)).toHaveText(["drawn under", "borrower"]);
  await option(canvas, "borrower", "inverse").click();
  await expect(formHops(page)).toHaveText([/drawn under/, /borrower/, /borrower/]);
  await expect(page.getByLabel("Read path", { exact: true }).locator(".arrow").last()).toHaveText("←");
  // The canvas wrote what the form writes, which a compilation of the part sends.
  await pathMode(canvas).getByRole("button", { name: "Done" }).click();
  await expect(pathMode(canvas)).toHaveCount(0);
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  await expect.poll(() => fake.submitted.filter((s) => s.target === "surface").pop()?.body ?? "").toContain("srf:stepDirection srf:Inverse");
  const body = fake.submitted.filter((s) => s.target === "surface").pop()!.body;
  expect(body).not.toMatch(/drawdown-sector-promotion[^.]*srf:readProperty/);
  // Leaving path mode kept what was written, and the picture draws it.
  await expect(canvas.locator(".onto-edge-label").filter({ hasText: /^(drawn under|borrower|← borrower)$/ })).toHaveCount(3);
});

test("a named source is drawn in path mode as the path the name stands for and edits nothing, and one action replaces it with a path, which a closure is then added to as a SHACL path", async ({ page }) => {
  const fake = new FakeService();
  const { canvas } = await facilitySurfaceCanvas(page, fake);
  await pickContract(page, "facility-refinancing");
  await surfaceNode(canvas, "class").filter({ hasText: "Members" }).getByRole("button", { name: /^Build the members path/ }).click();
  // The expansion names a source, which stands for the property one or more times. The path is drawn, marked as given by the name, with nothing to edit.
  await expect(trail(canvas)).toHaveText(["refinances +"]);
  await expect(pathMode(canvas)).toContainText("given by the name");
  await expect(pathMode(canvas).getByRole("status")).toContainText("Path mode edits nothing while the name is stated");
  await expect(pathMode(canvas).getByRole("group", { name: /^Closure of/ })).toHaveCount(0);
  await expect(pathMode(canvas).getByRole("button", { name: "Undo the last hop" })).toBeDisabled();
  await expect(pathMode(canvas).locator(".path-option[data-property]")).toHaveCount(0);
  await expect(pathMode(canvas).locator(".path-option.given")).toHaveCount(1);
  // Leaving path mode wrote nothing, so a compilation still sends the named source and no path.
  await pathMode(canvas).getByRole("button", { name: "Done" }).click();
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  await expect.poll(() => fake.submitted.filter((s) => s.kind === "compile" && s.target === "surface").length).toBe(1);
  const before = fake.submitted.filter((s) => s.kind === "compile" && s.target === "surface").pop()!.body;
  expect(before).toContain("srf:TransitiveClosure");
  expect(before).not.toContain("sh:oneOrMorePath");
  expect(before).not.toContain("srf:membersPath");

  // The one action removes the named source and writes the path in the same edit, and only then can the path be edited.
  await surfaceNode(canvas, "class").filter({ hasText: "Members" }).getByRole("button", { name: /^Build the members path/ }).click();
  await pathMode(canvas).getByRole("button", { name: "Replace the named source with a path" }).click();
  await expect(trail(canvas)).toHaveText(["refinances +"]);
  await expect(pathMode(canvas)).not.toContainText("given by the name");
  await expect(pathMode(canvas).getByRole("button", { name: "One or more times: refinances" })).toHaveAttribute("aria-pressed", "true");
  await expect(pathMode(canvas).getByRole("button", { name: "Replace the named source with a path" })).toHaveCount(0);
  // Zero or more instead, and the path is stated as srf:membersPath in place of the named source.
  await pathMode(canvas).getByRole("button", { name: "Zero or more times: refinances" }).click();
  await expect(trail(canvas)).toHaveText(["refinances *"]);
  await expect(pathMode(canvas).getByRole("button", { name: "Zero or more times: refinances" })).toHaveAttribute("aria-pressed", "true");
  await expect(pathMode(canvas).getByRole("button", { name: "One or more times: refinances" })).toHaveAttribute("aria-pressed", "false");
  await pathMode(canvas).getByRole("button", { name: "Done" }).click();
  await expect(canvas.locator(".onto-edge-label.dashed").filter({ hasText: "refinances *" })).toBeVisible();
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  await expect.poll(() => fake.submitted.filter((s) => s.kind === "compile" && s.target === "surface").length).toBe(2);
  const body = fake.submitted.filter((s) => s.kind === "compile" && s.target === "surface").pop()!.body;
  expect(body).toContain("sh:zeroOrMorePath");
  expect(body).not.toContain("srf:TransitiveClosure");
  // The form of the statement states the path too, and the toggle takes it off.
  await surfaceNode(canvas, "class").filter({ hasText: "Members" }).getByRole("button", { name: /^Build the members path/ }).click();
  await pathMode(canvas).getByRole("button", { name: "Zero or more times: refinances" }).click();
  await expect(trail(canvas)).toHaveText(["refinances"]);
  await pathMode(canvas).getByRole("button", { name: "Done" }).click();
  await expect(canvas.locator(".onto-edge-label").filter({ hasText: /^(⚠ )?refinances$/ })).toBeVisible();
});

// --- the surface canvas, the expression editor (SVA-S1 part 3) ------------------------------------------------------------------------

const EXPR = "https://example.org/lending#";
const DERIVED_AS = "https://www.nebularis.org/neuro-semantic/lattice/surface#derivedAs";
const editorOf = (canvas: Locator) => canvas.getByRole("region", { name: "Expression editor" });
const lineOf = (canvas: Locator) => editorOf(canvas).getByRole("status", { name: "Expression as a line" }).locator("code");
const exprNode = (canvas: Locator, slot: string) => editorOf(canvas).locator(`.expr-node[data-slot="${slot}"]`);
const rootNode = (canvas: Locator) => exprNode(canvas, `${EXPR}fm-target|${DERIVED_AS}`);
const undoEdit = (page: Page) => page.getByRole("button", { name: "Undo", exact: true }).click();

test("the facility derivation opens in the expression editor from its result edge as a line, switches to a tree that is remembered, changes the product to a quotient, shows the datatype mark and the line change, and undoes it", async ({ page }) => {
  const fake = new FakeService();
  const { ws, canvas } = await facilitySurfaceCanvas(page, fake);
  await pickContract(page, "facility-margin");
  await expect(editorOf(canvas)).toHaveCount(0);

  // A click on the result edge itself opens it, and so does a click on its label. It opens as the one line of text, which is read only.
  const edge = canvas.locator(".react-flow__edge").filter({ has: page.locator("title", { hasText: "is written margin weighted commitment as commitment × margin : decimal" }) });
  const point = await edge.locator("path.react-flow__edge-path").evaluate((p: SVGPathElement) => {
    const at = p.getPointAtLength(p.getTotalLength() * 0.15);
    const m = p.getScreenCTM()!;
    return { x: at.x * m.a + m.e, y: at.y * m.d + m.f };
  });
  await page.mouse.click(point.x, point.y);
  await expect(editorOf(canvas)).toBeVisible();
  await expect(lineOf(canvas)).toHaveText("commitment × margin : decimal");
  await expect(editorOf(canvas).getByRole("group", { name: "Expression tree" })).toHaveCount(0);
  await expect(editorOf(canvas).getByRole("button", { name: "Line" })).toHaveAttribute("aria-pressed", "true");
  // The form beside it shows the binding that states the expression.
  await expect(page).toHaveURL(/fm-target$/);
  await editorOf(canvas).getByRole("button", { name: "Done" }).click();
  await expect(editorOf(canvas)).toHaveCount(0);
  await canvas.locator(".onto-edge-label").filter({ hasText: "commitment × margin : decimal" }).click();
  await expect(editorOf(canvas)).toBeVisible();

  // The tree has a node for the product and one for each operand, each with its datatype, and no mark.
  await editorOf(canvas).getByRole("button", { name: "Tree" }).click();
  await expect(editorOf(canvas).locator(".expr-node")).toHaveCount(3);
  await expect(rootNode(canvas)).toContainText("Product");
  await expect(rootNode(canvas)).toHaveAttribute("data-datatype", "decimal");
  await expect(exprNode(canvas, `${EXPR}fm-expression|https://www.nebularis.org/neuro-semantic/lattice/surface#leftOperand`)).toContainText("commitment");
  await expect(editorOf(canvas).locator(".expr-mark")).toHaveCount(0);
  // The choice of rendering is kept in this browser for the workspace.
  expect(await page.evaluate((key) => localStorage.getItem(key), `lattice-studio:expression-view:${ws}`)).toBe("tree");

  // The product becomes a quotient. Both operands stay, the line changes, and a quotient of two decimals is a decimal, so nothing is marked.
  await rootNode(canvas).getByLabel("Kind").selectOption("quotient");
  await expect(lineOf(canvas)).toHaveText("commitment ÷ margin : decimal");
  await expect(rootNode(canvas)).toContainText("Quotient");
  await expect(rootNode(canvas)).toHaveAttribute("data-datatype", "decimal");
  await expect(editorOf(canvas).locator(".expr-mark")).toHaveCount(0);
  // The author states another datatype, and the node marks where it disagrees with the rules, as the line changes with it.
  await rootNode(canvas).getByLabel("Result datatype").selectOption({ label: "integer" });
  await expect(rootNode(canvas).locator('.expr-mark[data-mark="disagrees"]')).toContainText("states integer, the operands give decimal");
  await expect(rootNode(canvas).locator('.expr-mark[data-mark="result"]')).toContainText("the result binding states decimal");
  await expect(lineOf(canvas)).toHaveText("commitment ÷ margin : integer");
  await expect(rootNode(canvas)).toHaveAttribute("data-datatype", "integer");
  // The mark offers the datatype that agrees, and using it is one edit too.
  await rootNode(canvas).getByRole("button", { name: "Use decimal" }).click();
  await expect(editorOf(canvas).locator(".expr-mark")).toHaveCount(0);
  await expect(lineOf(canvas)).toHaveText("commitment ÷ margin : decimal");
  // Each change was one edit, so three undos are the way back.
  await undoEdit(page);
  await expect(rootNode(canvas).locator('.expr-mark[data-mark="disagrees"]')).toBeVisible();
  await undoEdit(page);
  await expect(lineOf(canvas)).toHaveText("commitment ÷ margin : decimal");
  await expect(editorOf(canvas).locator(".expr-mark")).toHaveCount(0);
  await undoEdit(page);
  await expect(lineOf(canvas)).toHaveText("commitment × margin : decimal");
  await expect(rootNode(canvas)).toContainText("Product");
  await expect(page.getByRole("button", { name: "Undo", exact: true })).toBeDisabled();

  // The tree is what the editor opens as next time, and the line is one click away.
  await editorOf(canvas).getByRole("button", { name: "Done" }).click();
  await page.reload();
  await page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Canvas" }).click();
  await pickContract(page, "facility-margin");
  await canvas.getByRole("button", { name: "Edit expression" }).click();
  await expect(editorOf(canvas).getByRole("group", { name: "Expression tree" })).toBeVisible();
  await expect(editorOf(canvas).getByRole("button", { name: "Tree" })).toHaveAttribute("aria-pressed", "true");
  await editorOf(canvas).getByRole("button", { name: "Line" }).click();
  await expect(editorOf(canvas).getByRole("group", { name: "Expression tree" })).toHaveCount(0);
});

test("a rounding of a sum is built from Add an expression, offering the contract's evidence and no cycle, and what a compilation sends is the expression", async ({ page }) => {
  const fake = new FakeService();
  const { canvas } = await facilitySurfaceCanvas(page, fake);
  await pickContract(page, "facility-margin");
  await canvas.getByRole("button", { name: "Edit expression" }).click();
  await editorOf(canvas).getByRole("button", { name: "Tree" }).click();
  // The binding states an expression, so there is nothing to add until it is removed, which leaves the derivation with none.
  await expect(editorOf(canvas).getByRole("group", { name: "Add an expression" })).toHaveCount(0);
  await rootNode(canvas).getByRole("button", { name: "Remove the expression" }).click();
  await expect(editorOf(canvas).locator(".expr-node")).toHaveCount(0);
  await expect(lineOf(canvas)).toHaveCount(0);
  const add = editorOf(canvas).getByRole("group", { name: "Add an expression" });
  await expect(add).toBeVisible();

  await add.getByLabel("Kind of the new expression").selectOption({ label: "Rounding" });
  await add.getByRole("button", { name: "Add an expression" }).click();
  await expect(lineOf(canvas)).toHaveText("round(…, …) : decimal");
  await expect(rootNode(canvas)).toContainText("Rounding");
  // Each missing part is a placeholder, marked.
  await expect(editorOf(canvas).locator(".expr-node.missing")).toHaveCount(1);
  await expect(editorOf(canvas).locator('.expr-mark[data-mark="no-scale"]')).toHaveText(/the scale is missing/);

  // An operand is set to a new sum, which the editor names in the baseline's namespace.
  await editorOf(canvas).locator(".expr-node.missing").getByLabel("Set the rounded operand").selectOption("new:sum");
  await expect(lineOf(canvas)).toHaveText("round(… + …, …) : decimal");
  // Only the contract's own evidence is offered, never its subject or its result target, and no expression that would be its own operand.
  const left = editorOf(canvas).locator(".expr-node.missing").first().getByLabel("Set the left operand");
  const offered = await left.locator("option").allTextContents();
  expect(offered).toEqual(["choose…", "commitment : decimal", "margin : decimal", "Sum", "Difference", "Product", "Quotient", "Rounding", "Choice", "A typed literal…"]);
  expect(await left.locator("option[value^=existing]").count()).toBe(0);
  await left.selectOption({ label: "commitment : decimal" });
  await editorOf(canvas).locator(".expr-node.missing").getByLabel("Set the right operand").selectOption({ label: "margin : decimal" });
  await expect(lineOf(canvas)).toHaveText("round(commitment + margin, …) : decimal");
  // A scale may be negative, and a value that is no whole number is refused where it is typed.
  const scale = rootNode(canvas).getByLabel("Scale");
  await scale.fill("two");
  await expect(rootNode(canvas)).toContainText("a whole number");
  await scale.fill("-2");
  await scale.press("Enter");
  await expect(lineOf(canvas)).toHaveText("round(commitment + margin, -2) : decimal");
  await scale.fill("2");
  await scale.press("Enter");
  await expect(lineOf(canvas)).toHaveText("round(commitment + margin, 2) : decimal");
  await expect(editorOf(canvas).locator(".expr-mark")).toHaveCount(0);
  // A typed literal as the sum's right operand, with its value and datatype, and then the evidence again.
  const sum = editorOf(canvas).locator(".expr-node.binary");
  await expect(sum).toHaveCount(1);
  await editorOf(canvas).locator('.expr-node.operand').filter({ hasText: "margin" }).getByLabel("Set the right operand").selectOption("literal");
  await editorOf(canvas).getByLabel("Literal value").fill("abc");
  await expect(editorOf(canvas).getByRole("button", { name: "Set", exact: true })).toBeDisabled();
  await editorOf(canvas).getByLabel("Literal value").fill("1.5");
  await editorOf(canvas).getByRole("button", { name: "Set", exact: true }).click();
  await expect(lineOf(canvas)).toHaveText("round(commitment + 1.5, 2) : decimal");
  await expect(editorOf(canvas).locator(".expr-node.literal")).toHaveAttribute("data-datatype", "decimal");
  await undoEdit(page);
  await expect(lineOf(canvas)).toHaveText("round(commitment + margin, 2) : decimal");

  // What a compilation sends states the rounding of the sum, with the scale an integer, and the product the derivation started with is gone.
  await editorOf(canvas).getByRole("button", { name: "Done" }).click();
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  await expect.poll(() => fake.submitted.filter((s) => s.kind === "compile" && s.target === "surface").length).toBe(1);
  const body = fake.submitted.filter((s) => s.kind === "compile" && s.target === "surface").pop()!.body;
  expect(body).toContain("srf:RoundingExpression");
  expect(body).toContain("srf:SumExpression");
  expect(body).toContain('srf:roundingScale 2');
  expect(body).toContain("ex:FacilityMarginExpression");
  expect(body).not.toContain("srf:ProductExpression");
});

// --- the construction, join and expansion editors (SVA-S1 part 4) ----------------------------------------------------------------------------

const editorRegion = (canvas: Locator, name: string) => canvas.getByRole("region", { name });
const compiledBody = async (fake: FakeService, canvas: Locator) => {
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  await expect.poll(() => fake.submitted.filter((s) => s.kind === "compile" && s.target === "surface").length).toBeGreaterThan(0);
  return fake.submitted.filter((s) => s.kind === "compile" && s.target === "surface").pop()!.body;
};

test("a keyed construction is built from Add a construction, with the key marked until it names a part, and what a compilation sends is the construction", async ({ page }) => {
  const fake = new FakeService();
  const { canvas } = await facilitySurfaceCanvas(page, fake);
  await pickContract(page, "borrower-exposure");
  // The box of the statement and the toolbar both open the editor, which shows the statement's node in the form.
  await surfaceNode(canvas, "statement").click();
  const editor = editorRegion(canvas, "Construction editor");
  await expect(editor).toBeVisible();
  await expect(page).toHaveURL(/be-node$/);
  await expect(editor.locator(".stmt-mark")).toHaveCount(0);
  await editor.getByRole("button", { name: "Remove the construction" }).click();
  await expect(editor.getByRole("group", { name: "Add a construction" })).toBeVisible();
  await expect(editor.locator('.stmt-mark[data-mark="required"]')).toContainText("srf:P10");
  await editor.getByRole("button", { name: "Add a construction", exact: true }).click();
  // A node for each instance, the identity that merges nothing, with its class and values still to state.
  await expect(editor.getByRole("radio", { name: "For each instance" })).toBeChecked();
  await expect(editor.locator('.stmt-mark[data-mark="class"]')).toBeVisible();
  await expect(editor.locator('.stmt-mark[data-mark="writes"]')).toBeVisible();
  await editor.getByLabel("Class", { exact: true }).selectOption({ label: "Borrower exposure" });
  await expect(editor.locator('.stmt-mark[data-mark="class"]')).toHaveCount(0);
  // A key names required evidence, and a node by key that names no part is marked until it does.
  await expect(editor.getByRole("group", { name: "Key" })).toHaveCount(0);
  await editor.getByRole("radio", { name: "By a key" }).check();
  await expect(editor.locator('.stmt-mark[data-mark="key-parts"]')).toContainText("srf:P24");
  await expect(editor.getByRole("group", { name: "Key" }).getByRole("checkbox")).toHaveCount(1);
  await editor.getByRole("checkbox", { name: /Key part borrower/ }).check();
  await expect(editor.locator('.stmt-mark[data-mark="key-parts"]')).toHaveCount(0);
  await editor.getByLabel("New property", { exact: true }).selectOption({ label: "exposure of" });
  await editor.getByLabel("New value read from", { exact: true }).selectOption({ label: "borrower (required)" });
  await editor.getByRole("button", { name: "Add a value" }).click();
  await expect(editor.locator(".stmt-mark")).toHaveCount(0);
  await expect(editor.getByRole("list", { name: "Values it writes" }).locator("[data-write]")).toHaveCount(1);
  // The drawing follows, and a compilation sends the construction.
  await editor.getByRole("button", { name: "Done" }).click();
  await expect(surfaceNode(canvas, "statement")).toContainText("Borrower exposure");
  await expect(surfaceNode(canvas, "statement")).toContainText("identity: by key (borrower)");
  await expect(surfaceNode(canvas, "statement")).toContainText("exposure of ← borrower");
  const body = await compiledBody(fake, canvas);
  expect(body).toContain("srf:ByKey");
  expect(body).toContain("ex:BorrowerExposureNode");
  expect(body).toContain("srf:keyBinding ex:be-borrower");
});

test("a composite key pair is added to the facility join, a rule is set and returned to its default, and a removed pair leaves its bindings marked as read by nothing until they are removed in one action", async ({ page }) => {
  const fake = new FakeService();
  const { canvas } = await facilitySurfaceCanvas(page, fake);
  await pickContract(page, "facility-branch");
  await surfaceNode(canvas, "statement").getByRole("button", { name: /^Edit join/ }).click();
  const editor = editorRegion(canvas, "Join editor");
  await expect(editor.locator("[data-pair]")).toHaveCount(1);
  await expect(editor.getByLabel("Second carrier", { exact: true })).toHaveValue(/#Branch$/);
  await expect(editor.locator(".stmt-mark")).toHaveCount(0);
  // The second carrier is never the contract's own, and the left side offers the first carrier's properties.
  expect(await editor.getByLabel("Second carrier", { exact: true }).locator("option").allTextContents()).not.toContain("Facility");
  await editor.getByLabel("New left binding").selectOption({ label: "facility reference" });
  await editor.getByLabel("New right binding").selectOption({ label: "branch code" });
  await editor.getByLabel("New pair compared as").selectOption({ label: "string" });
  await editor.getByRole("button", { name: "Add a key pair" }).click();
  await expect(editor.locator("[data-pair]")).toHaveCount(2);
  await expect(editor.locator(".stmt-mark")).toHaveCount(0);
  // The rules state their defaults, and an explicit choice is returned to its default.
  await expect(editor.locator('[data-rule="matches"]')).toContainText("States nothing, which means at most one.");
  await editor.getByLabel("One value finds").selectOption("AnyNumber");
  await expect(editor.locator('[data-rule="matches"]')).toContainText("States any number. The default is at most one.");
  await editor.getByRole("button", { name: "Done" }).click();
  await expect(surfaceNode(canvas, "statement")).toContainText("one value finds: any number");
  await expect(canvas.locator(".onto-edge-label").filter({ hasText: /^= : string$/ })).toHaveCount(1);
  let body = await compiledBody(fake, canvas);
  expect(body).toContain("srf:joinMatches srf:AnyNumber");
  await canvas.getByRole("button", { name: "Edit join", exact: true }).click();
  await editor.getByLabel("One value finds").selectOption("default");
  await expect(editor.locator('[data-rule="matches"]')).toContainText("States nothing");
  // Removing the added pair takes the pair alone. Its two bindings stay, and the canvas marks each as read by nothing.
  await editor.locator("[data-pair$=FacilityBranchKey]").getByRole("button", { name: "Remove the key pair" }).click();
  await expect(editor.locator("[data-pair]")).toHaveCount(1);
  await editor.getByRole("button", { name: "Done" }).click();
  await expect(canvas.locator(".surface-findings li").filter({ hasText: "No statement reads this binding. As required evidence it still excludes an instance that lacks the value." })).toHaveCount(2);
  // One action removes both, and the marks go with them.
  await canvas.getByRole("button", { name: "Remove unused bindings (2)" }).click();
  await expect(canvas.locator(".surface-findings li").filter({ hasText: "No statement reads this binding." })).toHaveCount(0);
  await expect(canvas.getByRole("button", { name: /^Remove unused bindings/ })).toHaveCount(0);
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  await expect.poll(() => fake.submitted.filter((s) => s.kind === "compile" && s.target === "surface").length).toBe(2);
  body = fake.submitted.filter((s) => s.kind === "compile" && s.target === "surface").pop()!.body;
  expect(body).not.toContain("srf:joinMatches");
  expect(body).not.toContain("FacilityBranchFacilityReference");
});

test("the facility expansion is changed from its named source to a path and given a node for each member with a stable name", async ({ page }) => {
  const fake = new FakeService();
  const { canvas } = await facilitySurfaceCanvas(page, fake);
  await pickContract(page, "facility-refinancing");
  await surfaceNode(canvas, "class").filter({ hasText: "Members" }).getByRole("button", { name: /^Edit expansion/ }).click();
  const editor = editorRegion(canvas, "Expansion editor");
  await expect(editor.locator(".stmt-mark")).toHaveCount(0);
  await expect(editor.getByLabel("Named source")).toHaveValue(/TransitiveClosure$/);
  await expect(editor.getByRole("list", { name: "The path the name stands for" })).toContainText("refinances+");
  // The property each member is written as is never the one the members are reached by (srf:P21).
  await editor.getByRole("button", { name: "Pick the property each member is written as on the canvas" }).click();
  await expect(canvas.getByRole("region", { name: "Path mode" })).toBeVisible();
  await expect(canvas.locator('.path-option[data-property$="#refinances"]')).toHaveCount(0);
  await expect(canvas.locator('.path-option[data-property$="#hasDrawdown"]')).toHaveCount(1);
  await canvas.getByRole("region", { name: "Path mode" }).getByRole("button", { name: "Done" }).click();
  await expect(editor).toBeVisible();
  // The named source is replaced by the path it stands for, and then only evidence the path reads is offered.
  await editor.getByRole("button", { name: "Replace the named source with a path" }).click();
  await expect(editor.getByRole("list", { name: "Members path so far" })).toContainText("refinances+");
  await expect(editor.getByLabel("Use a named source")).toBeVisible();
  await expect(editor.locator(".stmt-mark")).toHaveCount(0);
  // A node for each member opens its own editor, which keeps the key to what the law names.
  await editor.getByRole("button", { name: "Add a node for each member" }).click();
  const member = editorRegion(canvas, "Node for each member editor");
  await expect(member).toBeVisible();
  await expect(member.getByRole("radio", { name: "For each instance and member" })).toBeChecked();
  await expect(member.getByRole("radio", { name: "The member itself" })).toBeVisible();
  await member.getByLabel("Class", { exact: true }).selectOption({ label: "Facility" });
  await member.getByLabel("Member name", { exact: true }).selectOption({ label: "facility reference" });
  await member.getByLabel("New property", { exact: true }).selectOption({ label: "facility reference" });
  await member.getByLabel("New value read from", { exact: true }).selectOption("member");
  await member.getByRole("button", { name: "Add a value" }).click();
  await expect(member.locator(".stmt-mark")).toHaveCount(0);
  // The member itself takes the name out, since it spells nothing (srf:P24).
  await member.getByRole("radio", { name: "The member itself" }).check();
  await expect(member.getByLabel("Member name", { exact: true })).toHaveCount(0);
  await member.getByRole("button", { name: "Done" }).click();
  await expect(surfaceNode(canvas, "statement")).toContainText("identity: the member itself");
  const body = await compiledBody(fake, canvas);
  expect(body).toContain("srf:MemberNode");
  expect(body).toContain("sh:oneOrMorePath");
  // The expansion states its path and no name, though the covenant projection's expansion still names its source.
  expect(body.match(/ex:fr-expansion a [^]*?\.\n/)![0]).not.toContain("srf:expansionSource");
  expect(body.match(/ex:fr-expansion a [^]*?\.\n/)![0]).toContain("srf:membersPath");
  expect(body).not.toContain("srf:memberName");
});

test("the loops of the class graph leave across the flow and the facility declares refinances", async ({ page }) => {
  const fake = new FakeService();
  const { ws } = await facilitySurfaceCanvas(page, fake);
  await page.goto(`/#/w/${ws}/baseline`);
  await page.getByRole("group", { name: "Detail pane" }).getByRole("button", { name: "Diagram" }).click();
  const diagram = page.getByRole("region", { name: "Ontology diagram" });
  for (const property of ["ex:refinances", "ex:refinancesInChain"]) {
    await expect(diagram.locator(".react-flow__edge").filter({ has: page.locator("title", { hasText: `${property}, from Facility to Facility` }) })).toHaveCount(1);
    await expect(diagram.locator(".onto-edge-label").filter({ hasText: new RegExp(`^${property}$`) })).toBeVisible();
  }
});

// --- the persistence simulator (SVA-P4) ---------------------------------------------------------------------------------------------------

test("the simulator creates a facility, changes it, loses a race as another writer and steps back, and the canvas lights each landing place a step wrote", async ({ page }) => {
  const fake = new FakeService();
  const { canvas } = await facilityPersistenceCanvas(page, fake);
  const journey = JSON.parse(readFileSync(join(import.meta.dirname, FIXTURE), "utf-8")) as Recorded;
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  await canvas.getByRole("combobox", { name: "Target" }).selectOption({ label: "Facility" });
  await expect(landingNode(canvas, "place")).toHaveCount(7);
  // Nothing is lit, and nothing runs, until the author presses Run.
  const lit = canvas.locator('.landing-node.place[data-lit="true"]');
  await expect(lit).toHaveCount(0);

  await page.getByRole("tab", { name: "Simulator" }).click();
  const pane = page.getByRole("region", { name: "Simulator", exact: true });
  await expect(pane.getByRole("combobox", { name: "Simulator target" })).toBeVisible();
  await pane.getByRole("combobox", { name: "Simulator target" }).selectOption({ label: "Facility" });
  const steps = pane.getByLabel("Steps in the sample world");
  const size = pane.getByLabel("Size of the sample world");
  await expect(steps).toHaveText("0 steps");
  await expect(size).toContainText("1 quad,");
  await expect(size).toContainText("of the 5.00 MiB request limit");
  await expect(pane.getByRole("button", { name: "Step back" })).toBeDisabled();
  expect(fake.runs.filter((r) => r.kind === "simulate")).toEqual([]);

  // The object is a form derived from the facility's boundary shape. The create is the only write the world can take, since the facility does not exist.
  await expect(pane.getByRole("group", { name: "Write" }).getByRole("button", { name: "Create" })).toHaveAttribute("aria-pressed", "true");
  await expect(pane.getByRole("group", { name: "Write" }).getByRole("button", { name: "Append" })).toBeDisabled();
  await expect(pane.getByRole("checkbox", { name: "As another writer" })).toBeDisabled();
  await expect(pane.getByRole("textbox", { name: "Root" })).toHaveValue(ROOT);
  await pane.getByRole("textbox", { name: "facility reference" }).fill(FACILITY.facilityReference);
  await pane.getByRole("textbox", { name: "commitment" }).fill(FACILITY.commitment);
  await pane.getByRole("textbox", { name: "margin", exact: true }).fill(STEPS[0].margin);
  await pane.getByRole("textbox", { name: "arranged by" }).fill(FACILITY.arrangedBy);
  await pane.getByRole("textbox", { name: "borrower" }).fill(FACILITY.borrower);
  await pane.getByRole("textbox", { name: "lender" }).fill(FACILITY.lender.join("\n"));
  await pane.getByRole("button", { name: "Add a drawdown" }).click();
  await pane.getByRole("textbox", { name: "drawn amount" }).fill(FACILITY.drawdown.amount);
  await pane.getByRole("textbox", { name: "drawdown date" }).fill(FACILITY.drawdown.date);
  expect(fake.runs.filter((r) => r.kind === "simulate")).toEqual([]);

  // Step 1, a create.
  await pane.getByRole("button", { name: "Run", exact: true }).click();
  const outcome = pane.getByRole("region", { name: "The outcome" });
  await expect(outcome.locator(".chip.outcome")).toHaveText("Applied");
  await expect(outcome.locator("dd").filter({ hasText: "urn:rev:facility-1/1" })).toBeVisible();
  await expect(outcome.locator("dd").filter({ hasText: "Apache Jena ARQ" })).toBeVisible();
  await expect(pane.getByRole("region", { name: "The checks" }).getByText("payloadCheck")).toBeVisible();
  await expect(pane.getByRole("region", { name: "The request" })).toContainText("NOW()");
  const delta = pane.getByRole("region", { name: "The delta" });
  await expect(delta.getByRole("region", { name: /^Landing place Data graph/ })).toContainText("urn:g:facilities");
  await expect(delta.getByRole("region", { name: /^Landing place Patch log, the triples added/ })).toContainText("urn:rev:facility-1/1/add");
  await expect(delta.getByRole("region", { name: /^Landing place Patch log, the triples removed/ })).toHaveCount(0);
  await expect(steps).toHaveText("1 step");
  const created = await size.textContent();
  // The canvas lights the five places the create wrote, and not the keys or the removed patch log.
  await expect(lit).toHaveCount(5);
  await expect(landingNode(canvas, "place").filter({ hasText: "{newRev}/add" })).toHaveAttribute("data-lit", "true");
  await expect(landingNode(canvas, "place").filter({ hasText: "{newRev}/del" })).toHaveAttribute("data-lit", "false");
  await expect(landingNode(canvas, "place").filter({ hasText: "urn:g:keys" })).toHaveAttribute("data-lit", "false");

  // Step 2, a replace that changes the margin. The facility is in the sample world now, so the form still holds it.
  await pane.getByRole("group", { name: "Write" }).getByRole("button", { name: "Replace" }).click();
  await expect(pane.getByRole("combobox", { name: "Operation by name" })).toHaveValue("cas-replace");
  await expect(pane.getByRole("checkbox", { name: "As another writer" })).toBeEnabled();
  await pane.getByRole("textbox", { name: "margin", exact: true }).fill(STEPS[1].margin);
  await pane.getByRole("button", { name: "Run", exact: true }).click();
  await expect(steps).toHaveText("2 steps");
  await expect(outcome.locator("dd").filter({ hasText: "urn:rev:facility-1/2" })).toBeVisible();
  await expect(delta.getByRole("region", { name: /^Landing place Patch log, the triples removed/ })).toBeVisible();
  await expect(delta.getByRole("region", { name: /^Landing place Data graph/ }).locator("pre.removed")).toContainText(`- <${ROOT}> <${EX}margin> "3.25"`);
  await expect(lit).toHaveCount(6);
  await expect(landingNode(canvas, "place").filter({ hasText: "{newRev}/del" })).toHaveAttribute("data-lit", "true");
  const replaced = await size.textContent();
  expect(replaced).not.toBe(created);

  // Step 3, the same change as another writer, from the position before the world's. The guard refuses it, and the world stays where it was.
  await pane.getByRole("textbox", { name: "margin", exact: true }).fill(STEPS[2].margin);
  await pane.getByRole("checkbox", { name: "As another writer" }).check();
  await expect(pane.getByText("The step is sent from position 1, one before the sample world's, so the guard refuses it.")).toBeVisible();
  await pane.getByRole("button", { name: "Run", exact: true }).click();
  await expect(outcome.locator(".chip.outcome")).toHaveText("Lost race");
  await expect(outcome.locator(".sim-outcome strong")).toHaveText("PreconditionFailed");
  await expect(outcome.locator("p.small")).toContainText("The version row is at position 2, not 1");
  await expect(steps).toHaveText("2 steps");
  await expect(size).toHaveText(replaced!);
  await expect(lit).toHaveCount(0);
  await expect(delta).toContainText("The step changed no graph.");

  // The requests were the journey's, and each ran once, since nothing runs until Run is pressed.
  const sent = fake.runs.filter((r) => r.kind === "simulate");
  expect(sent.map((r) => [r.target, r.mediaType, r.wait])).toEqual([["persistence", "application/trig", true], ["persistence", "application/trig", true], ["persistence", "application/trig", true]]);
  expect(sent.map((r) => r.body)).toEqual(journey.steps.slice(0, STEPS.length).map((s) => s.body));

  // Step back removes the change, and the world is the one the create left.
  await pane.getByRole("button", { name: "Step back" }).click();
  await expect(steps).toHaveText("1 step");
  await expect(size).toHaveText(created!);
  await expect(lit).toHaveCount(0);
  await expect(pane.getByRole("list", { name: "Steps taken" }).getByRole("listitem")).toHaveText(["create-if-absent on facility-1 to urn:rev:facility-1/1"]);
  await pane.getByRole("button", { name: "Step back" }).click();
  await expect(steps).toHaveText("0 steps");
  await expect(size).toContainText("1 quad,");
  await expect(pane.getByRole("button", { name: "Step back" })).toBeDisabled();
});

test("the simulator generates a facility from its boundary shape, and creates it", async ({ page }) => {
  const fake = new FakeService();
  const { canvas } = await facilityPersistenceCanvas(page, fake);
  const journey = JSON.parse(readFileSync(join(import.meta.dirname, FIXTURE), "utf-8")) as Recorded;
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  await page.getByRole("tab", { name: "Simulator" }).click();
  const pane = page.getByRole("region", { name: "Simulator", exact: true });
  await pane.getByRole("combobox", { name: "Simulator target" }).selectOption({ label: "Facility" });
  // Nothing is generated until the author asks, and the form starts empty.
  await expect(pane.getByRole("textbox", { name: "margin", exact: true })).toHaveValue("");
  await expect(pane.getByRole("status", { name: "Left for the author" })).toHaveCount(0);
  await pane.getByRole("button", { name: "Generate from the shape" }).click();
  // The facility sample's boundary shape requires a reference, a commitment and a margin and nothing else, so those three are given and nothing is left for the author.
  await expect(pane.getByRole("status", { name: "Left for the author" })).toContainText("The shape's requirements are all met");
  await expect(pane.getByRole("textbox", { name: "Root" })).toHaveValue(ROOT);
  await expect(pane.getByRole("textbox", { name: "facility reference" })).not.toHaveValue("");
  await expect(pane.getByRole("textbox", { name: "commitment", exact: true })).not.toHaveValue("");
  await expect(pane.getByRole("textbox", { name: "margin", exact: true })).not.toHaveValue("");
  expect(fake.runs.filter((r) => r.kind === "simulate")).toEqual([]);
  await pane.getByRole("button", { name: "Run", exact: true }).click();
  const outcome = pane.getByRole("region", { name: "The outcome" });
  await expect(outcome.locator(".chip.outcome")).toHaveText("Applied");
  await expect(outcome.locator("dd").filter({ hasText: "urn:rev:facility-1/1" })).toBeVisible();
  await expect(pane.getByRole("region", { name: "The checks" }).getByText("payloadCheck")).toBeVisible();
  await expect(pane.getByLabel("Steps in the sample world")).toHaveText("1 step");
  // The step is the one the journey's fixture holds for the generated facility, which the run worker answered.
  expect(fake.runs.filter((r) => r.kind === "simulate").map((r) => r.body)).toEqual([journey.steps[STEPS.length].body]);
});

test("the simulator keeps its sample world while the author looks at another view, and an object can be given as Turtle", async ({ page }) => {
  const fake = new FakeService();
  const { ws, canvas } = await facilityPersistenceCanvas(page, fake);
  await canvas.getByRole("button", { name: "Compile", exact: true }).click();
  await page.getByRole("tab", { name: "Simulator" }).click();
  const pane = page.getByRole("region", { name: "Simulator", exact: true });
  await pane.getByRole("combobox", { name: "Simulator target" }).selectOption({ label: "Facility" });
  await pane.getByRole("group", { name: "Object source" }).getByRole("button", { name: "Turtle" }).click();
  // A blank node is refused before anything is sent, since a payload holds none.
  await pane.getByRole("textbox", { name: "Object as Turtle" }).fill(`@prefix ex: <${EX}> . ex:facility-1 a ex:Facility ; ex:lender [ ex:legalName "x" ] .`);
  await expect(pane.getByRole("alert")).toContainText("blank node");
  await expect(pane.getByRole("button", { name: "Run", exact: true })).toBeDisabled();
  await pane.getByRole("textbox", { name: "Object as Turtle" }).fill(`@prefix ex: <${EX}> . ex:facility-1 a ex:Facility ; ex:margin 3.25 .`);
  await expect(pane.getByRole("alert")).toHaveCount(0);
  await expect(pane.getByRole("button", { name: "Run", exact: true })).toBeEnabled();
  await expect(pane.getByLabel("Size of the step")).toContainText("The step is");
  // A step that is not one the fake has frames for is one failed run, and moves no world.
  await pane.getByRole("button", { name: "Run", exact: true }).click();
  await expect(pane.getByRole("status", { name: "Simulator status" })).toContainText("Failed");
  await expect(pane.getByLabel("Steps in the sample world")).toHaveText("0 steps");
  expect(fake.runs.filter((r) => r.kind === "simulate")).toHaveLength(1);
  await page.goto(`/#/w/${ws}/overview`);
  await page.goto(`/#/w/${ws}/persistence`);
  await page.getByRole("tab", { name: "Simulator" }).click();
  await expect(page.getByRole("region", { name: "Simulator", exact: true }).getByLabel("Steps in the sample world")).toHaveText("0 steps");
});
