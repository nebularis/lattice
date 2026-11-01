import { expect, test, type Page } from "@playwright/test";
import { analysisView, detectionResult, loadFacilityAnalysis, loadFacilityTurtle, loadSample, loadTemplate, mockStudio, reportTurtle, textOffsetOf } from "./support";

const FACILITY_ELEMENT_11 = "00000001-0000-4000-8000-000000000011";
const FACILITY_ELEMENT_13 = "00000001-0000-4000-8000-000000000013";

async function insertFacilitySample(page: Page): Promise<void> {
  const doc = page.locator('section[aria-label="Document"]');
  await doc.getByRole("listitem").filter({ hasText: "Facility Agreement (sample)" }).getByRole("button", { name: "Insert sample" }).click();
  await expect(doc.getByText("Sections")).toBeVisible();
}

function harnessModel(page: Page) {
  return page.evaluate(() => (window as unknown as { __harness: { model(): unknown } }).__harness.model());
}

function harnessMetadata(page: Page) {
  return page.evaluate(() => (window as unknown as { __harness: { metadata(): unknown } }).__harness.metadata());
}

function harnessSelect(page: Page, elementId: string, start: number, end: number) {
  return page.evaluate(
    ({ elementId, start, end }) => (window as unknown as { __harness: { select(e: string, s: number, n: number): void } }).__harness.select(elementId, start, end),
    { elementId, start, end },
  );
}

function tab(page: Page, name: string) {
  return page.locator("nav.tab-bar").getByRole("button", { name });
}

function harnessCommand(page: Page, id: string) {
  return page.evaluate(
    (commandId) => (window as unknown as { __harness: { command(id: string): Promise<void> } }).__harness.command(commandId),
    id,
  );
}

test("S9-02: a loaded catalogue shows Connected, the workspace and the templates and samples", async ({ page }) => {
  await mockStudio(page);
  await page.goto("harness.html");

  await expect(page.locator(".status-connected")).toHaveText("Connected");
  const doc = page.locator('section[aria-label="Document"]');
  await expect(doc.getByLabel("Workspace", { exact: true })).toHaveValue("0a1b2c3d-0000-4000-8000-000000000001");
  await expect(doc.locator("ul").nth(0).getByRole("listitem")).toHaveCount(2);
  await expect(doc.locator("ul").nth(1).getByRole("listitem")).toHaveCount(2);
});

test("S9-03: Apply template on the licence creates six sections, each element empty, with guidance shown", async ({ page }) => {
  await mockStudio(page);
  await page.goto("harness.html");

  const doc = page.locator('section[aria-label="Document"]');
  await doc.getByRole("listitem").filter({ hasText: "Software Licence" }).getByRole("button", { name: "Apply template" }).click();

  const template = loadTemplate("software-licence");
  await expect(page.getByText(template.sections[0].guidance)).toBeVisible();

  const model = (await harnessModel(page)) as { sections: { sectionKey: string; elements: { parts: { text: string }[] }[] }[] };
  expect(model.sections.map((section) => section.sectionKey)).toEqual(template.sections.map((section) => section.sectionKey));
  for (const section of model.sections) {
    expect(section.elements).toHaveLength(1);
    const text = section.elements[0].parts.map((part) => part.text).join("").trim();
    expect(text).toBe("");
  }
});

test("S9-04: Insert sample facility sets the model, metadata and a new documentId", async ({ page }) => {
  await mockStudio(page);
  await page.goto("harness.html");

  await insertFacilitySample(page);
  await expect(page.locator('section[aria-label="Document"]').getByText("Sections")).toBeVisible();

  const sample = loadSample("facility-agreement");
  await expect
    .poll(async () => {
      const model = (await harnessModel(page)) as { sections: unknown[] };
      return model.sections.length;
    })
    .toBe(sample.sections.length);

  const model = (await harnessModel(page)) as { sections: { sectionKey: string }[] };
  const metadata = (await harnessMetadata(page)) as { documentId: string; variables: unknown[] };

  expect(model.sections.map((section) => section.sectionKey)).toEqual(sample.sections.map((section) => section.sectionKey));
  expect(metadata.variables).toEqual(sample.variables);
  expect(metadata.documentId).not.toBe(sample.documentId);
});

test("S9-05: Mark variable turns the selected text into a variable part", async ({ page }) => {
  await mockStudio(page);
  await page.goto("harness.html");
  await insertFacilitySample(page);

  const sample = loadSample("facility-agreement");
  const { start, end } = textOffsetOf(sample, FACILITY_ELEMENT_11, "GBP 250");
  await harnessSelect(page, FACILITY_ELEMENT_11, start, end);

  await tab(page, "Markup").click();
  const markup = page.locator('section[aria-label="Markup"]');
  await markup.getByLabel("Key").fill("prepayment-fee");
  await markup.getByLabel("Label").fill("Prepayment fee");
  await markup.getByLabel("Value type").selectOption("money");
  await markup.getByRole("button", { name: "Mark variable" }).click();

  const model = (await harnessModel(page)) as {
    sections: { elements: { elementId: string; parts: { kind: string; variableKey?: string; text: string }[] }[] }[];
  };
  const element = model.sections.flatMap((section) => section.elements).find((candidate) => candidate.elementId === FACILITY_ELEMENT_11)!;
  const variablePart = element.parts.find((part) => part.kind === "variable" && part.variableKey === "prepayment-fee");
  expect(variablePart?.text).toBe("GBP 250");

  const metadata = (await harnessMetadata(page)) as { variables: { variableKey: string; valueType: string }[] };
  const declared = metadata.variables.find((variable) => variable.variableKey === "prepayment-fee");
  expect(declared?.valueType).toBe("money");
});

