import { useState } from "react";
import { Check, ChevronRight, Code2, Eye, FileDiff, Plus, Save, Settings2, Trash2 } from "lucide-react";

type ContractKind = "Promotion" | "Index" | "Projection";
type Contract = { id: string; name: string; kind: ContractKind; carrier: string; profile: string; state: string; change: string };

const contracts: Contract[] = [
  { id: "subscription-currency", name: "Subscription currency", kind: "Promotion", carrier: "saas:Subscription", profile: "default-v1", state: "Approved", change: "No impact" },
  { id: "job-family", name: "Job family lookup", kind: "Index", carrier: "hr:RoleAssignment", profile: "employment-v1", state: "Generated", change: "3 dependent surfaces" },
  { id: "clinical-crosswalk", name: "Clinical code crosswalk", kind: "Promotion", carrier: "trial:Enrollment", profile: "clinical-v2", state: "Review requested", change: "Crosswalk changed" },
  { id: "subscription-arr", name: "Annual recurring revenue", kind: "Projection", carrier: "saas:Subscription", profile: "default-v1", state: "Generated", change: "MORK staging update" },
];

const turtle = `@prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
@prefix saas: <https://example.org/saas/> .

ex:subscription-currency a srf:PromotionContract ;
  srf:carrier saas:Subscription ;
  srf:promotesTo saas:subscriptionCurrency ;
  srf:surfaceProfile ex:default-profile .`;

