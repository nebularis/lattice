This is fantastic work. Out of your incredible work on docs/architecture/rdf-sparql-patterns-guide.md​, falls a need for further development.

Many of these patterns lead to choices. Because Lattice is a framework (like spring), providing ontologies, libraries, deployable services (in java, python, etc), and control plan infrastructure (rabbitmq, SPI for database access, Postgres based capabilities), an end user will be deciding which parts to use - maybe some, maybe all!

## Making Persistence Profiles Configurable

This means the user who is writing their own applied​ ontology on top of Lattice, may need to choose their own approach and decide which mechanism for concurrent reads and writes to use. Some (but not all) of their graph content MAY be aggregates. Some may not. Some may require total ordering over fields, and some may not. The user will wish to choose between patterns and combinations of patters to suit their design and their unique environment. This unique per-user implementation is why configurability is so important. Whilst we MAY in the future build some multi-tenant platform on top of Lattice, that will never be baked into this codebase, it will be another type of implementation which happens to host multiple user implementations itself.

This tells me we need 2 things:

1) a way for users to indicate how their ontology (which sits on top of our ontology layers) will be handled
2) a way to generate the correct SPARQL based on the user's configuration

For (1) I think we need to decide if we are going to build this layer on top of surface​ or not. I think NOT, but we should validate that none of surface​ codebase is reusable for this - I suspect because the intent and scope is different it will not be.

Instead, I think we should build a new ontology substrate in `ontology/persistence​`, which allows the user to configure for their own ontologies whatever is not behaving in the default way. A simplistic example might look like this:

```turtle
# 2. Configure a specific profile instance for your OWL class / scenario
dal:OrderClassStrongProfile a dal:DataAccessProfile ;
    dal:targetClass       ex:Order ;
    dal:concurrencyProfile dal:CompareAndSet ;    # Part IV / C [1]
    dal:orderingGrain      dal:EventGrain ;       # Part III / O [1]
    dal:receiptModel       dal:PatchLog ;         # Chapter 20 [1]
    dal:metaTopology       dal:SharedSharded ;    # Chapter 17 [1]
    dal:metaShards         "64"^^xsd:long ;
    dal:uniquenessPolicy   dal:RejectOnViolation .
```

We MIGHT however, want to consider granularity. I _like_ that this could work at an OWL Class level, but perhaps the user will want to apply it to a whole ontology! I think, therefore, that the DataAccessProfile​ needs to be defined in such a way that you can scope it how you wish - to a class, an equivalentClass​, a namespace (because how would you define what the scope of "an ontology" would be otherwise?), and so on and so forth.

We NEED to decide though, for each of these properties - concurrency profile, ordering grain, receipt model, meta topology, shards, uniqueness - whether it makes sense that they could vary by profile? Indeed, does each of these actually need it's own profile class, that can be scoped via some intermediate ProfileScope​ ? We MUST THINK of the consequences of differing grains here: what would it mean if I chose different grains for different parts of my implementation? How do we warn the user of the consequences of odd choices here, when processing the configuration? How do configurations get applied​ to one another? What is the precedence if namespace​ has one profile and class Foo​ inside the namespace has another (override?) and then another equivalentClass​ that covers a subset of the population for Foo​ has yet another? NB: we MUST BE CAREFUL with equivalentClass​, or anything that relies on reasoning or entailment, because different SPIs will offer different levels of conformance. We should emit a warning if a profile expects reasoning and an SPI doesn't offer it as a default operation/setting.

YET ANOTHER challenge is what to do about ontology content that is from _inside_ Lattice. The user might be handling a population of individuals from, for example, behaviour​ or some other Lattice substrate. What if the use of elements defined in a Lattice owned ontology needs different profiles for different uses in user / applied​ ontologies? For example, the user builds two applied ontologies of their own, let's say lending​ and credit​, and they both use OWL classes from behaviour​ but in different way that require different profiles. We need NOT ONLY to give the user a way to configure this demand for how the SPARQL should behave (and the behaviour of surrounding capabilities Lattice offers, such as reconciliation batch jobs, etc), but we also need to be able to guarantee that the back end can support the granularity AND that our SPARQL layers (and/or other layers targeting outside the RDF database, e.g., Rabbit/Kafka) can support it too! 

## Making Aggregate Roots Configurable

NOW let us go back to the other important question: HOW does the user determine that something is an aggregate? And how does the user define what the aggregate root(s) are and what containment rules apply? In the patterns guide, "orders are aggregates: an order and its line items change together", but only the implementor (i.e., the end user - not part of Lattice!) can know this! It is specific to a use-case and/or business/organisation, so we need to make it configurable!!! HOW can we let the user define what their aggregate roots are?

Because an RDF graph is a flat web of triples without hard physical boundaries, defining an aggregate root and its composite membership requires imposing a logical boundary. In semantic web technologies, this is achieved using one of three structural patterns. Let's look at them briefly:

### Pattern 1: Named Graph Partitioning (Physical Aggregation)

This is the most common pattern for operational systems. The Aggregate Root's IRI names a dedicated graph, and all composite members (entities and value objects) are co-located inside that graph.turtle# The graph IRI is the Aggregate Root ID

```turtle
GRAPH <urn:g:orders/1> {
  <urn:order:1>  a ex:Order ;          # <- Aggregate Root
                 ex:lineItem <urn:order:1/li/1> .
                 
  <urn:order:1/li/1> a ex:LineItem ;   # <- Composite Member
                     ex:sku "WIDGET-9" .
}
```

**Persistence Layer Impact**: Mutation operations can use a clean CLEAR GRAPH or whole-graph PUT replace, making the entire aggregate a single unit of consistency.

**Evaluation**: High operational efficiency, native support in most triple stores, but leads to graph proliferation.

### Pattern 2: Tree Traversal via Property Paths (Logical Aggregation)

Instead of physical separation, the entire domain lives in a shared graph. The aggregate boundary is defined purely through the ontology by declaring *composition properties* as distinct from associative relationships.

```turtle
# In the Ontology:
ex:lineItem  rdfs:subPropertyOf  dal:isCompositeOf .
ex:customer  rdfs:subPropertyOf  dal:isAssociatedWith .

# In the Data:
<urn:order:1> ex:lineItem <urn:order:1/li/1> . # Included in aggregate
<urn:order:1> ex:customer <urn:person:42> .    # Excluded from aggregate
```

**Persistence Layer Impact**: A persistence engine can calculate the aggregate boundary dynamically at query/write time by executing a property path expansion:

```sparql
CONSTRUCT { ?root ?p ?child . ?child ?p2 ?descendant }
WHERE {
  BIND(<urn:order:1> AS ?root)
  ?root (dal:isCompositeOf)* ?child .
  ?child ?p ?descendant .
}
```

**Evaluation**: Keeps data inside large, highly optimized graphs, but requires strict modeling discipline to avoid infinite traversal loops or pulling in the entire graph universe.

### Pattern 3: SHACL Shape Traversal (Validation-Driven Aggregation)

This pattern uses SHACL Node Shapes to explicitly declare the structural blueprint of the aggregate.

```turtle
ex:OrderAggregateShape
    a sh:NodeShape ;
    sh:targetClass ex:Order ;
    sh:property [
        sh:path ex:lineItem ;
        sh:node ex:LineItemShape ; # Recursively defines boundaries
        sh:minCount 1 ;
    ] .
```

**Persistence Layer Impact**: A persistence library reads the `sh:property` trees at startup. When a payload is submitted, it parses the target shape, walks the properties matching sh:node, captures those specific triples, and rejects any unmapped elements as outside the aggregate boundary.

**Evaluation**: Exceptionally robust because the validation schema is the boundary definition, _however_, forces the user to adopt our persistence layer OR forces us to implement extremely complex SHACL machinery for SPIs that support SHACL execution on-write.

## Persistence Software Layer Design

### Persistence SPARQL (Pre-)Compiler

This is explicitly out of scope here. The instinct is, I think, to build the SPI layers in Java, for performance reasons. I do, however, want to keep any software functionality we define for `persistence` COMPLETELY separate from the SPI implementation. Instead, I believe we need to define a compilation toolchain that takes the `ontology/persistence` individuals defined for a user's implementation/deployment, and safely generates SPARQL templates for all the SPARQL operations across individual nodes and/or aggregates in the configuration set.

It is vital that our generated SPARQL is **as efficient as possible**, which is a real challenge given we do not know the full nature of the implementation/deployment apart from what is defined in the `ontology/persistence` configuration.

The **primary reason** for generating SPARQL as part of the design-time utility of Lattice, is so that a user implementation can completely eschew the use of our java code and simply compile SPARQL for use in their own application. They may use our ontologies without adopting any runtime components into their architecture!

_Note: Another thing to consider here is that future projection design MAY lead us to generating non-RDF projections of ontology T-Boxes - e.g., we may build a layer that allows a user to define a T-Box and Lattice provides tools to translate than into SQL or LPG with labels, etc - and therefore compilation of queries suited to a target deployment type is a potential direction of travel._

### Persistence Execution Layer

#### Request Query Mapping

An _optional_ layer will be a Java component that wires together incoming requests with the compiled queries, sending these on to the SPI. This layer will need to be loaded with the configuration from `ontology/persistence`, BUT this is a RUNTIME component not a DESIGN TIME one! This component is NOT a running service, it is a library that must be injected with the SPI it will interact with to interact with the backend(s).