test("S9-06: Analyse saves the document as markup, runs the job and shows its findings", async ({ page }) => {
  const studio = await mockStudio(page);

  await page.goto("harness.html");
  await insertFacilitySample(page);
  await tab(page, "Analyse").click();
  await page.locator('section[aria-label="Analyse"]').getByRole("button", { name: "Analyse" }).click();

  await expect(page.getByText("Unmarked text outside every section")).toBeVisible();
  await expect(page.getByText("Job: succeeded")).toBeVisible();
  expect(studio.puts).toHaveLength(1);
  expect(studio.puts[0].ifMatch).toBe('"0"');
  expect(studio.puts[0].contentType).toBe("application/xml");
  expect(studio.puts[0].body).toContain("<template>facility-agreement</template>");
  expect(studio.jobSubmissions).toHaveLength(1);
  expect(studio.jobSubmissions[0]).toContain("kind=analyse&target=");
});

test("S9-07: a second Analyse sends the revision it kept, and a 412 shows as a conflict", async ({ page }) => {
  const studio = await mockStudio(page);

  await page.goto("harness.html");
  await insertFacilitySample(page);
  await tab(page, "Analyse").click();
  const analyse = page.locator('section[aria-label="Analyse"]').getByRole("button", { name: "Analyse" });
  await analyse.click();
  await expect(page.getByText("Job: succeeded")).toBeVisible();
  await analyse.click();
  await expect.poll(() => studio.puts.length).toBe(2);
  expect(studio.puts[1].ifMatch).toBe('"1"');

  await page.unroute("**/api/workspaces/*/documents/*");
  await page.route("**/api/workspaces/*/documents/*", (route) => route.fulfill({ status: 412, body: "" }));
  await analyse.click();
  await expect(page.getByRole("alert")).toContainText("Conflict");
});

test("S9-14: Accept a detection marks the suggested variable", async ({ page }) => {
  const sample = loadSample("facility-agreement");
  const agent = textOffsetOf(sample, FACILITY_ELEMENT_13, "[Agent]");
  const report = reportTurtle([
    detectionResult(FACILITY_ELEMENT_13, { kind: "placeholder", text: "[Agent]", ...agent, partIndex: 1, action: "mark-variable", valueType: "party", key: "agent" }),
  ]);
  await mockStudio(page, { report });

  await page.goto("harness.html");
  await insertFacilitySample(page);
  await tab(page, "Analyse").click();
  await page.locator('section[aria-label="Analyse"]').getByRole("button", { name: "Analyse" }).click();
  await expect(page.getByText("[Agent]")).toBeVisible();

  await page.locator('section[aria-label="Analyse"]').getByRole("button", { name: "Accept" }).click();

  const model = (await harnessModel(page)) as {
    sections: { elements: { elementId: string; parts: { kind: string; variableKey?: string; text: string }[] }[] }[];
  };
  const element = model.sections.flatMap((section) => section.elements).find((candidate) => candidate.elementId === FACILITY_ELEMENT_13)!;
  const variablePart = element.parts.find((part) => part.kind === "variable" && part.text === "[Agent]");
  expect(variablePart?.variableKey).toBe("agent");
});

test("S9-08: Logical English tab shows the facility reading", async ({ page }) => {
  await mockStudio(page);

  await page.goto("harness.html");
  await insertFacilitySample(page);
  await tab(page, "Analyse").click();
  await page.locator('section[aria-label="Analyse"]').getByRole("button", { name: "Analyse" }).click();
  await tab(page, "Logical English").click();

  const analysis = loadFacilityAnalysis();
  const le = page.locator('section[aria-label="Logical English"]');
  await expect(le.locator("ul").nth(1).getByRole("listitem")).toHaveCount(analysis.elements.length);
  await expect(le.locator(".legend li")).toHaveCount(8);
  await expect(le.locator("pre")).toHaveText(analysis.leProgram);
});

