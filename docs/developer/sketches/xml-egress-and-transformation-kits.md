<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# XML egress: SPARQL results, XSLT, and embedded LegalRuleML

Version 0.1, draft for review. Explores how LATTICE and applied modules such as Open CBAA emit XML
for consumers who want it, using SPARQL results as the source and XSLT as the transform, with the
transformation kit published so an adopter can run it without our code.

Third in a set. [legalruleml-mapping.md](legalruleml-mapping.md) is the construct analysis,
[legalruleml-runtime-pipeline.md](legalruleml-runtime-pipeline.md) covers ingress, and
[normative-wire-protocol.md](normative-wire-protocol.md) covers JSON egress. This sketch covers XML
egress and does not revisit the others.

**The position it argues.** SPARQL Query Results XML is the source, not RDF/XML. XSLT 3.0 on Saxon
is the transform, hosted in a new Java module and published as an artefact. LegalRuleML payloads
are embedded as real element subtrees rather than escaped text, using `fn:parse-xml()` to lift a
stored literal and `xs:any processContents="lax"` to admit the foreign schema. The entire
transformation kit — query, stylesheet, schema — is a versioned public artefact, so a consumer who
distrusts or cannot run our runtime gets the same output from any conformant XSLT processor.

---

## Contents

1. [Why XML, and for whom](#1-why-xml-and-for-whom)
2. [The source format decision](#2-the-source-format-decision)
3. [Tabular to tree](#3-tabular-to-tree)
4. [The schema](#4-the-schema)
5. [Embedding LegalRuleML without CDATA](#5-embedding-legalruleml-without-cdata)
6. [The `xs:ID` collision, and other embedding hazards](#6-the-xsid-collision-and-other-embedding-hazards)
7. [Hosting: Saxon in Java](#7-hosting-saxon-in-java)
8. [Publishing the transformation kit](#8-publishing-the-transformation-kit)
9. [Generation, and the drift question](#9-generation-and-the-drift-question)
10. [Determinism and canonical XML](#10-determinism-and-canonical-xml)
11. [Security](#11-security)
12. [Scale and streaming](#12-scale-and-streaming)
13. [ACORD, and what this kit could also serve](#13-acord-and-what-this-kit-could-also-serve)
14. [What exists today](#14-what-exists-today)
15. [A first slice](#15-a-first-slice)
16. [Risks and open questions](#16-risks-and-open-questions)

---

## 1. Why XML, and for whom

The JSON sketch's audience table has a gap. Two consumer classes want XML and will not take JSON.

| Consumer | Why XML |
|---|---|
| Established market platforms | ACORD is XML. A policy administration system bought in 2011 has an XML ingest and no JSON path |
| Regulatory and market-body filings | submission formats are XSD-defined, and validation against a published schema is the acceptance criterion |
| LegalRuleML-native partners | the standard is XML. Handing them JSON containing escaped XML is worse than handing them XML |
| Document toolchains | XSLT to PDF, XSL-FO, and print pipelines are XML-native and will not change |

The third row is the interesting one. A consumer who sends LegalRuleML and receives JSON with the
payload as an escaped string has to unescape and reparse, and any escaping defect corrupts a legal
document silently. **XML egress is the only skin where an embedded LegalRuleML statement stays a
first-class parsed subtree end to end.** That is a correctness argument, not a preference.

---

## 2. The source format decision

Two candidate sources, and the choice matters more than it appears.

### 2.1 RDF/XML is a trap

RDF/XML is a serialisation of a graph, and **the same graph has many valid RDF/XML documents**. A
serialiser may choose striped or flat form, may abbreviate a typed node
(`<foo:Thing rdf:about="…">` rather than `<rdf:Description>` plus `rdf:type`), may use
`rdf:parseType="Resource"` for anonymous nodes or expand them, may emit `rdf:nodeID` or nest, and
may order properties freely.

An XSLT written against one serialiser's output breaks when the serialiser is upgraded, the store
is swapped, or a blank node appears where an IRI used to be. There is no fix short of writing an
XSLT that handles every RDF/XML production, which is a project rather than a stylesheet.

**RDF/XML is rejected as the transform source.** It stays available as a raw egress format for
consumers who want the graph and will parse it with an RDF library, which is a different use case.

### 2.2 SPARQL Query Results XML is regular by construction

The [W3C SPARQL Query Results XML Format](https://www.w3.org/TR/rdf-sparql-XMLres/) is a table, in
namespace `http://www.w3.org/2005/sparql-results#`:

```xml
<sparql xmlns="http://www.w3.org/2005/sparql-results#">
  <head>
    <variable name="termKey"/>
    <variable name="modality"/>
    <variable name="bearerKey"/>
  </head>
  <results>
    <result>
      <binding name="termKey"><literal>uw-authority</literal></binding>
      <binding name="modality"><uri>https://…/instrument#PermissionModality</uri></binding>
      <binding name="bearerKey"><literal>coverholder</literal></binding>
    </result>
  </results>
</sparql>
```

Five element names, one optional `xml:lang`, one optional `datatype`. That is the whole grammar.
An XSLT written against it cannot be surprised.

The trade is that a table is flat and the output is a tree, which §3 addresses, and that the query
now carries part of the contract, which §8 turns into a feature rather than a cost.

### 2.3 The rejected third option

Deriving XML from the Market Profile JSON via XSLT 3.0's `fn:json-to-xml()` would guarantee the two
skins never diverge, and it is genuinely tempting. It fails on the LegalRuleML case: the Market
Profile carries a payload as a JSON string, so an XML document derived from it would carry escaped
text, losing exactly the property §1 identifies as XML's reason to exist.

**XML is projected from the graph, not from the JSON.** §9 addresses the drift this creates.

---

## 3. Tabular to tree

A denormalised result set plus `xsl:for-each-group` is the standard XSLT 2.0-and-later answer, and
it is well suited here.

```xml
<xsl:template match="sr:sparql">
  <instrument key="{sr:results/sr:result[1]/sr:binding[@name='instrumentKey']/sr:literal}">
    <terms>
      <xsl:for-each-group select="sr:results/sr:result"
                          group-by="sr:binding[@name='termKey']/sr:literal">
        <term key="{current-grouping-key()}"
              modality="{lat:localName(current-group()[1]/sr:binding[@name='modality']/sr:uri)}">
          <xsl:for-each-group select="current-group()"
                              group-by="sr:binding[@name='conditionKey']/sr:literal">
            <condition read="{current-group()[1]/sr:binding[@name='readPath']/sr:literal}">
              <xsl:for-each select="current-group()">
                <within><xsl:value-of select="lat:localName(sr:binding[@name='within']/sr:uri)"/></within>
              </xsl:for-each>
            </condition>
          </xsl:for-each-group>
        </term>
      </xsl:for-each-group>
    </terms>
  </instrument>
</xsl:template>
```

Three practical notes.

- **One query per aggregate, not per level.** A single denormalised SELECT with nested grouping
  beats several queries joined in the stylesheet, because it removes the ordering dependency
  between documents and keeps the whole transform a pure function of one input.
- **`ORDER BY` in the query is mandatory**, not cosmetic. Grouping is order-sensitive for output
  determinism (§10), and SPARQL results are unordered unless the query says otherwise.
- **IRI shortening happens in the stylesheet**, not the query. A `lat:localName()` function keeps
  the mapping from `…/instrument#PermissionModality` to `permission` in one declared place, and it
  is generated from the same term table as the JSON skins (§9).

Where a genuinely recursive structure appears — nested profiles under
`elg:hasCondition`, which do nest (ADR-A03) — grouping is insufficient and the query must emit a
path or depth column so the stylesheet can rebuild the tree. That is the one place this approach
gets awkward, and it is worth pinning the maximum nesting depth in the query rather than pretending
SPARQL will express arbitrary recursion comfortably.

---

## 4. The schema

Mirroring the Market Profile of the JSON sketch, so the two skins carry the same information under
the same names.

```xml
<instrument xmlns="https://schemas.nebularis.org/lattice/xml/1.0"
            key="BA-2026-001" version="1">

  <parties>
    <party key="coverholder"   role="coverholder" actor="harbour-underwriting-ltd"/>
    <party key="leadInsurer"   role="insurer"     actor="insurer-a"   share="0.6"/>
    <party key="followInsurer" role="insurer"     actor="insurer-b"   share="0.4"/>
  </parties>

  <participation key="insurers" rule="several">
    <member ref="leadInsurer"/>
    <member ref="followInsurer"/>
  </participation>

  <terms>
    <term key="uw-authority" form="conditions" modality="permission"
          bearer="coverholder" activity="bind">
      <activatedBy>
        <all>
          <condition read="policy.contractType" scheme="contract-type" match="exact">
            <oneOf>insurance</oneOf>
          </condition>
          <condition read="riskLocation" scheme="territory" match="hierarchical">
            <within>FR</within>
            <except>FR-20R</except>
          </condition>
          <condition read="sumInsured">
            <atMost amount="5000000" unit="GBP"/>
            <atMost amount="5750000" unit="EUR"/>
          </condition>
        </all>
      </activatedBy>
    </term>
  </terms>

  <bindings>
    <binding scheme="territory"     edition="iso-3166:2026"/>
    <binding scheme="contract-type" edition="lma-contract-type:2025"/>
  </bindings>
</instrument>
```

### 4.1 Design rules

| Rule | Reason |
|---|---|
| **Scalars are attributes, structure is elements** | conventional XML, and it keeps the document readable. `amount` and `unit` on `<atMost>` rather than child elements |
| **Repetition is a repeated element, never a delimited attribute** | `<within>FR</within><within>BE</within>`, so a schema can constrain each and a consumer can iterate |
| **Keys are document-local, matching the JSON skin** | §9 of the wire-protocol sketch. `ref="leadInsurer"` is an `xs:IDREF`-shaped reference, though see §6 before making it a real `xs:IDREF` |
| **No IRIs in ordinary documents** | an optional `<provenance>` block carries them for consumers that want the graph |
| **Element-qualified, attribute-unqualified** | `elementFormDefault="qualified"`, `attributeFormDefault="unqualified"`. Standard, and keeps attributes free of prefixes |
| **No mixed content anywhere except `<text>`** | mixed content defeats most binding tools. Prose lives in one designated element |

---

## 5. Embedding LegalRuleML without CDATA

The requirement is that a LegalRuleML statement appears inside `<payload>` as a real element
subtree that a validator and a binding tool can see, not as escaped text or CDATA.

```xml
<term key="notice-2" form="legalruleml">
  <payload dialect="oasis-lrml-1.0-normalised">
    <lrml:PrescriptiveStatement xmlns:lrml="http://docs.oasis-open.org/legalruleml/ns/v1.0/"
                                xmlns:ruleml="http://ruleml.org/spec"
                                key="ps2">
      <lrml:hasTemplate>
        <ruleml:Rule closure="universal">
          <ruleml:if>…</ruleml:if>
          <ruleml:then>
            <lrml:SuborderList>
              <lrml:Obligation>…</lrml:Obligation>
            </lrml:SuborderList>
          </ruleml:then>
        </ruleml:Rule>
      </lrml:hasTemplate>
    </lrml:PrescriptiveStatement>
  </payload>
</term>
```

Two problems to solve: getting it out of the graph as nodes, and admitting it in the schema.

### 5.1 Getting it out: `fn:parse-xml()`

The ingress pipeline stores an unliftable payload verbatim, which means it sits in the graph as an
`xsd:string` literal containing XML. XPath 3.0 supplies the inverse:

```xml
<xsl:template match="sr:binding[@name='payload']">
  <payload dialect="{../sr:binding[@name='dialect']/sr:literal}">
    <xsl:copy-of select="parse-xml(sr:literal)/*"/>
  </payload>
</xsl:template>
```

`fn:parse-xml($arg as xs:string?) as document-node()?` is standard XPath 3.0 and implemented by
Saxon-HE. `fn:parse-xml-fragment()` handles a payload with several top-level statements and no
single root. `xsl:copy-of` carries the subtree including its namespace nodes, so the output declares
`lrml:` and `ruleml:` correctly without any manual namespace fixing.

This is the whole mechanism. No CDATA, no escaping, no string concatenation, and no custom
extension function.

### 5.2 Admitting it: two schema strategies

**Strategy 1, lax wildcard.** The base schema admits any foreign-namespace content and validates it
when a schema for that namespace is available to the processor.

```xml
<xs:element name="payload">
  <xs:complexType>
    <xs:sequence>
      <xs:any namespace="##other" processContents="lax"
              minOccurs="1" maxOccurs="unbounded"/>
    </xs:sequence>
    <xs:attribute name="dialect" type="lat:DialectName" use="required"/>
  </xs:complexType>
</xs:element>
```

`lax` is the operative choice and is frequently misread. It means: *if the validator can find a
schema for the element's namespace, validate strictly against it, and if it cannot, accept
well-formed content*. So a consumer who adds the LegalRuleML XSD to their catalog gets full
validation of the payload with no change to our schema or their instance documents, and a consumer
who does not still validates everything outside the payload.

**Strategy 2, explicit import and reference.** A strict profile imports LegalRuleML and names the
permitted elements.

```xml
<xs:import namespace="http://docs.oasis-open.org/legalruleml/ns/v1.0/"
           schemaLocation="oasis/lrml-normal.xsd"/>

<xs:element name="payload">
  <xs:complexType>
    <xs:choice minOccurs="1" maxOccurs="unbounded">
      <xs:element ref="lrml:Statements"/>
      <xs:element ref="lrml:PrescriptiveStatement"/>
      <xs:element ref="lrml:ConstitutiveStatement"/>
      <xs:element ref="lrml:PenaltyStatement"/>
      <xs:element ref="lrml:ReparationStatement"/>
      <xs:element ref="lrml:OverrideStatement"/>
    </xs:choice>
    <xs:attribute name="dialect" type="lat:DialectName" use="required"/>
  </xs:complexType>
</xs:element>
```

This is the most literal reading of "their schema embedded within ours", and it buys real typed
bindings: JAXB, `xsd.exe` or XMLSpy generate `PrescriptiveStatement` classes rather than
`org.w3c.dom.Element`.

**The cost is not small.** LegalRuleML's XSD is large, ships in three variants (basic, compact,
normalised), and importing it means every consumer's generated model gains the entire LegalRuleML
object graph whether or not they use it. A binding-platform team that never touches LegalRuleML
should not have to compile it.

### 5.3 Recommendation

**Ship both, as two schema documents over one instance format.**

| Schema | Content | For |
|---|---|---|
| `lattice-1.0.xsd` | the base, with `xs:any processContents="lax"` | every consumer. No LegalRuleML dependency |
| `lattice-1.0-lrml.xsd` | imports the base and the OASIS normalised XSD, narrowing `<payload>` by reference | consumers wanting typed LegalRuleML bindings |

The same instance document validates against both, so the choice is the consumer's and costs us one
extra schema file. **Pin the normalised serialisation.** Accepting all three variants triples the
test surface for no benefit, and the ingress pipeline already normalises, so a payload we emit is
normalised by construction. A caller who sends compact gets it back normalised, and the `dialect`
attribute says so honestly rather than lying about what was stored.

---

## 6. The `xs:ID` collision, and other embedding hazards

Four hazards that only appear once foreign content is embedded. Each is subtle and each produces an
invalid or wrong document rather than an obvious failure.

### 6.1 `@key` is `xs:ID`, and IDs are document-scoped

LegalRuleML's `@key` has type `xs:ID`, and the specification's own conformance rule requires each
`@key` to be *unique within that document*. Embedding statements drawn from several source
documents into one response **can collide**, producing a document that is not schema-valid and that
some parsers reject outright.

| Option | Assessment |
|---|---|
| Rewrite keys on embedding, prefixing with the term key | preserves validity. **Breaks `@keyref` integrity** unless every reference is rewritten consistently, which the stylesheet can do since both are in scope |
| Emit at most one source document's statements per response | simple, and unacceptably limiting for an instrument assembled from several wordings |
| Wrap each payload in `<lrml:LegalRuleML>` with `xml:base` | does **not** help. `xs:ID` uniqueness is per XML document, not per subtree or base URI |
| Declare the collision out of scope and let it fail | dishonest |

**Rewrite, consistently, in the stylesheet.** A named template rewrites `@key` and every `@keyref`
within one payload by a deterministic prefix derived from the term key, and the original value is
preserved in a `lat:sourceKey` attribute so the link back to the source document survives. The
rewrite is a pure function of the term key, which keeps §10's determinism.

### 6.2 Namespace prefix collisions

Two payloads may bind the same prefix to different namespaces, or the host document may bind
`lrml:` differently. `xsl:copy-of` preserves each subtree's own namespace nodes, so XML semantics
are safe, but the serialised output can carry several prefix declarations for the same URI. Harmless
and untidy. Declaring the common namespaces once on the root and letting Saxon's serialiser
consolidate keeps output clean.

### 6.3 `xs:IDREF` on our own references

§4's `<member ref="leadInsurer"/>` is tempting to type as `xs:IDREF`, which would let a validator
check referential integrity. Doing so puts our keys into the same document-wide ID space as the
embedded LegalRuleML keys, so a collision between one of our keys and a LegalRuleML `@key` becomes
possible.

**Keep our references as `xs:NCName`, not `xs:IDREF`**, and check referential integrity with
Schematron or `xs:key`/`xs:keyref` scoped to our own elements. `xs:key` is scoped to a declared
selector, so it does not share the global ID space and is the right tool.

### 6.4 The payload is untrusted content

It arrived from a caller. §11 covers this.

---

## 7. Hosting: Saxon in Java

### 7.1 Why Saxon, and why Java

| Requirement | Saxon-HE |
|---|---|
| XSLT 3.0 and XPath 3.1, for `parse-xml()`, `for-each-group`, streaming | yes. Saxon-HE is the reference implementation |
| Java 25, which the platform already pins | yes |
| Swappable through a standard interface | yes, via JAXP `TransformerFactory`, so no hard coupling |
| Licence compatible | **MPL 2.0**, the same licence as this repository's own tooling. Unlike the reasoner, which is AGPL and needs the ADR-A83 isolation treatment, Saxon needs none |
| Already needed elsewhere | **yes.** The ingress pipeline's Route B needs an XSLT 2.0 processor for the OASIS normaliser and triplifier. One dependency, two uses |

The last row matters for the cost case. Saxon is not a dependency this capability introduces alone.

The reasoning isolation check (`tools/reasoning_isolation_check.py`) matches
`hermit|openllet|pellet|drools|owlapi|owlready|jpype|py4j|pyjnius`. Saxon is not a reasoner or a
rules engine and does not match, so no ADR-A83 conflict arises. Worth confirming in the slice rather
than assuming.

### 7.2 Module placement

A new Maven module beside the seven that exist, since none of them fits.

```text
platform/
  semantic-dataset-spi/        graph references, snapshots, capabilities
  semantic-dataset-fuseki/     named-graph read adapter          ← supplies SPARQL results
  semantic-xml-egress/         NEW: query + stylesheet + serialiser
  semantic-policy/
  platform-outbox/
  release-integration/
  surface-workflow/
  reasoning-testkit/
```

`semantic-xml-egress` depends on `semantic-dataset-spi` for graph references and on Saxon. It does
**not** depend on `semantic-dataset-fuseki`, so any conforming store adapter can feed it. Its public
surface is narrow:

```java
public interface XmlProjection {
    /** Project one graph reference through a named, versioned transformation kit. */
    XmlResult project(GraphReference ref, KitId kit, ProjectionOptions options);
}
```

`KitId` names a published kit version (§8), so the caller selects a contract rather than a
stylesheet path, and the module resolves which query and stylesheet that implies.

---

## 8. Publishing the transformation kit

This is the part with the most leverage, and it needs one correction to be workable.

**An XSLT alone is not publishable, because it has no defined input.** A stylesheet that consumes
SPARQL results is meaningless without the query that produced them. So the published unit is a
**kit** of three artefacts plus a manifest:

```text
contracts/xml/lattice-instrument/1.0/
    manifest.json          kit id, version, checksums, compatible ontology versions
    query.rq               the SPARQL SELECT, with ORDER BY, that defines the input
    transform.xsl          XSLT 3.0, consumes sparql-results, emits lattice XML
    lattice-1.0.xsd        base schema, lax payload
    lattice-1.0-lrml.xsd   strict profile importing the OASIS schema
    examples/
        input.srx          a captured SPARQL result set
        expected.xml       the exact expected output
```

### 8.1 What publishing buys

| Benefit | Detail |
|---|---|
| **Runtime independence** | a consumer points any SPARQL endpoint at `query.rq`, runs `transform.xsl` in Saxon, .NET's Saxon port, or a commercial processor, and gets byte-identical output. No LATTICE code |
| **Auditability** | a regulator can verify our output is what our published transform produces, rather than trusting an opaque service |
| **A conformance test for us** | `examples/input.srx` plus `expected.xml` is a golden-file test. Our runtime must produce `expected.xml`, and so must any third party |
| **Vendor neutrality** | a market body can adopt the kit without adopting us, which is the strongest adoption argument available |
| **Versioning falls out** | a kit is a directory with a version. Deprecating a kit is deprecating a directory |

### 8.2 What it constrains

Publishing a transform makes the **query** part of the public contract, which means the query's
variable names and result shape are now compatibility surface. That is a real cost and it is worth
paying, because the alternative is a published stylesheet whose input nobody can reproduce.

It also means **no Saxon extension functions**. The stylesheet must be pure XSLT 3.0 so that any
conformant processor runs it. Convenience functions like `lat:localName()` are declared in the
stylesheet with `xsl:function`, not imported from a vendor namespace. That is a constraint worth
enforcing with a check rather than a convention, since a single `saxon:` call silently makes the kit
unportable.

---

## 9. Generation, and the drift question

The JSON sketch argues that all skins are generated from one term table so they cannot drift. XML
projected independently from the graph reopens that risk: a term renamed in the term table changes
the JSON and leaves the XSLT emitting the old name.

Three options.

| Option | Drift | Readability of the published artefact |
|---|---|---|
| Hand-write query and stylesheet | **yes, unbounded** | best |
| Generate both from the term table | none | generated XSLT is unusual to publish and read |
| Hand-write, and check against the term table in CI | caught, not prevented | best |

**Generate, and generate legibly.** The repository already treats generated artefacts as first-class
(`fnd:DerivedArtefact`, deterministic output, golden files), and a generated stylesheet fits that
pattern. The unusual part is that this generated artefact is *meant to be read by outsiders*, which
means the generator must emit comments, stable ordering and sensible whitespace rather than the
densest correct output. That is a small extra requirement on the generator and it removes an entire
class of divergence.

The kit's `manifest.json` records the term-table version it was generated from, so a kit and a JSON
schema that disagree are detectable rather than merely unlikely.

---

## 10. Determinism and canonical XML

XML egress must be reproducible, because the output may be filed, hashed, signed or compared.

| Source of nondeterminism | Control |
|---|---|
| SPARQL result order | `ORDER BY` in `query.rq`, on every grouping key. Not optional |
| Attribute order | XSLT does not guarantee it. Fix by emitting attributes in a declared order in the template, and by canonicalising if a hash is required |
| Namespace prefix choice | declare all prefixes on the root with `xsl:namespace-alias` or explicit declarations |
| Whitespace | `<xsl:output indent="no"/>` for the canonical form. An indented form is a separate, non-canonical convenience output |
| Embedded payload | already normalised at ingress. Re-serialising a parsed subtree is stable in Saxon, but a hash should be taken over the C14N form |
| Timestamps | none in the document body. Generation time belongs in a transport header or an optional `<provenance>` block that is excluded from the hash |

Where a hash is needed, **Canonical XML 1.1 (C14N11)** over the output, with a note that C14N and
the `<payload>` subtree interact: C14N will re-serialise the embedded LegalRuleML too, which is
correct but means the payload's byte form in our output may differ from the byte form the caller
sent. **The stored literal remains the authoritative copy of what was received**, and the emitted
form is a faithful re-serialisation, not a byte-preserving echo. That distinction should be stated
in the schema documentation, because a caller comparing bytes will otherwise think we altered their
document.

---

## 11. Security

XML processing is a well-known source of the OWASP Top 10's A05 misconfiguration class, and this
design both parses untrusted XML and re-emits it. Four controls, none optional.

### 11.1 XXE and entity expansion on inbound payloads

`fn:parse-xml()` parses caller-supplied content. An external entity reference can read local files
or make network requests, and nested entity definitions produce the billion-laughs expansion.

**Controls:**
- Disable DTD processing entirely on the parser Saxon uses:
  `http://apache.org/xml/features/disallow-doctype-decl` set true, and
  `XMLConstants.FEATURE_SECURE_PROCESSING` set true on the `TransformerFactory`.
- Set Saxon's `ALLOW_EXTERNAL_FUNCTIONS` to false and `XML_PARSER_FEATURE` overrides to reject
  external DTDs and external parameter entities.
- Reject a payload containing a `<!DOCTYPE` declaration at the boundary, before parsing, rather than
  relying only on parser configuration. Defence in depth, and it produces a clearer refusal.

### 11.2 XSLT is code

A stylesheet can read documents (`fn:doc`, `fn:unparsed-text`) and, with extensions enabled, invoke
Java. **Only kit stylesheets from `contracts/xml/` are ever loaded**, never a caller-supplied one,
and they are loaded from the classpath with their checksums verified against the manifest. A
caller-supplied stylesheet is not a feature and should not become one.

Set `FEATURE_SECURE_PROCESSING`, disable extension functions, and supply a `URIResolver` that
refuses every URI not in the kit. A stylesheet that needs to resolve an external document is a
stylesheet that is not publishable anyway (§8.2), so the restriction costs nothing.

### 11.3 The payload is untrusted content, echoed

A LegalRuleML payload accepted from caller A and returned to caller B carries A's content into B's
parser. Three consequences:

- **Validate on ingress, not only on egress.** The runtime pipeline already validates against the
  OASIS XSD at the boundary, which is the right place.
- **Size and depth limits** on both parse and emit. A deeply nested payload is a parser
  denial-of-service even without entities.
- **Never render a payload as HTML without escaping.** The review workbench displays payloads, and
  an XML subtree injected into a DOM is a script-injection vector. That is the workbench's
  responsibility and belongs in its own review, but it originates here and should be flagged to
  whoever builds it.

### 11.4 Tenant isolation

The projection runs a SPARQL query against a graph reference. The reference carries tenant and
project, and `semantic-policy` already enforces scope at the control boundary. The XML module must
**not** accept a raw query or a raw endpoint from a caller, only a `GraphReference` plus a `KitId`,
which is why §7.2's interface takes exactly those two. Accepting a query string would turn this
module into an unrestricted SPARQL endpoint with an XML serialiser attached.

---

## 12. Scale and streaming

An instrument is small. A bordereau projection or a portfolio-wide filing is not.

| Size | Approach |
|---|---|
| one instrument, hundreds of elements | ordinary tree transform. No special handling |
| thousands of cases | **XSLT 3.0 streaming.** `xsl:mode streamable="yes"`, `xsl:stream`. Saxon-HE supports a useful subset, Saxon-EE supports more |
| very large filings | chunk by aggregate and emit several documents with a manifest, rather than one enormous one |

**Streaming and grouping conflict.** `xsl:for-each-group` with `group-by` is not streamable in
general. Where streaming is needed, the query must return results pre-grouped and ordered so the
stylesheet can use `group-adjacent`, which is streamable. That is a query design constraint driven
by the output, and it is another reason the query belongs in the published kit.

For the first kit, **do not stream.** Establish correctness, then measure, then stream only the kits
that need it.

---

## 13. ACORD, and what this kit could also serve

The insurance market's XML standard is ACORD, and any XML egress conversation in this domain ends up
there. Worth stating the relationship rather than leaving it implied.

**Our schema is not ACORD and should not pretend to be.** ACORD models transactions and messages.
This schema models a contract's terms and their meaning, which ACORD does not carry. Conflating them
would produce a schema that is bad at both.

**The kit mechanism is how ACORD gets served.** An ACORD projection is another kit: a different
query, a different stylesheet, a different schema, the same module and the same publication model.
Nothing about §7 or §8 changes. That is the argument for building the kit abstraction rather than a
single hard-coded transform, and it generalises beyond ACORD to any market body's submission format.

An intermediate worth considering later: emit our schema, then publish a **second-stage XSLT** from
our schema to ACORD. Two hops, but it means the market-specific transform is pure XML-to-XML with no
SPARQL knowledge, which is exactly the kind of artefact a market body can own and maintain itself.

---

## 14. What exists today

Measured, not assumed.

| Piece | State |
|---|---|
| XSLT or Saxon anywhere in code | **none.** Zero references in `.java` or `.py` |
| Java platform | Java 25, Maven, seven modules |
| SPARQL results source | `semantic-dataset-fuseki` is the named-graph read adapter |
| Graph reference contract | exists, in `semantic-dataset-spi` |
| Policy enforcement at the boundary | `semantic-policy` exists |
| RDF/XML output | `mork2rml.py` has `--format xml`, for RML output only. Not related |
| JSON-LD framing precedent | SPC's egress formatter frames results. Different skin, same architectural idea |
| An XML contract directory | `contracts/` has `events`, `identity`, `mork`, `openapi`, `release`, `surface`. No `xml` |

So this is a genuinely new capability with one new third-party dependency, sitting on foundations
that already exist.

---

## 15. A first slice

One kit, end to end, chosen to exercise the mechanism rather than the domain.

**Kit:** `lattice-instrument/1.0`, projecting one instrument with conditions-form terms only.

| Step | Deliverable | Pass criterion |
|---|---|---|
| 1 | `platform/semantic-xml-egress` module with Saxon-HE and `FEATURE_SECURE_PROCESSING` | builds, and `check:reasoning-isolation` still passes |
| 2 | `query.rq` with full `ORDER BY` | returns a stable denormalised result set |
| 3 | `transform.xsl`, pure XSLT 3.0, no extensions | a portability check confirms no `saxon:` namespace appears |
| 4 | `lattice-1.0.xsd` with lax payload | output validates |
| 5 | Golden test: `input.srx` → `expected.xml`, byte-exact | passes twice in a row and after a JVM restart |
| 6 | **Security test: a payload containing a DOCTYPE and an external entity** | **refused at the boundary, and the entity is never resolved** |
| 7 | **Embedding test: two payloads with colliding `@key`** | both embedded, keys rewritten deterministically, `@keyref` integrity preserved, document schema-valid |
| 8 | Third-party reproduction: run the kit in a plain Saxon CLI outside our code | byte-identical to step 5 |

**Steps 6, 7 and 8 are the slice.** Steps 1 to 5 are ordinary work that will go fine. Step 6 is the
security property, step 7 is the embedding hazard that a naive implementation gets wrong and
discovers in production, and step 8 is the entire publication claim. A slice that delivers 1 to 5
and defers the rest has not tested anything that was in doubt.

The strict schema profile (`lattice-1.0-lrml.xsd`) and the `legalruleml` form can follow in a second
slice, since step 7 already proves the embedding mechanism with the lax schema.

---

## 16. Risks and open questions

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| X1 | A `saxon:` extension creeps into a published stylesheet, silently making the kit unportable | **high** | high | Automated portability check in CI, not a convention. Step 3 above |
| X2 | XXE or entity expansion through `parse-xml()` on caller content | medium | **severe** | §11.1, defence in depth, and step 6 as a standing test |
| X3 | `@key` collisions produce invalid documents under load, after passing single-payload tests | **high** | medium | §6.1 rewrite, and step 7 |
| X4 | The published query becomes a compatibility millstone | medium | medium | Version the kit as a whole. A query change is a new kit version, never an edit |
| X5 | XML and JSON skins diverge | medium | high | §9 generation from the term table, and the manifest records which version |
| X6 | The module is given a raw-query entry point "just for testing" and becomes an open SPARQL endpoint | medium | **severe** | §11.4. The interface takes `GraphReference` and `KitId` only. No overload |
| X7 | Effort is spent before a consumer asks | **high** | medium | Same ruling as the interchange work. This sketch says how, not whether |

### Open questions

| # | Question |
|---|---|
| X-Q1 | Is the XML schema a LATTICE artefact or an applied one? §4's example mixes substrate structure with insurance naming, the same tension as the JSON sketch's W1 |
| X-Q2 | Does the kit ship inside `contracts/xml/`, or as a separately released package a market body can consume without cloning the repository? |
| X-Q3 | Should the canonical output be C14N11 by default, or is that only for consumers who hash and sign? C14N output is less readable |
| X-Q4 | Do we support compact-serialisation LegalRuleML payloads on egress, or always normalise? §5.3 recommends always normalise, which means the caller's exact bytes are not echoed |
| X-Q5 | Is a second-stage schema-to-ACORD stylesheet ours to write, or the market body's? §13 suggests theirs, which is an adoption question rather than a technical one |
| X-Q6 | Does the optional `<provenance>` block expose graph IRIs and revision hashes to every consumer, or only privileged ones? Related to the JSON sketch's W8 |

X-Q6 and the JSON sketch's W8 are the same question in two skins and should be answered once, for
both, rather than separately.
