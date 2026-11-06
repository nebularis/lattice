<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

## 12. Building a domain
{: #domains}

The substrate names no industry. A project that uses LATTICE, such as the one you have in mind, adds its own domain on top. This chapter shows how LATTICE's own insurance domain is built, then turns that into steps for a domain of yours.

<div class="callout"><strong>Under construction.</strong> The insurance domain is being built now, by the project's applied insurance reference work. This chapter teaches what is merged. Modules marked "not yet built" below are planned.</div>

### Where applied content lives

Applied content lives at the lowest level of sharing that covers everything using it.

| Level | Where | Holds |
|---|---|---|
| substrate | `ontology/<layer>/` | domain-neutral mechanisms with stated laws |
| cross-domain applied | `ontology/applied/<module>/` | domain-neutral content not yet promoted to the substrate, such as classification and capacity |
| domain-shared | `ontology/applied/<domain>/common/` | content meaningful in one domain, used by several of its modules |
| domain module | `ontology/applied/<domain>/<module>/` | one area of the domain |

Dependencies run one way. A domain's modules import its `common/` module, the cross-domain modules and the substrate, and never another domain's modules. Moving a module up a level changes its namespace and breaks every importer, so the lowest-level rule keeps such moves rare. A data architect would recognise enterprise, divisional and departmental models, with the rule that nothing depends sideways.

### The insurance domain

| Module | Content | State |
|---|---|---|
| `common/` | code-list contracts shared by the domain's modules, liability role types, physical units and currencies | built |
| `peril/` | the reference peril vocabulary: causes of loss, their characteristics, intensity measures and thresholds | built, with collections and crosswalks arriving |
| `exposure/` | locations, assets, values, zones and loss history | core built, the rest arriving |
| `submission/` | packaging an exposure set for underwriting | not yet built |
| `claims/`, `contract/` | loss chains and contract terms | deferred |

`common/` shows two moves you will make in your own domain. It declares **scheme contracts**, from chapter 7, for each code list its modules share, such as peril and mechanism of loss. And it declares **roles**, from chapter 6, that insurance needs and the substrate does not name, such as the harmed party, the liable party and the claimant. Each is a `pty:Role`, so every Party mechanism works with it unchanged.

### A reference vocabulary, from the peril module

Two entries of the peril module's cause-of-loss scheme, from its vocabulary file, show a distinction a code list with a single parent column cannot make.

<!-- source: ontology/applied/insurance/peril/vocab/peril-vocab.ttl -->
```turtle
prl-voc:N.MET.TC.SRG a skos:Concept ;
    skos:inScheme prl-voc:CauseScheme ;
    skos:notation "N.MET.TC.SRG"^^prl:ReferenceCode , "WSS"^^prl:CatModelCode ;
    skos:prefLabel "Tropical cyclone storm surge"@en ;
    skos:definition "An abnormal rise of sea level during a tropical cyclone, caused by the storm's wind and pressure field."@en ;
    skos:note "Its extension intersects N.HYD.FLD.CST, coastal flood of any origin (whitepaper §3.5). The WSS model code follows the Oasis Open Exposure Data peril classification."@en ;
    prl:broaderPartitive prl-voc:N.MET.TC ; skos:broader prl-voc:N.MET.TC ;
    prl:overlaps prl-voc:N.HYD.FLD.CST ;
    prl:accumulationClass prl-voc:Catastrophe ; prl:typicalMechanism prl-voc:Inundation ;
    prl:typicalAgency prl-voc:Natural ; prl:onset prl-voc:Sudden ; prl:definitionBasis prl-voc:Physical ; prl:harmSubject prl-voc:Property .
# …
prl-voc:N.MET.TC.HUR a skos:Concept ;
    skos:inScheme prl-voc:CauseScheme ;
    skos:notation "N.MET.TC.HUR"^^prl:ReferenceCode ;
    skos:prefLabel "Hurricane"@en ;
    skos:definition "A tropical cyclone at or above hurricane strength in the North Atlantic and eastern North Pacific basins."@en ;
    skos:note "Follows the WMO's basin-specific naming: 'hurricane' names the same wind-speed class the WMO calls 'severe tropical cyclone' or 'typhoon' in other basins. The numeric threshold itself is recorded in peril-intensity.ttl (AIR-2.6), not here."@en ;
    prl:broaderGeneric prl-voc:N.MET.TC ; skos:broader prl-voc:N.MET.TC ;
    prl:accumulationClass prl-voc:Catastrophe ; prl:typicalMechanism prl-voc:WindLoad , prl-voc:Inundation ;
    prl:typicalAgency prl-voc:Natural ; prl:onset prl-voc:Sudden ; prl:definitionBasis prl-voc:Threshold ; prl:harmSubject prl-voc:Property ;
    prl:intensityMeasure prl-voc:SustainedWind1Min .
```

Both sit under tropical cyclone, but differently. A storm surge is a **part** of a cyclone (`prl:broaderPartitive`). A hurricane is a **kind** of cyclone (`prl:broaderGeneric`). Both also assert plain `skos:broader`, so any SKOS tool, and Eligibility's hierarchical match from chapter 8, still sees one hierarchy. The domain adds precision without losing compatibility.

A hurricane is defined by a threshold. `prl:intensityMeasure` names what is measured, a one-minute sustained wind, and the threshold itself is a Quantification range set from chapter 7, kept in the module's separate intensity file. A storm surge also `prl:overlaps` coastal flood, recording that the two can describe the same water. Each concept also carries characteristics drawn from schemes of their own, such as its typical agency (natural, here) and its onset (sudden), so a query can select "every sudden natural peril" without a hand-maintained list. [Source on GitHub](https://github.com/nebularis/lattice/blob/main/ontology/applied/insurance/peril/vocab/peril-vocab.ttl).

### Steps for a domain of your own

The steps below follow LATTICE's own modelling rules and the way its domains are being built. They are a starting point, not a recipe LATTICE prescribes.

1. **Model reality first.** Ask how the law and the contracts of your field answer a question before modelling it, and record any simplification you choose.
2. **Write the examples first.** A handful of worked cases, like the facility in this tutorial, fixes what the model must accept before anyone argues about classes.
3. **Place each concept at its level.** Most of what you need will already be a substrate mechanism, a role, a condition, a state or a value space, specialised for your field. Only content that names your field's own things belongs in your domain.
4. **Subclass and specialise, never edit.** Extend substrate classes and properties, as `ex:Agreement` did in chapter 2 and as a lending module might specialise `cls:industry`. Declare roles as `pty:Role`.
5. **Keep code lists out of the model.** Declare a scheme contract for each code list, and bind the lists you use. Your business vocabularies can live in your own repository, with no change to LATTICE.
6. **Add shapes, then version.** Give each module SHACL shapes for its rules, a version IRI, and imports pinned to exact versions of what it uses.
7. **Decide storage last.** Once the model is stable, choose Persistence profiles per class, and Surface promotions for the questions your users ask most.

The project's own conventions are in [CONTRIBUTING.md](https://github.com/nebularis/lattice/blob/main/CONTRIBUTING.md) and the [applied domains README](https://github.com/nebularis/lattice/blob/main/ontology/applied/README.md).