export function Studio() {
  const [selectedId, setSelectedId] = useState(contracts[0].id);
  const [kind, setKind] = useState<ContractKind>("Promotion");
  const [steps, setSteps] = useState(["saas:hasPlan", "saas:hasPricing", "saas:inCurrency"]);
  const [showTechnical, setShowTechnical] = useState(false);
  const [saved, setSaved] = useState(false);
  const selected = contracts.find((contract) => contract.id === selectedId) ?? contracts[0];

  function addStep() {
    setSteps([...steps, ""]);
  }

  function updateStep(index: number, value: string) {
    setSteps(steps.map((step, current) => current === index ? value : step));
  }

  function removeStep(index: number) {
    setSteps(steps.filter((_, current) => current !== index));
  }

  return <main className="studio-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-mark">S</span><span>Surface Contract Studio</span></div>
      <div className="environment"><span className="status-dot" />Tenant example / Staging</div>
      <button className="icon-button" title="Studio settings" aria-label="Studio settings"><Settings2 size={18} /></button>
    </header>

    <div className="workspace">
      <aside className="portfolio" aria-label="Contract portfolio">
        <div className="section-head"><div><span className="eyebrow">Portfolio</span><h1>Surface contracts</h1></div><button className="icon-button" title="Create contract" aria-label="Create contract"><Plus size={18} /></button></div>
        <div className="filter-row"><button className="filter active">All <span>3</span></button><button className="filter">Needs review <span>1</span></button></div>
        <nav className="contract-list">
          {contracts.map((contract) => <button key={contract.id} className={`contract-row ${contract.id === selectedId ? "selected" : ""}`} onClick={() => { setSelectedId(contract.id); setKind(contract.kind); setSaved(false); }}>
            <span className={`kind-pill ${contract.kind.toLowerCase()}`}>{contract.kind}</span>
            <strong>{contract.name}</strong><small>{contract.carrier}</small><span className="row-state">{contract.state}</span>
          </button>)}
        </nav>
      </aside>

      <section className="editor" aria-label="Contract editor">
        <div className="editor-title"><div><span className="eyebrow">{selected.kind} contract</span><h2>{selected.name}</h2><p>Revision r-2026-09-19-001 <span className="state-chip">{selected.state}</span></p></div><div className="actions"><button className="secondary" onClick={() => setShowTechnical(!showTechnical)}><Code2 size={16} />Technical view</button><button className="primary" onClick={() => setSaved(true)}><Save size={16} />{saved ? "Saved draft" : "Save draft"}</button></div></div>
        <div className="kind-switch" role="group" aria-label="Contract kind"><button className={kind === "Promotion" ? "active" : ""} onClick={() => setKind("Promotion")}>Promotion</button><button className={kind === "Index" ? "active" : ""} onClick={() => setKind("Index")}>Index</button><button className={kind === "Projection" ? "active" : ""} onClick={() => setKind("Projection")}>Projection</button></div>
        <div className="form-grid">
          <label>Contract name<input defaultValue={selected.name} /></label>
          <label>Carrier<select defaultValue={selected.carrier}><option>saas:Subscription</option><option>hr:RoleAssignment</option><option>trial:Enrollment</option></select></label>
          <label>Target namespace<input defaultValue="https://example.org/generated/" /></label>
          <label>Profile<select defaultValue={selected.profile}><option>default-v1</option><option>employment-v1</option><option>clinical-v2</option></select></label>
        </div>
        <section className="panel"><div className="panel-title"><div><span className="eyebrow">Read path</span><h3>Property traversal</h3></div><button className="icon-button" title="Add path step" aria-label="Add path step" onClick={addStep}><Plus size={18} /></button></div>
          <div className="path-builder">{steps.map((step, index) => <div className="path-step" key={`${index}-${step}`}><span>{index + 1}</span><input value={step} placeholder="namespace:property" onChange={(event) => updateStep(index, event.target.value)} />{index < steps.length - 1 && <ChevronRight size={18} />}{steps.length > 1 && <button className="icon-button compact" title="Remove path step" aria-label="Remove path step" onClick={() => removeStep(index)}><Trash2 size={15} /></button>}</div>)}</div>
        </section>
        {kind === "Index" && <section className="panel population"><div><span className="eyebrow">Population and closure</span><h3>Job family scheme contract</h3></div><label className="toggle"><input type="checkbox" defaultChecked /> Materialize membership assertions</label><label className="toggle"><input type="checkbox" defaultChecked /> Include `skos:broader` closure</label><label>Population budget<input type="number" defaultValue="5000" min="1" /></label></section>}
        {kind === "Projection" && <section className="panel population"><div><span className="eyebrow">Projection roles</span><h3>Deterministic ARR derivation</h3></div><label>Projection kind<select defaultValue="derivation"><option>derivation</option><option>join</option><option>expansion</option></select></label><label>Required evidence<input defaultValue="saas:hasMonthlyPrice, saas:hasBillingPeriodsPerYear" /></label><label>Result target<input defaultValue="saas:annualRecurringRevenue" /></label><label className="toggle"><input type="checkbox" checked readOnly /> Deterministic-only lowering</label><label className="toggle"><input type="checkbox" checked readOnly /> No LLM completion</label></section>}
        {showTechnical && <section className="technical"><div className="panel-title"><div><span className="eyebrow">Turtle</span><h3>Generated declaration preview</h3></div><button className="icon-button" title="Copy Turtle" aria-label="Copy Turtle" onClick={() => navigator.clipboard.writeText(turtle)}><Code2 size={17} /></button></div><pre>{turtle}</pre></section>}
      </section>

      <aside className="inspector" aria-label="Validation and impact inspector">
        <section><span className="eyebrow">Release readiness</span><h3>Law checklist</h3><ul className="law-list"><li><Check size={16} />S1 path form is exclusive</li><li><Check size={16} />R1 deterministic generation</li><li><Check size={16} />R2 parity evidence current</li><li><Check size={16} />R5 closure is well-founded</li></ul></section>
        <section><span className="eyebrow">Read set</span><h3>Impact preview</h3><div className="impact-card"><strong>{selected.change}</strong><p>Profile and source graph revisions are pinned. Generation will only read the declared contract, profile, and source graphs.</p><button className="link-button"><Eye size={15} />Inspect dependencies</button></div></section>
        <section><span className="eyebrow">Generated output</span><h3>Revision diff</h3><div className="diff"><div><span className="diff-add">+ 12</span><span>direct properties</span></div><div><span className="diff-same">= 3</span><span>provenance records</span></div><div><span className="diff-remove">- 0</span><span>breaking changes</span></div></div><button className="link-button"><FileDiff size={15} />Open full diff</button></section>
        {kind === "Projection" && <section className="technical-inspector"><span className="eyebrow">MORK Technical Inspector</span><h3>Staged mapping</h3><dl><dt>Graph</dt><dd>mork/staging/arr-r-001</dd><dt>MCN</dt><dd>Not computed</dd><dt>Backends</dt><dd>SPARQL, Native IR</dd><dt>Dependencies</dt><dd>None</dd><dt>Review</dt><dd>Engineering review</dd></dl><p>Mapping activation is governed by the MORK workflow and cannot be requested here.</p></section>}
      </aside>
    </div>
  </main>;
}
