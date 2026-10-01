import { expect, test, type Page } from "@playwright/test";
import {
  loadFacilityAnalysis,
  loadFacilityTurtle,
  loadSample,
  loadTemplate,
  mockAnalysis,
  mockCatalog,
  mockGraph,
  mockJob,
  mockSnapshotSubmission,
  textOffsetOf,
} from "./support";

const HEALTHY = { status: "ok" as const, fuseki: "up" as const, amqp: "up" as const };
const FACILITY_ELEMENT_11 = "00000001-0000-4000-8000-000000000011";
const FACILITY_ELEMENT_13 = "00000001-0000-4000-8000-000000000013";

async function mockHealthOk(page: Page): Promise<void> {
  await page.route("**/api/health", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(HEALTHY) }),
  );
}

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

test("S9-02: health ok shows Connected and the catalogue loads", async ({ page }) => {
  await mockHealthOk(page);
  await mockCatalog(page);
  await page.goto("harness.html");

  await expect(page.locator(".status-connected")).toHaveText("Connected");
  const doc = page.locator('section[aria-label="Document"]');
  await expect(doc.locator("ul").nth(0).getByRole("listitem")).toHaveCount(3);
  await expect(doc.locator("ul").nth(1).getByRole("listitem")).toHaveCount(3);
});

test("S9-03: Apply template on the licence creates six sections, each element empty, with guidance shown", async ({ page }) => {
  await mockHealthOk(page);
  await mockCatalog(page);
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
  await mockHealthOk(page);
  await mockCatalog(page);
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
  await mockHealthOk(page);
  await mockCatalog(page);
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

test("S9-06: Analyse submits the snapshot and shows validation, findings and detections", async ({ page }) => {
  const sample = loadSample("facility-agreement");
  const agentOffset = textOffsetOf(sample, FACILITY_ELEMENT_13, "[Agent]");
  const detection = {
    elementId: FACILITY_ELEMENT_13,
    partIndex: 1,
    start: agentOffset.start,
    end: agentOffset.end,
    text: "[Agent]",
    kind: "placeholder",
    suggestion: { action: "mark-variable", valueType: "party", suggestedKey: "agent", targetElementId: null },
  };

  await mockHealthOk(page);
  await mockCatalog(page);
  await mockSnapshotSubmission(page, { detections: [detection] });
  await mockJob(page, ["completed"]);
  await mockAnalysis(page);

  const puts: unknown[] = [];
  page.on("request", (request) => {
    if (request.method() === "PUT" && request.url().includes("/snapshot")) {
      puts.push(request.postDataJSON());
    }
  });

  await page.goto("harness.html");
  await insertFacilitySample(page);
  await tab(page, "Analyse").click();
  await page.locator('section[aria-label="Analyse"]').getByRole("button", { name: "Analyse" }).click();

  await expect(page.getByText("[Agent]")).toBeVisible();
  expect(puts).toHaveLength(1);
  expect((puts[0] as { baseRevision: number | null }).baseRevision).toBeNull();
});

test("S9-07: Accept a detection marks the suggested variable", async ({ page }) => {
  const sample = loadSample("facility-agreement");
  const agentOffset = textOffsetOf(sample, FACILITY_ELEMENT_13, "[Agent]");
  const detection = {
    elementId: FACILITY_ELEMENT_13,
    partIndex: 1,
    start: agentOffset.start,
    end: agentOffset.end,
    text: "[Agent]",
    kind: "placeholder",
    suggestion: { action: "mark-variable", valueType: "party", suggestedKey: "agent", targetElementId: null },
  };

  await mockHealthOk(page);
  await mockCatalog(page);
  await mockSnapshotSubmission(page, { detections: [detection] });
  await mockJob(page, ["completed"]);
  await mockAnalysis(page);

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
  await mockHealthOk(page);
  await mockCatalog(page);
  await mockSnapshotSubmission(page, {});
  await mockJob(page, ["completed"]);
  await mockAnalysis(page);

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

test("S9-09: Graph tab renders the diagram and the Turtle toggle shows the mocked text", async ({ page }) => {
  await mockHealthOk(page);
  await mockCatalog(page);
  await mockSnapshotSubmission(page, {});
  await mockJob(page, ["completed"]);
  await mockAnalysis(page);
  await mockGraph(page);

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
  const turtle = loadFacilityTurtle();
  await expect(graph.locator("pre")).toContainText(turtle.slice(0, 30));
});

test("S9-10: a failing health check shows Disconnected, and a failed submission shows an error banner", async ({ page }) => {
  await page.route("**/api/health", (route) => route.abort());
  await mockCatalog(page);
  await mockSnapshotSubmission(page, { status: 500, errorBody: { error: "internal error", details: [] } });

  await page.goto("harness.html");
  await expect(page.locator(".status-disconnected")).toHaveText("Disconnected");

  await insertFacilitySample(page);
  await tab(page, "Analyse").click();
  await page.locator('section[aria-label="Analyse"]').getByRole("button", { name: "Analyse" }).click();

  await expect(page.getByRole("alert")).toContainText("internal error");
});

test("S9-11: a job that stays queued times out after pollTimeoutMs", async ({ page }) => {
  await mockHealthOk(page);
  await mockCatalog(page);
  await mockSnapshotSubmission(page, {});
  await mockJob(page, ["queued"]);

  await page.goto("harness.html?pollTimeoutMs=1000");
  await insertFacilitySample(page);
  await tab(page, "Analyse").click();
  await page.locator('section[aria-label="Analyse"]').getByRole("button", { name: "Analyse" }).click();

  await expect(page.getByRole("alert")).toContainText("timeout", { timeout: 5000 });
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

  await mockHealthOk(page);
  await mockCatalog(page);
  await mockSnapshotSubmission(page, {});
  await mockJob(page, ["completed"]);
  await page.route("**/api/documents/*/revisions/*/analysis", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        documentId: "00000001-0000-4000-8000-000000000000",
        revision: 1,
        analysis: maliciousAnalysis,
        conformance: [],
        proposalGraph: {
          tenantId: "poc",
          projectId: "word-authoring",
          graphIri: "https://example.org/lattice/authoring/doc/x/rev/1/proposal-graph",
          revisionHash: `sha256:${"c".repeat(64)}`,
        },
      }),
    }),
  );

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
  await mockHealthOk(page);
  await mockCatalog(page);
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

test("S9a-08: the analyse command switches to the Analyse tab and sends one PUT", async ({ page }) => {
  await mockHealthOk(page);
  await mockCatalog(page);
  await mockSnapshotSubmission(page, {});
  await mockJob(page, ["completed"]);
  await mockAnalysis(page);

  const puts: unknown[] = [];
  page.on("request", (request) => {
    if (request.method() === "PUT" && request.url().includes("/snapshot")) {
      puts.push(request.postDataJSON());
    }
  });

  await page.goto("harness.html");
  await insertFacilitySample(page);

  await harnessCommand(page, "analyse");

  await expect(tab(page, "Analyse")).toHaveClass(/active/);
  await expect.poll(() => puts.length).toBe(1);
});