test("S9-09: Graph tab renders the diagram and the Turtle toggle shows the document graph and the proposals", async ({ page }) => {
  await mockStudio(page);

  await page.goto("harness.html");
  await insertFacilitySample(page);
  await tab(page, "Analyse").click();
  await page.locator('section[aria-label="Analyse"]').getByRole("button", { name: "Analyse" }).click();
  await tab(page, "Graph").click();

  const analysis = loadFacilityAnalysis();
  const graph = page.locator('section[aria-label="Graph"]');
  await expect(graph.locator("svg")).toBeVisible();
  const nodeCount = await graph.locator("svg .node").count();
  expect(nodeCount).toBe(analysis.graphView.nodes.length);

  await graph.getByRole("button", { name: "Turtle" }).click();
  await expect(graph.getByLabel("Document graph")).toContainText("cst:revision");
  await expect(graph.getByLabel("Proposals")).toContainText(loadFacilityTurtle().slice(0, 30));
});

test("S9-10: workspaces that cannot be listed show Disconnected, and a failed save shows an error banner", async ({ page }) => {
  await mockStudio(page, { workspacesDown: true });
  await page.goto("harness.html");
  await expect(page.locator(".status-disconnected")).toHaveText("Disconnected");

  const failing = await page.context().newPage();
  await mockStudio(failing, { putStatus: 500 });
  await failing.route("**/api/workspaces/*/documents/*", (route) => route.fulfill({ status: 500, body: "internal error" }));
  await failing.goto("harness.html");
  await insertFacilitySample(failing);
  await tab(failing, "Analyse").click();
  await failing.locator('section[aria-label="Analyse"]').getByRole("button", { name: "Analyse" }).click();

  await expect(failing.getByRole("alert")).toContainText("internal error");
});

test("S9-11: a job that stays running times out after pollTimeoutMs", async ({ page }) => {
  await mockStudio(page, { jobStatuses: ["Running"] });

  await page.goto("harness.html?pollTimeoutMs=1000");
  await insertFacilitySample(page);
  await tab(page, "Analyse").click();
  await page.locator('section[aria-label="Analyse"]').getByRole("button", { name: "Analyse" }).click();

  await expect(page.getByRole("alert")).toContainText("timeout", { timeout: 5000 });
});

test("S9-12: a failed job shows its failure message", async ({ page }) => {
  await mockStudio(page, { jobStatuses: ["Queued", "Failed"] });

  await page.goto("harness.html");
  await insertFacilitySample(page);
  await tab(page, "Analyse").click();
  await page.locator('section[aria-label="Analyse"]').getByRole("button", { name: "Analyse" }).click();

  await expect(page.getByRole("alert")).toContainText("mocked failure");
});

test("S9-13: Logical English never renders document text as HTML (self-probe target)", async ({ page }) => {
  const payload = '<img src=x onerror="window.__xss=1">';
  const maliciousAnalysis = {
    ...loadFacilityAnalysis(),
    elements: [
      {
        elementId: FACILITY_ELEMENT_13,
        objectId: "13",
        sectionKey: "undertakings",
        kind: "clause",
        text: payload,
        relationClass: null,
        basis: "none",
        formId: null,
        leTemplate: null,
        leSentence: null,
        spans: [],
      },
    ],
  };

  await mockStudio(page, { analysis: analysisView(maliciousAnalysis, []) });

  await page.goto("harness.html");
  await insertFacilitySample(page);
  await tab(page, "Analyse").click();
  await page.locator('section[aria-label="Analyse"]').getByRole("button", { name: "Analyse" }).click();
  await tab(page, "Logical English").click();

  await expect(page.locator('section[aria-label="Logical English"]')).toContainText(payload);
  const xss = await page.evaluate(() => (window as unknown as { __xss?: number }).__xss);
  expect(xss).toBeUndefined();
});

test("S9a-07: markVariable command fills the Markup form, then Mark variable marks the text", async ({ page }) => {
  await mockStudio(page);
  await page.goto("harness.html");
  await insertFacilitySample(page);

  const sample = loadSample("facility-agreement");
  const { start, end } = textOffsetOf(sample, FACILITY_ELEMENT_11, "GBP 250");
  await harnessSelect(page, FACILITY_ELEMENT_11, start, end);

  await harnessCommand(page, "markVariable");

  await expect(tab(page, "Markup")).toHaveClass(/active/);
  const markup = page.locator('section[aria-label="Markup"]');
  await expect(markup.getByLabel("Key")).toHaveValue("gbp-250");
  await expect(markup.getByLabel("Value type")).toHaveValue("money");

  await markup.getByRole("button", { name: "Mark variable" }).click();

  const model = (await harnessModel(page)) as {
    sections: { elements: { elementId: string; parts: { kind: string; variableKey?: string }[] }[] }[];
  };
  const element = model.sections.flatMap((section) => section.elements).find((candidate) => candidate.elementId === FACILITY_ELEMENT_11)!;
  expect(element.parts.some((part) => part.kind === "variable" && part.variableKey === "gbp-250")).toBe(true);
});

test("S9a-08: the analyse command switches to the Analyse tab and saves the document once", async ({ page }) => {
  const studio = await mockStudio(page);

  await page.goto("harness.html");
  await insertFacilitySample(page);

  await harnessCommand(page, "analyse");

  await expect(tab(page, "Analyse")).toHaveClass(/active/);
  await expect.poll(() => studio.puts.length).toBe(1);
});