This component MUST NOT assume an interface! We DO NOT implement an HTTP listener or a RabbitMQ endpoint here. The reason for this is that an implementation can _choose_ how to expose and wire together capabilities. Some may wish to write their own HTTP API layer and route to this library by calling it from their own code. Another may place all queries behind a RabbitMQ boundary and write a java consumer that pulls messages, runs queries on the SPI using this library, and writes the response back to another queue - a pattern that would work well if the user's application is going to use RabbitMQ's support for `AMQP 1.0 over WebSocket`, for example, or the `RabbitMQ Web MQTT Plugin` to provide async data responses to rich-client (e.g., React) applications directly in the browser.

This component's implementation and design WILL NOT be included in the work package scope. This component's implementation MUST be added to the open design questions in `docs/developer/plans/lattice-platform-agentic-development-v0.2.md` and marked as unresolved.

#### Query Execution Component

The query execution component sits closer to the SPIs, because specific SPIs MAY need to override the syntax of certain queries, due to backend naunces and/or different levels of support for the standards. This introduces quite the complexity for us, because we _pre-compiled_ SPARQL already at design-time, and now at runtime some other component might want to _mess_ with the SPARQL.

For now we will mark this as an unresolved area of design - this component will NOT be included in the work package scope. The implementation gaps arrising here MUST be added to the open design questions in `docs/developer/plans/lattice-platform-agentic-development-v0.2.md` and marked as unresolved.

#### Housekeeping Component

A component will be needed to run configurable housekeeping tasks, ranging from checking population sizes are growing within limits, pruning old data and archiving, etc etc. This will require extensive design and its own roadmap as part of the implementation.

This component WILL be part of the work package.

## Architectural Position

Our users will be able to configure - at various levels of overlapping granularity - how aggregate roots are defined for THEIR application (built on OUR ontologies) AND how THEIR persistence profiles are to work. 

We will provide software components that read the configuration and produce SPARQL templates.

Since we are writing a persistence compilation wrapper over an ontology config layer, do not hardcode the boundary strategy. Treat it as configuration metadata. In our new `ontology/persistence​` ontology, map scopes to their boundary strategies explicitly. This structural agility ensures your persistence wrapper can generate a ground DELETE/INSERT against a dedicated graph for some families, while compiling dynamic property-path updates for others, protecting your application from the open-world performance traps of raw SPARQL.

In the documentation for `ontology/persistence​`, we must write EXTENSIVELY to explain all of this, so that users who skip our java layer for some queries (e.g., perhaps they write by our layer by read directly, or vice versa), understand all the moving parts and what they must remain aware of.

## Task

You must now write out the `docs/developer/sketches​`, `docs/developer/plan`, and `docs/developer/status` for the following, which you will then implement (following our agent instructions for developers, which are in `.github/copilot-instructions`):

1. A thoroughly detailed architectural specification of `ontology/persistence​` and the java components that support it, linking everything back to `docs/architecture/rdf-sparql-patterns-guide.md` so all the documentation is internally consistent.
2. A complete rewrite of `docs/developer/plans/rdf-sparql-patterns-phase-plan.md` - your plan will replace this plan. Remove `Slice 2: Store-specific adapters and policy` and re-define `Slice 2` in terms of this prompt. You may keep/integrate and expand on the **Policy enforcement** ideas in the origin plan, but the `Store Adapters` must be removed from the plan. Instead we implement the ontology substrate, the compiler(s), and the `Request Query Mapping` library. No SPI development in this plan please, and no query execution.
3. Add a NOTE to `docs/developer/plans/lattice-platform-agentic-development-v0.2.md` - within `Part 6 — PHASE 2: Ingestion and query planes`. We need to add a note that states PENDING all the work this package being complete, THAT package will need to be updated before it can be implemented to account for the changes here.

Your `docs/developer/sketch` must NOT contain less detail than this prompt explores! It needs to be pretty extensive so that the plan is robust.

Your replacement for `docs/developer/plans/rdf-sparql-patterns-phase-plan.md` must outline the plan to deliver all the components we've discussed here, except the query execution at runtime part, so:

- A thoroughly detailed implementation of `ontology/persistence​`, with extensive documentation, user guides, which must include extensive example configurations AND explanatory generated turtle (showing what our layers will generate in the background)
- A complete implementation of the compiler tool-chain and any other required tools to support the use of `ontology/persistence` at design-time. I don't care if the compiler is built in python or java, however I would prefer that you build this on a templating system (such as mustache) rather than by pure string interpolation, so that we can easily escape any malicious content in user-supplied `ontology/persistence` configuration data. YOU MUST ensure that the templating system is not allowing SPARQL injection attacks to take place. Recall that tools typically go in `tools`, so if you build the compiler in python, the sub-project lives in there. If you build in java, we don't have a java project root at `tools`, so if that case please write a python wrapper in `tools` that looks for the java executable on the path and if not present then looks in the local build folder. 
- A first cut of the `platform/housekeeping` component, covering its configuration landscape and expected behaviours, interfaces and contracts with other layers/components, and a full planned roadmap. Thorough documentation will be required in the README for the project AND we need an architectural design specification in `docs/architecture`.
