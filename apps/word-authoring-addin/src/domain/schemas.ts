/**
 * One Ajv 2020-12 instance holding every schema under `contracts/authoring` and
 * `contracts/events` the word authoring POC uses (ADR-A114, plan WA8), keyed by the same
 * schema name the Java service's `ContractSchemas` and the Python `test_authoring_contracts.py`
 * use: the file name without `.schema.json`. This is the only place the set of schema resources is
 * listed on the add-in side.
 */
import Ajv2020 from "ajv/dist/2020.js";
import type { ErrorObject } from "ajv";

import common from "../../../../contracts/authoring/common.schema.json" with { type: "json" };
import documentSnapshot from "../../../../contracts/authoring/document-snapshot.schema.json" with { type: "json" };
import snapshotSubmission from "../../../../contracts/authoring/snapshot-submission.schema.json" with { type: "json" };
import snapshotAccepted from "../../../../contracts/authoring/snapshot-accepted.schema.json" with { type: "json" };
import authoringTemplate from "../../../../contracts/authoring/authoring-template.schema.json" with { type: "json" };
import templateList from "../../../../contracts/authoring/template-list.schema.json" with { type: "json" };
import sampleList from "../../../../contracts/authoring/sample-list.schema.json" with { type: "json" };
import documentView from "../../../../contracts/authoring/document-view.schema.json" with { type: "json" };
import jobView from "../../../../contracts/authoring/job-view.schema.json" with { type: "json" };
import analysisView from "../../../../contracts/authoring/analysis-view.schema.json" with { type: "json" };
import health from "../../../../contracts/authoring/health.schema.json" with { type: "json" };
import errorSchema from "../../../../contracts/authoring/error.schema.json" with { type: "json" };
import wordingAnalysisRequest from "../../../../contracts/events/wording-analysis-request.schema.json" with { type: "json" };
import wordingAnalysisResult from "../../../../contracts/events/wording-analysis-result.schema.json" with { type: "json" };

export const SCHEMAS: Record<string, object> = {
  common,
  "document-snapshot": documentSnapshot,
  "snapshot-submission": snapshotSubmission,
  "snapshot-accepted": snapshotAccepted,
  "authoring-template": authoringTemplate,
  "template-list": templateList,
  "sample-list": sampleList,
  "document-view": documentView,
  "job-view": jobView,
  "analysis-view": analysisView,
  health,
  error: errorSchema,
  "wording-analysis-request": wordingAnalysisRequest,
  "wording-analysis-result": wordingAnalysisResult,
};

const ajv = new Ajv2020({ allErrors: true, strict: true });
for (const schema of Object.values(SCHEMAS)) {
  ajv.addSchema(schema);
}

function formatError(error: ErrorObject): string {
  const path = error.instancePath === "" ? "/" : error.instancePath;
  return `${path} ${error.message ?? "is invalid"}`;
}

/** Validates `value` against the schema named `name`, returning one message per violation. */
export function validate(name: string, value: unknown): string[] {
  const schema = SCHEMAS[name];
  if (!schema) {
    throw new Error(`no schema named ${name}`);
  }
  const id = (schema as { $id: string }).$id;
  const validateFn = ajv.getSchema(id);
  if (!validateFn) {
    throw new Error(`schema ${name} did not compile`);
  }
  const ok = validateFn(value);
  if (ok) {
    return [];
  }
  return (validateFn.errors ?? []).map(formatError);
}
