# MORK Synthetic Data Generator Suite
#
# NB: this test generator was produced by Claude Opus 4.6 on AWS Bedrock, from the MORK DL encoding.
#
## Design Philosophy
#
# The generator suite creates two fundamentally different kinds of data:
#
# 1. **Target-side data**: Well-formed FBO/NSDP individuals (tanks, flows, scopes, covers, towers, placements) that populate the knowledge graph the MORK pipeline maps *into*.
#
# 2. **Source-side data**: Deliberately messy, structurally alien "external schemas" — the kind of data a broker might receive from a cedent's spreadsheet, a legacy system export, or a third-party API — that the MORK pipeline must map *from*. These schemas are intentionally incongruent with the target ontology: they flatten hierarchies, denormalise joins, use different naming conventions, combine multiple ontological concepts into single fields, split single concepts across multiple fields, and generally behave the way real-world insurance data does.
#
# The generator is deterministic given a seed, reproducible, and parameterised to control complexity.
#
"""
====================================
MORK Synthetic Data Generator Suite
====================================

Generates:
  1. FBO/NSDP target-side instance data (placements, towers, tanks, flows, covers)
  2. External source schemas (deliberately misaligned with target ontology)
  3. External source instance data (conforming to external schemas)
  4. Expected MORK mapping graphs (ground truth for pipeline testing)
  5. Expected compiled artefacts (ground truth for compiler testing)

Usage:
    generator = MorkSyntheticDataGenerator(seed=42)
    dataset = generator.generate_full_dataset(
        num_placements=10,
        num_external_schemas=5,
        instances_per_schema=20,
    )
    dataset.write_all("./test_data/")
"""

from __future__ import annotations

import hashlib
import json
import random
import string
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import rdflib
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH, SKOS, XSD


# ═══════════════════════════════════════════════════════════════════
# Namespace declarations
# ═══════════════════════════════════════════════════════════════════

FBO = Namespace("http://www.nebularis.org/ontologies/FBO#")
NSDP = Namespace("http://www.nebularis.org/ontologies/NSDP#")
MORK = Namespace("http://www.nebularis.org/ontologies/Mork#")
MTPL = Namespace("http://www.nebularis.org/ontologies/MorkTemplates#")
RISK = Namespace("http://www.nebularis.org/vocabularies/risk#")
GEO = Namespace("http://www.nebularis.org/vocabularies/geo#")
FIN = Namespace("http://www.nebularis.org/vocabularies/financial#")
LOB = Namespace("http://www.nebularis.org/vocabularies/lob#")
SYNTH = Namespace("http://www.nebularis.org/synthetic/")
EXT = Namespace("http://www.nebularis.org/synthetic/external/")


# ═══════════════════════════════════════════════════════════════════
# Vocabulary pools — the raw material for generation
# ═══════════════════════════════════════════════════════════════════

class VocabularyPool:
    """
    Curated vocabulary pools drawn from the FBO 20-dimensional scope model
    (FBO Definition 2.7) and insurance domain knowledge.
    """

    PERILS = [
        ("AllRisks", None),
        ("NaturalPeril", "AllRisks"),
        ("Hurricane", "NaturalPeril"),
        ("Flood", "NaturalPeril"),
        ("Earthquake", "NaturalPeril"),
        ("Wildfire", "NaturalPeril"),
        ("Windstorm", "NaturalPeril"),
        ("ManMadePeril", "AllRisks"),
        ("Fire", "ManMadePeril"),
        ("Explosion", "ManMadePeril"),
        ("CyberPeril", "ManMadePeril"),
        ("Ransomware", "CyberPeril"),
        ("DataBreach", "CyberPeril"),
        ("NationStateAttack", "CyberPeril"),
        ("Terrorism", "ManMadePeril"),
        ("PoliticalViolence", "ManMadePeril"),
    ]

    TERRITORIES = [
        ("Worldwide", None),
        ("NorthAmerica", "Worldwide"),
        ("US", "NorthAmerica"),
        ("US_FL", "US"),
        ("US_TX", "US"),
        ("US_CA", "US"),
        ("US_NY", "US"),
        ("US_LA", "US"),
        ("US_GulfCoast", "US"),
        ("Canada", "NorthAmerica"),
        ("Europe", "Worldwide"),
        ("UK", "Europe"),
        ("Germany", "Europe"),
        ("France", "Europe"),
        ("AsiaPacific", "Worldwide"),
        ("Japan", "AsiaPacific"),
        ("Australia", "AsiaPacific"),
        ("LatinAmerica", "Worldwide"),
        ("Caribbean", "LatinAmerica"),
    ]

    LINES_OF_BUSINESS = [
        ("Property", None),
        ("CommercialProperty", "Property"),
        ("IndustrialProperty", "Property"),
        ("Casualty", None),
        ("GeneralLiability", "Casualty"),
        ("ProductsLiability", "Casualty"),
        ("ProfessionalLiability", "Casualty"),
        ("Marine", None),
        ("CargoMarine", "Marine"),
        ("HullMarine", "Marine"),
        ("Specialty", None),
        ("Aviation", "Specialty"),
        ("Energy", "Specialty"),
        ("CyberInsurance", "Specialty"),
        ("Surety", "Specialty"),
        ("FinancialLines", None),
        ("DirectorsOfficers", "FinancialLines"),
        ("ErrorsOmissions", "FinancialLines"),
    ]

    COVERAGE_TYPES = [
        "PropertyDamage", "BusinessInterruption", "ThirdPartyLiability",
        "FirstPartyLoss", "ContingentBI", "ExtraExpense", "LossOfRents",
        "CyberLiability", "CyberFirstParty", "MediaLiability",
        "BodilyInjury", "PersonalInjury", "AdvertisingInjury",
    ]

    TANK_TYPES = [
        "Indemnity", "Parametric", "Signal", "Pool",
        "Hybrid", "Surety", "Collateralised",
    ]

    BASES = [
        "PerOccurrence", "PerClaim", "PerLocation", "PerRisk",
        "Aggregate", "AnnualAggregate", "ProductsAggregate",
        "PolicyAggregate", "CombinedSingleLimit",
        "PoolAggregate", "PoolPerEvent", "PoolAnnual",
        "EventTriggered", "SignalTriggered",
    ]

    FLOW_TYPES_CORE = ["Erosion", "Aggregation", "Override", "Attachment", "Limitation"]
    FLOW_TYPES_SIGNAL = ["SignalActivate", "SignalDeactivate", "TriggerGate", "GraduatedPayout"]
    FLOW_TYPES_POOL = ["PoolDistribute", "PoolContribute", "PoolWithdraw"]
    FLOW_TYPES_COLLATERAL = ["CollateralDraw", "CollateralRelease", "CollateralTopUp"]
    FLOW_TYPES_RECOVERY = ["SubrogationCreate", "SubrogationRecover", "SalvageRecover"]

    PARTY_ROLES = [
        "PolicyHolder", "Principal", "Obligee", "Beneficiary",
        "Indemnitor", "Guarantor", "Cedent", "Reinsurer",
        "Retrocessionaire", "PoolParticipant", "Investor",
        "Sponsor", "ServiceProvider", "Claimant",
    ]

    TRIGGER_MODES = [
        "Occurrence", "ClaimsMade", "Discovery", "Parametric",
        "Hybrid", "PoolTriggered", "SignalTriggered",
    ]

    COLLATERAL_STATUSES = [
        "NotApplicable", "FullyFunded", "PartiallyFunded",
        "DrawPending", "Released", "Trapped", "InDispute",
    ]

    REINSTATEMENT_STATUSES = [
        "NotApplicable", "Available", "PartiallyUsed",
        "Exhausted", "PendingPremium", "Declined",
    ]

    DEFENSE_TREATMENTS = [
        "ErodesLimit", "OutsideLimit", "SeparateTower",
        "SharedWithIndemnity", "Supplementary", "NotApplicable",
    ]

    CURRENCIES = ["USD", "GBP", "EUR", "JPY", "AUD", "CAD", "CHF"]

    COMPANY_NAMES = [
        "Meridian Holdings", "Apex Capital Group", "Northwind Industries",
        "Constellation Partners", "Pacific Rim Ventures", "Sterling Dynamics",
        "Atlas International", "Vanguard Enterprises", "Summit Resources",
        "Pinnacle Solutions", "Crestview Technology", "Ironclad Manufacturing",
        "Silverline Logistics", "Oceanic Trading", "Frontier Energy Corp",
        "Quantum Biotech", "Nexus Financial", "Zenith Aerospace",
        "Emerald Healthcare", "Titan Construction", "Sapphire Retail Group",
        "Cobalt Mining Ltd", "Prism Telecommunications", "Forge Steel Works",
        "Horizon Agriculture", "Cascade Hospitality", "Vertex Pharmaceuticals",
        "Obsidian Defense Systems", "Lunar Entertainment", "Granite Real Estate",
    ]

    INSURER_NAMES = [
        "Lloyd's Syndicate 2468", "AIG", "Zurich Insurance",
        "Swiss Re", "Munich Re", "Berkshire Hathaway Specialty",
        "Chubb", "Allianz", "SCOR", "Hannover Re",
        "Tokio Marine", "MS Amlin", "Hiscox",
        "Lancashire Holdings", "Markel International",
    ]

    BROKER_NAMES = [
        "Marsh McLennan", "Aon", "Willis Towers Watson",
        "Gallagher", "Lockton", "Brown & Brown",
        "Hub International", "USI Insurance Services",
    ]


# ═══════════════════════════════════════════════════════════════════
# SECTION 1: FBO Target-Side Data Generation
# ═══════════════════════════════════════════════════════════════════

@dataclass
class GeneratedPlacement:
    """A complete insurance placement with all FBO structures."""
    placement_id: str
    insured_name: str
    broker: str
    inception: date
    expiry: date
    currency: str
    programme: GeneratedProgramme
    towers: list[GeneratedTower]
    participants: list[GeneratedParticipant]
    # RDF serialisation
    graph: Graph = field(default_factory=Graph)


@dataclass
class GeneratedProgramme:
    programme_id: str
    programme_name: str
    line_of_business: str
    territory_scope: list[str]
    peril_scope: list[str]


@dataclass
class GeneratedTower:
    tower_id: str
    tower_name: str
    layers: list[GeneratedLayer]


@dataclass
class GeneratedLayer:
    layer_id: str
    attachment: Decimal
    limit: Decimal
    basis: str
    tank: GeneratedTank
    flows: list[GeneratedFlow]


@dataclass
class GeneratedTank:
    tank_id: str
    tank_type: str
    capacity: Decimal
    basis: str
    scope: GeneratedScope
    trigger_config: Optional[dict] = None
    pool_config: Optional[dict] = None
    collateral_config: Optional[dict] = None


@dataclass
class GeneratedScope:
    perils: list[str]
    territories: list[str]
    coverage_types: list[str]
    line_of_business: str
    party_roles: list[str]
    trigger_mode: str = "Occurrence"
    defense_treatment: str = "NotApplicable"
    collateral_status: str = "NotApplicable"
    reinstatement_status: str = "NotApplicable"


@dataclass
class GeneratedFlow:
    flow_id: str
    flow_type: str
    source_tank_id: str
    target_tank_id: str
    precedence: int
    condition: Optional[str] = None


@dataclass
class GeneratedParticipant:
    participant_id: str
    name: str
    role: str  # "Leader", "Follower"
    share: Decimal
    line_stamp: Decimal


@dataclass
class GeneratedCoverSpan:
    span_id: str
    floor: Decimal
    ceiling: Decimal
    capacity_share: Decimal
    source_tank_id: str
    tank_type: str
    scope: GeneratedScope
    term_hash: str
    computed_at: datetime


class FBOTargetGenerator:
    """
    Generates well-formed FBO instance data: placements, programmes,
    towers with layers, capacity tanks, flow graphs, cover spans.

    All data aligns with:
      - FBO Definition 2.1 (CapacityTank)
      - FBO Definition 2.7 (20-dim ScopeQualifier)
      - FBO Definition 3.2 (FlowAction)
      - FBO Definition 3.5 (Well-Formed FlowGraph WF1-WF8)
      - FBO Definition 5.4 (CoverSpan)
    """

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.vocab = VocabularyPool()
        self._counter = 0

    def _uid(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter:04d}"

    def _money(self, low: int, high: int, step: int = 1_000_000) -> Decimal:
        """Generate a money amount in whole millions."""
        val = self.rng.randrange(low, high + 1, step)
        return Decimal(str(val))

    def _pick(self, items: list, k: int = 1) -> list:
        k = min(k, len(items))
        return self.rng.sample(items, k)

    def _pick_one(self, items: list):
        return self.rng.choice(items)

    def _pick_perils(self, n: int = None) -> list[str]:
        """Pick perils, preferring leaves of the hierarchy."""
        leaves = [p for p, parent in self.vocab.PERILS if
                  p not in {par for _, par in self.vocab.PERILS if par}]
        if n is None:
            n = self.rng.randint(1, min(4, len(leaves)))
        return [p for p in self._pick(leaves, n)]

    def _pick_territories(self, n: int = None) -> list[str]:
        leaves = [t for t, parent in self.vocab.TERRITORIES if
                  t not in {par for _, par in self.vocab.TERRITORIES if par}]
        if n is None:
            n = self.rng.randint(1, min(3, len(leaves)))
        return [t for t in self._pick(leaves, n)]

    def generate_placement(self) -> GeneratedPlacement:
        """Generate a complete placement with realistic structure."""
        placement_id = self._uid("PLC")
        insured = self._pick_one(self.vocab.COMPANY_NAMES)
        broker = self._pick_one(self.vocab.BROKER_NAMES)
        currency = self._pick_one(self.vocab.CURRENCIES[:3])  # USD/GBP/EUR mostly

        inception = date(2025, 1, 1) + timedelta(days=self.rng.randint(0, 364))
        expiry = inception + timedelta(days=365)

        lob_leaf = self._pick_one([
            l for l, _ in self.vocab.LINES_OF_BUSINESS
            if l not in {p for _, p in self.vocab.LINES_OF_BUSINESS if p}
        ])
        territories = self._pick_territories()
        perils = self._pick_perils()

        programme = GeneratedProgramme(
            programme_id=self._uid("PRG"),
            programme_name=f"{insured} {lob_leaf} Programme {inception.year}",
            line_of_business=lob_leaf,
            territory_scope=territories,
            peril_scope=perils,
        )

        # Decide programme complexity
        complexity = self.rng.choice(["simple", "standard", "complex", "rcv"])
        towers = self._generate_towers(programme, complexity, currency)

        # Generate market participants
        num_participants = self.rng.randint(2, 6)
        participants = self._generate_participants(num_participants)

        placement = GeneratedPlacement(
            placement_id=placement_id,
            insured_name=insured,
            broker=broker,
            inception=inception,
            expiry=expiry,
            currency=currency,
            programme=programme,
            towers=towers,
            participants=participants,
        )

        self._serialise_placement_to_rdf(placement)
        return placement

    def _generate_towers(
        self,
        programme: GeneratedProgramme,
        complexity: str,
        currency: str,
    ) -> list[GeneratedTower]:
        """Generate tower structures based on complexity."""
        towers = []

        if complexity == "simple":
            # Single tower, 2-3 layers, indemnity only
            towers.append(self._generate_indemnity_tower(
                programme, currency, num_layers=self.rng.randint(2, 3)
            ))

        elif complexity == "standard":
            # Primary + excess tower, 3-4 layers, with aggregate
            towers.append(self._generate_indemnity_tower(
                programme, currency, num_layers=self.rng.randint(3, 4),
                include_aggregate=True
            ))

        elif complexity == "complex":
            # Multiple towers: property + liability, 4-5 layers each
            towers.append(self._generate_indemnity_tower(
                programme, currency, num_layers=self.rng.randint(3, 5),
                include_aggregate=True,
                tower_name="Property Tower"
            ))
            towers.append(self._generate_indemnity_tower(
                programme, currency, num_layers=self.rng.randint(2, 4),
                include_aggregate=True,
                tower_name="Liability Tower"
            ))

        elif complexity == "rcv":
            # Indemnity tower + parametric supplement + optional pool
            towers.append(self._generate_indemnity_tower(
                programme, currency, num_layers=self.rng.randint(3, 4),
                include_aggregate=True,
                tower_name="Traditional Tower"
            ))
            towers.append(self._generate_parametric_tower(
                programme, currency
            ))
            if self.rng.random() < 0.4:
                towers.append(self._generate_pool_tower(
                    programme, currency
                ))

        return towers

    def _generate_indemnity_tower(
        self,
        programme: GeneratedProgramme,
        currency: str,
        num_layers: int = 3,
        include_aggregate: bool = False,
        tower_name: str = "Primary Tower",
    ) -> GeneratedTower:
        tower_id = self._uid("TWR")
        layers = []
        flows = []
        running_attachment = Decimal("0")

        # Generate ascending layers
        for i in range(num_layers):
            limit = self._money(5_000_000, 50_000_000, 5_000_000)
            layer_id = self._uid("LYR")

            coverage_types = self._pick(
                self.vocab.COVERAGE_TYPES[:7],
                self.rng.randint(1, 3)
            )

            scope = GeneratedScope(
                perils=programme.peril_scope,
                territories=programme.territory_scope,
                coverage_types=coverage_types,
                line_of_business=programme.line_of_business,
                party_roles=["PolicyHolder"],
                trigger_mode="Occurrence",
                defense_treatment=self._pick_one(["ErodesLimit", "OutsideLimit"]),
                reinstatement_status="Available" if i < 2 else "NotApplicable",
            )

            tank = GeneratedTank(
                tank_id=self._uid("TNK"),
                tank_type="Indemnity",
                capacity=limit,
                basis="PerOccurrence" if i < num_layers - 1 else "AnnualAggregate",
                scope=scope,
            )

            layer = GeneratedLayer(
                layer_id=layer_id,
                attachment=running_attachment,
                limit=limit,
                basis=tank.basis,
                tank=tank,
                flows=[],
            )
            layers.append(layer)
            running_attachment += limit

        # Build flow graph (WF1-acyclic: strictly downward)
        aggregate_tank = None
        if include_aggregate:
            agg_limit = sum(l.limit for l in layers) * Decimal("1.5")
            aggregate_tank = GeneratedTank(
                tank_id=self._uid("TNK"),
                tank_type="Indemnity",
                capacity=agg_limit,
                basis="AnnualAggregate",
                scope=layers[0].tank.scope,
            )

        precedence = 1
        for i, layer in enumerate(layers):
            # Erosion to aggregate
            if aggregate_tank:
                layer.flows.append(GeneratedFlow(
                    flow_id=self._uid("FLW"),
                    flow_type="Erosion",
                    source_tank_id=layer.tank.tank_id,
                    target_tank_id=aggregate_tank.tank_id,
                    precedence=precedence,
                ))
                precedence += 1

            # Attachment: lower layer exhaustion triggers upper layer
            if i > 0:
                layer.flows.append(GeneratedFlow(
                    flow_id=self._uid("FLW"),
                    flow_type="Attachment",
                    source_tank_id=layers[i - 1].tank.tank_id,
                    target_tank_id=layer.tank.tank_id,
                    precedence=precedence,
                ))
                precedence += 1

        return GeneratedTower(
            tower_id=tower_id,
            tower_name=tower_name,
            layers=layers,
        )

    def _generate_parametric_tower(
        self,
        programme: GeneratedProgramme,
        currency: str,
    ) -> GeneratedTower:
        """Generate a parametric CAT bond tower."""
        tower_id = self._uid("TWR")
        limit = self._money(50_000_000, 200_000_000, 25_000_000)

        scope = GeneratedScope(
            perils=programme.peril_scope[:2],
            territories=programme.territory_scope[:1],
            coverage_types=["PropertyDamage"],
            line_of_business=programme.line_of_business,
            party_roles=["PolicyHolder", "Investor"],
            trigger_mode="Parametric",
            collateral_status="FullyFunded",
        )

        index_name = self._pick_one(["PCS", "PERILS", "CAT-IN-A-BOX", "AIR"])
        threshold = self._money(1_000_000_000, 20_000_000_000, 1_000_000_000)

        tank = GeneratedTank(
            tank_id=self._uid("TNK"),
            tank_type="Parametric",
            capacity=limit,
            basis="EventTriggered",
            scope=scope,
            trigger_config={
                "expression_type": "Comparison",
                "index": index_name,
                "operator": "GE",
                "threshold": str(threshold),
                "graduated_tiers": [
                    {"threshold_pct": 50, "payout_pct": 50, "cap": str(limit * Decimal("0.5"))},
                    {"threshold_pct": 75, "payout_pct": 75, "cap": str(limit * Decimal("0.75"))},
                    {"threshold_pct": 100, "payout_pct": 100, "cap": str(limit)},
                ],
            },
            collateral_config={
                "amount": str(limit),
                "status": "FullyFunded",
                "trust_account": f"TRUST-{self._uid('COL')}",
            },
        )

        layer = GeneratedLayer(
            layer_id=self._uid("LYR"),
            attachment=Decimal("0"),
            limit=limit,
            basis="EventTriggered",
            tank=tank,
            flows=[
                GeneratedFlow(
                    flow_id=self._uid("FLW"),
                    flow_type="TriggerGate",
                    source_tank_id=tank.tank_id,
                    target_tank_id=tank.tank_id,  # self-gate
                    precedence=1,
                ),
                GeneratedFlow(
                    flow_id=self._uid("FLW"),
                    flow_type="GraduatedPayout",
                    source_tank_id=tank.tank_id,
                    target_tank_id=tank.tank_id,
                    precedence=2,
                ),
            ],
        )

        return GeneratedTower(
            tower_id=tower_id,
            tower_name="Parametric CAT Bond",
            layers=[layer],
        )

    def _generate_pool_tower(
        self,
        programme: GeneratedProgramme,
        currency: str,
    ) -> GeneratedTower:
        """Generate a pool participation tower."""
        tower_id = self._uid("TWR")
        pool_capacity = self._money(100_000_000, 500_000_000, 50_000_000)
        our_share = Decimal(str(self.rng.choice([5, 10, 15, 20, 25]))) / Decimal("100")
        our_limit = pool_capacity * our_share

        num_participants = self.rng.randint(3, 8)
        pool_participants = []
        remaining_share = Decimal("1.0") - our_share
        for i in range(num_participants - 1):
            if i == num_participants - 2:
                share = remaining_share
            else:
                share = (remaining_share / Decimal(str(num_participants - 1))).quantize(Decimal("0.01"))
                remaining_share -= share
            pool_participants.append({
                "participant_id": self._uid("PP"),
                "name": self._pick_one(self.vocab.INSURER_NAMES),
                "share": str(share),
                "payout_cap": str(pool_capacity * share * Decimal("0.8")),
            })

        scope = GeneratedScope(
            perils=programme.peril_scope,
            territories=programme.territory_scope,
            coverage_types=["PropertyDamage", "BusinessInterruption"],
            line_of_business=programme.line_of_business,
            party_roles=["PoolParticipant"],
            trigger_mode="PoolTriggered",
        )

        tank = GeneratedTank(
            tank_id=self._uid("TNK"),
            tank_type="Pool",
            capacity=our_limit,
            basis="PoolAggregate",
            scope=scope,
            pool_config={
                "total_capacity": str(pool_capacity),
                "our_share": str(our_share),
                "payout_basis": self._pick_one(["ProRata", "ExposureWeighted"]),
                "participants": pool_participants,
            },
        )

        layer = GeneratedLayer(
            layer_id=self._uid("LYR"),
            attachment=Decimal("0"),
            limit=our_limit,
            basis="PoolAggregate",
            tank=tank,
            flows=[
                GeneratedFlow(
                    flow_id=self._uid("FLW"),
                    flow_type="PoolDistribute",
                    source_tank_id=tank.tank_id,
                    target_tank_id=tank.tank_id,
                    precedence=1,
                ),
            ],
        )

        return GeneratedTower(
            tower_id=tower_id,
            tower_name="Pool Participation",
            layers=[layer],
        )

    def _generate_participants(self, n: int) -> list[GeneratedParticipant]:
        """Generate market participants with shares summing to ~1.0."""
        names = self._pick(self.vocab.INSURER_NAMES, n)
        shares = []
        remaining = Decimal("100")
        for i in range(n):
            if i == n - 1:
                share = remaining
            else:
                share = Decimal(str(self.rng.randint(5, int(remaining / (n - i)))))
                remaining -= share
            shares.append(share / Decimal("100"))

        participants = []
        for i, (name, share) in enumerate(zip(names, shares)):
            participants.append(GeneratedParticipant(
                participant_id=self._uid("MKT"),
                name=name,
                role="Leader" if i == 0 else "Follower",
                share=share,
                line_stamp=share * sum(
                    l.limit for t in [] for l in t.layers  # placeholder
                ) if False else self._money(1_000_000, 50_000_000),
            ))
        return participants

    def generate_cover_spans(self, placement: GeneratedPlacement) -> list[GeneratedCoverSpan]:
        """Materialise CoverSpans from a placement's towers (FBO Definition 5.6)."""
        spans = []
        for tower in placement.towers:
            for layer in tower.layers:
                tank = layer.tank
                span = GeneratedCoverSpan(
                    span_id=self._uid("CSP"),
                    floor=layer.attachment,
                    ceiling=layer.attachment + layer.limit,
                    capacity_share=Decimal("1.0"),
                    source_tank_id=tank.tank_id,
                    tank_type=tank.tank_type,
                    scope=tank.scope,
                    term_hash=hashlib.sha256(
                        f"{tank.tank_id}:{tank.capacity}:{tank.basis}".encode()
                    ).hexdigest(),
                    computed_at=datetime.utcnow(),
                )
                spans.append(span)
        return spans

    def _serialise_placement_to_rdf(self, placement: GeneratedPlacement):
        """Serialise a placement to its RDF graph."""
        g = placement.graph
        g.bind("fbo", FBO)
        g.bind("nsdp", NSDP)
        g.bind("risk", RISK)
        g.bind("geo", GEO)
        g.bind("lob", LOB)
        g.bind("synth", SYNTH)

        p_uri = SYNTH[placement.placement_id]
        g.add((p_uri, RDF.type, NSDP.Placement))
        g.add((p_uri, NSDP.insuredName, Literal(placement.insured_name)))
        g.add((p_uri, NSDP.brokerName, Literal(placement.broker)))
        g.add((p_uri, NSDP.inceptionDate, Literal(placement.inception, datatype=XSD.date)))
        g.add((p_uri, NSDP.expiryDate, Literal(placement.expiry, datatype=XSD.date)))
        g.add((p_uri, NSDP.currency, Literal(placement.currency)))

        # Programme
        prg = SYNTH[placement.programme.programme_id]
        g.add((prg, RDF.type, NSDP.Programme))
        g.add((prg, NSDP.programmeName, Literal(placement.programme.programme_name)))
        g.add((prg, NSDP.hasLineOfBusiness, LOB[placement.programme.line_of_business]))
        g.add((p_uri, NSDP.hasProgramme, prg))

        # Towers, layers, tanks, flows
        for tower in placement.towers:
            t_uri = SYNTH[tower.tower_id]
            g.add((t_uri, RDF.type, FBO.Tower))
            g.add((t_uri, RDFS.label, Literal(tower.tower_name)))
            g.add((prg, FBO.hasTower, t_uri))

            for layer in tower.layers:
                l_uri = SYNTH[layer.layer_id]
                g.add((l_uri, RDF.type, FBO.Layer))
                g.add((l_uri, FBO.hasAttachment, Literal(layer.attachment, datatype=XSD.decimal)))
                g.add((l_uri, FBO.hasLimit, Literal(layer.limit, datatype=XSD.decimal)))
                g.add((t_uri, FBO.hasLayer, l_uri))

                # Tank
                tk_uri = SYNTH[layer.tank.tank_id]
                g.add((tk_uri, RDF.type, FBO.CapacityTank))
                g.add((tk_uri, FBO.hasTankType, FBO[layer.tank.tank_type]))
                g.add((tk_uri, FBO.hasCapacity, Literal(layer.tank.capacity, datatype=XSD.decimal)))
                g.add((tk_uri, FBO.hasBasis, FBO[layer.tank.basis]))
                g.add((l_uri, FBO.hasTank, tk_uri))

                # Scope (20 dims — we populate the ones that matter)
                sc_uri = SYNTH[self._uid("SC")]
                g.add((sc_uri, RDF.type, FBO.ScopeQualifier))
                g.add((tk_uri, FBO.hasScope, sc_uri))

                for peril in layer.tank.scope.perils:
                    g.add((sc_uri, FBO.hasPeril, RISK[peril]))
                for terr in layer.tank.scope.territories:
                    g.add((sc_uri, FBO.hasTerritory, GEO[terr]))
                for ct in layer.tank.scope.coverage_types:
                    g.add((sc_uri, FBO.hasCoverageType, FBO[ct]))
                g.add((sc_uri, FBO.hasLineOfBusiness, LOB[layer.tank.scope.line_of_business]))
                for pr in layer.tank.scope.party_roles:
                    g.add((sc_uri, FBO.hasPartyRole, FBO[pr]))
                g.add((sc_uri, FBO.hasTriggerMode, FBO[layer.tank.scope.trigger_mode]))
                g.add((sc_uri, FBO.hasDefenseTreatment, FBO[layer.tank.scope.defense_treatment]))
                g.add((sc_uri, FBO.hasCollateralStatus, FBO[layer.tank.scope.collateral_status]))
                g.add((sc_uri, FBO.hasReinstatementStatus, FBO[layer.tank.scope.reinstatement_status]))

                # Trigger config
                if layer.tank.trigger_config:
                    tc_uri = SYNTH[self._uid("TC")]
                    g.add((tc_uri, RDF.type, FBO.TriggerConfig))
                    g.add((tk_uri, FBO.hasTriggerConfig, tc_uri))
                    tc = layer.tank.trigger_config
                    te_uri = SYNTH[self._uid("TE")]
                    g.add((te_uri, RDF.type, FBO.AtomicTrigger))
                    g.add((te_uri, FBO.hasOperator, FBO[tc["operator"]]))
                    g.add((te_uri, FBO.hasThreshold,
                           Literal(Decimal(tc["threshold"]), datatype=XSD.decimal)))
                    g.add((tc_uri, FBO.hasTriggerExpression, te_uri))

                # Pool config
                if layer.tank.pool_config:
                    pc_uri = SYNTH[self._uid("PC")]
                    g.add((pc_uri, RDF.type, FBO.PoolConfig))
                    g.add((tk_uri, FBO.hasPoolConfig, pc_uri))
                    pc = layer.tank.pool_config
                    g.add((pc_uri, FBO.hasPayoutBasis, FBO[pc["payout_basis"]]))
                    for pp in pc["participants"]:
                        pp_uri = SYNTH[pp["participant_id"]]
                        g.add((pp_uri, RDF.type, FBO.PoolParticipation))
                        g.add((pp_uri, FBO.hasContributionShare,
                               Literal(Decimal(pp["share"]), datatype=XSD.decimal)))
                        g.add((pp_uri, FBO.hasPayoutCap,
                               Literal(Decimal(pp["payout_cap"]), datatype=XSD.decimal)))
                        g.add((pc_uri, FBO.hasParticipant, pp_uri))

                # Flows
                for flow in layer.flows:
                    f_uri = SYNTH[flow.flow_id]
                    g.add((f_uri, RDF.type, FBO.FlowAction))
                    g.add((f_uri, FBO.hasFlowType, FBO[flow.flow_type]))
                    g.add((f_uri, FBO.hasSourceTank, SYNTH[flow.source_tank_id]))
                    g.add((f_uri, FBO.hasTargetTank, SYNTH[flow.target_tank_id]))
                    g.add((f_uri, FBO.hasPrecedence, Literal(flow.precedence, datatype=XSD.integer)))


# ═══════════════════════════════════════════════════════════════════
# SECTION 2: External Schema Generation
# ═══════════════════════════════════════════════════════════════════

class FieldDistortion(Enum):
    """
    How a target ontology concept gets distorted in an external schema.
    Each distortion represents a real-world data integration challenge.
    """
    # A property chain (e.g., Tank → Scope → Peril) becomes a single flat field
    FLATTEN_CHAIN = "flatten_chain"
    # Multiple ontology concepts combined into one field with a delimiter
    CONCATENATE = "concatenate"
    # A single ontology concept split across multiple fields
    SPLIT = "split"
    # A concept is encoded as a code/ID that needs lookup
    CODE_ENCODE = "code_encode"
    # Nested JSON/XML in a single text field
    NESTED_BLOB = "nested_blob"
    # Reversed/inverted semantics (e.g., "deductible" stored where "limit" expected)
    SEMANTIC_SHIFT = "semantic_shift"
    # Units embedded in value (e.g., "25M USD" instead of separate amount/currency)
    INLINE_UNIT = "inline_unit"
    # Boolean encoded as Y/N, 1/0, TRUE/FALSE, "Yes"/"No"
    BOOLEAN_VARIANT = "boolean_variant"
    # Date in non-standard format
    DATE_VARIANT = "date_variant"
    # Hierarchy flattened to a single level
    FLATTEN_HIERARCHY = "flatten_hierarchy"
    # Name used instead of code/IRI
    LABEL_REFERENCE = "label_reference"
    # Completely different terminology for the same concept
    DOMAIN_RENAME = "domain_rename"


@dataclass
class ExternalField:
    """A field in an external schema."""
    name: str
    data_type: str  # "string", "number", "boolean", "date", "json"
    nullable: bool
    description: str
    # Mapping metadata (ground truth — not exposed to the pipeline)
    target_concept: str  # FBO/NSDP class or property
    distortion: FieldDistortion
    mapping_notes: str  # How this field maps to the target


@dataclass
class ExternalSchema:
    """A fabricated external data schema, deliberately misaligned with FBO/NSDP."""
    schema_id: str
    schema_name: str
    description: str
    source_system: str
    fields: list[ExternalField]
    # What FBO structures this schema is trying to represent
    target_domain: str  # "placement", "tower", "layer", "submission", "quote", "claim"
    # The naming convention used
    naming_convention: str  # "camelCase", "snake_case", "SCREAMING_SNAKE", "Hungarian", "terse"
    # Additional structural distortions
    structural_notes: list[str]


@dataclass
class ExternalInstance:
    """An instance conforming to an external schema."""
    instance_id: str
    schema_id: str
    field_values: dict[str, Any]
    # Ground truth: the FBO individuals this instance should map to
    ground_truth_iris: list[str]


class ExternalSchemaGenerator:
    """
    Generates deliberately misaligned external schemas that represent
    the kinds of data sources the MORK mapping pipeline must handle.

    Design goals:
    - Schemas should NOT look like the FBO/NSDP ontology
    - Each schema introduces multiple distortion patterns
    - Instance data must be internally consistent with the schema
    - Ground truth mappings must be provided for validation
    """

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.vocab = VocabularyPool()
        self._counter = 0

    def _uid(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter:04d}"

    # ── Naming convention distortions ──────────────────────────

    NAMING_TRANSFORMS = {
        "camelCase": lambda s: s[0].lower() + s[1:] if s else s,
        "snake_case": lambda s: ''.join(
            f'_{c.lower()}' if c.isupper() else c for c in s
        ).lstrip('_'),
        "SCREAMING_SNAKE": lambda s: ''.join(
            f'_{c}' if c.isupper() else c.upper() for c in s
        ).lstrip('_'),
        "Hungarian": lambda s: "str" + s if s else s,
        "terse": lambda s: s[:3].lower() + s[-3:].lower() if len(s) > 6 else s.lower(),
    }

    def _transform_name(self, concept: str, convention: str) -> str:
        base = self.NAMING_TRANSFORMS.get(convention, lambda s: s)(concept)
        return base

    # ── Schema archetypes ─────────────────────────────────────

    def generate_schema(self) -> ExternalSchema:
        """Generate a single external schema with a random archetype."""
        archetype = self.rng.choice([
            self._archetype_flat_submission,
            self._archetype_nested_quote,
            self._archetype_legacy_bordereaux,
            self._archetype_api_response,
            self._archetype_spreadsheet_extract,
            self._archetype_reinsurance_slip,
            self._archetype_claims_feed,
            self._archetype_catastrophe_model_output,
        ])
        return archetype()

    def _archetype_flat_submission(self) -> ExternalSchema:
        """
        Mimics a broker's flat CSV submission.
        Everything about a placement is in one row.
        Tower/layer structure is lost — just aggregate numbers.
        Perils and territories are comma-separated in a single field.
        """
        convention = self.rng.choice(["camelCase", "snake_case"])
        sid = self._uid("SCH")

        fields = [
            ExternalField(
                name=self._transform_name("SubmissionRef", convention),
                data_type="string", nullable=False,
                description="Unique submission reference",
                target_concept="nsdp:Placement",
                distortion=FieldDistortion.DOMAIN_RENAME,
                mapping_notes="Maps to placement identifier",
            ),
            ExternalField(
                name=self._transform_name("ClientName", convention),
                data_type="string", nullable=False,
                description="Name of the insured party",
                target_concept="nsdp:insuredName",
                distortion=FieldDistortion.DOMAIN_RENAME,
                mapping_notes="Direct map to insuredName",
            ),
            ExternalField(
                name=self._transform_name("EffectiveDate", convention),
                data_type="string", nullable=False,
                description="Policy effective date (DD/MM/YYYY)",
                target_concept="nsdp:inceptionDate",
                distortion=FieldDistortion.DATE_VARIANT,
                mapping_notes="Non-ISO date format, maps to inceptionDate",
            ),
            ExternalField(
                name=self._transform_name("ExpiryDate", convention),
                data_type="string", nullable=False,
                description="Policy expiry date (DD/MM/YYYY)",
                target_concept="nsdp:expiryDate",
                distortion=FieldDistortion.DATE_VARIANT,
                mapping_notes="Non-ISO date format",
            ),
            ExternalField(
                name=self._transform_name("TotalLimitCcy", convention),
                data_type="string", nullable=False,
                description="Total programme limit with currency, e.g. '25M USD'",
                target_concept="fbo:hasCapacity",
                distortion=FieldDistortion.INLINE_UNIT,
                mapping_notes="Combines fbo:hasCapacity and nsdp:currency. Needs parsing: '25M USD' → 25000000 + USD",
            ),
            ExternalField(
                name=self._transform_name("PerilsApplicable", convention),
                data_type="string", nullable=False,
                description="Comma-separated list of perils",
                target_concept="fbo:hasPeril",
                distortion=FieldDistortion.CONCATENATE,
                mapping_notes="Split on comma, each maps to fbo:hasPeril on ScopeQualifier. Names not IRIs.",
            ),
            ExternalField(
                name=self._transform_name("TerritoryList", convention),
                data_type="string", nullable=True,
                description="Semicolon-separated territory codes",
                target_concept="fbo:hasTerritory",
                distortion=FieldDistortion.CONCATENATE,
                mapping_notes="Split on semicolon, each maps to fbo:hasTerritory. Uses ISO-like codes, not ontology IRIs.",
            ),
            ExternalField(
                name=self._transform_name("ClassOfBusiness", convention),
                data_type="string", nullable=False,
                description="Line of business category",
                target_concept="fbo:hasLineOfBusiness",
                distortion=FieldDistortion.LABEL_REFERENCE,
                mapping_notes="Free-text label, needs fuzzy match to LOB vocabulary",
            ),
            ExternalField(
                name=self._transform_name("DeductibleAmt", convention),
                data_type="number", nullable=True,
                description="Per-occurrence deductible amount",
                target_concept="fbo:hasAttachment",
                distortion=FieldDistortion.SEMANTIC_SHIFT,
                mapping_notes="'Deductible' in submission language = 'attachment' in FBO for the primary layer",
            ),
            ExternalField(
                name=self._transform_name("NumberOfLayers", convention),
                data_type="number", nullable=True,
                description="How many layers in the programme",
                target_concept="fbo:Tower",
                distortion=FieldDistortion.FLATTEN_CHAIN,
                mapping_notes="Metadata about tower structure; no direct FBO equivalent — informs generation",
            ),
            ExternalField(
                name=self._transform_name("LayerSchedule", convention),
                data_type="json", nullable=True,
                description="JSON array of layer details [{limit, xs, basis}]",
                target_concept="fbo:Layer",
                distortion=FieldDistortion.NESTED_BLOB,
                mapping_notes="Nested structure maps to multiple Layer/Tank individuals. 'xs' = attachment, 'basis' needs vocabulary lookup.",
            ),
            ExternalField(
                name=self._transform_name("CyberIncluded", convention),
                data_type="string", nullable=True,
                description="Whether cyber coverage is included (Y/N)",
                target_concept="fbo:hasPeril",
                distortion=FieldDistortion.BOOLEAN_VARIANT,
                mapping_notes="Y → add CyberPeril to scope; N or null → do not include",
            ),
            ExternalField(
                name=self._transform_name("BrokerRef", convention),
                data_type="string", nullable=False,
                description="Placing broker reference",
                target_concept="nsdp:brokerName",
                distortion=FieldDistortion.CODE_ENCODE,
                mapping_notes="Broker code, needs lookup against broker reference data",
            ),
        ]

        return ExternalSchema(
            schema_id=sid,
            schema_name="Broker Flat Submission Format",
            description="Single-row-per-placement CSV commonly exported from broker management systems",
            source_system=self.rng.choice(["EPIC", "BrokerEdge", "Acturis", "Custom Excel"]),
            fields=fields,
            target_domain="placement",
            naming_convention=convention,
            structural_notes=[
                "Tower/layer structure is collapsed into a single row with optional nested JSON",
                "All scope dimensions (perils, territories) are concatenated into strings",
                "Currency is embedded in the limit field",
                "Dates use DD/MM/YYYY format",
                "Deductible terminology instead of attachment",
            ],
        )

    def _archetype_nested_quote(self) -> ExternalSchema:
        """
        Mimics an insurer's API response for a quote.
        Deeply nested JSON with its own internal identifiers.
        Uses completely different terminology (e.g., "section" for "layer").
        """
        convention = "camelCase"
        sid = self._uid("SCH")

        fields = [
            ExternalField(
                name="quoteId", data_type="string", nullable=False,
                description="Internal quote reference UUID",
                target_concept="nsdp:Placement",
                distortion=FieldDistortion.DOMAIN_RENAME,
                mapping_notes="UUID-style ID, maps to placement identifier in the quote context",
            ),
            ExternalField(
                name="proposedInsured", data_type="json", nullable=False,
                description='{"name": str, "sic": str, "revenue": number, "domicile": str}',
                target_concept="nsdp:InsuredParty",
                distortion=FieldDistortion.NESTED_BLOB,
                mapping_notes="Nested JSON blob maps to InsuredParty + FinancialDetails. Revenue needs separate FinancialDetails individual.",
            ),
            ExternalField(
                name="programmeStructure", data_type="json", nullable=False,
                description='{"sections": [{"sectionRef": str, "attachment": number, "limitOfLiability": number, "basisOfSettlement": str, "reinstatements": number}]}',
                target_concept="fbo:Tower",
                distortion=FieldDistortion.NESTED_BLOB,
                mapping_notes="'sections' = layers. 'limitOfLiability' = fbo:hasCapacity. 'basisOfSettlement' = fbo:hasBasis. 'reinstatements' maps to reinstatementStatus.",
            ),
            ExternalField(
                name="perils.included", data_type="json", nullable=False,
                description='["ALL_RISKS", "FLOOD", ...] or ["EXCLUDING:WAR", "EXCLUDING:NUCLEAR"]',
                target_concept="fbo:ScopeQualifier",
                distortion=FieldDistortion.CONCATENATE,
                mapping_notes="Array of peril codes. 'EXCLUDING:X' prefix means add to exclusion scope. Codes use SCREAMING_SNAKE, not ontology IRIs.",
            ),
            ExternalField(
                name="territory", data_type="json", nullable=False,
                description='{"primary": "US", "subnational": ["FL", "TX", "LA"], "worldwide": false}',
                target_concept="fbo:hasTerritory",
                distortion=FieldDistortion.SPLIT,
                mapping_notes="Territory split into primary/subnational/worldwide flag. Must reconstruct into fbo:hasTerritory set.",
            ),
            ExternalField(
                name="pricing", data_type="json", nullable=True,
                description='{"grossPremium": number, "commission": number, "netPremium": number, "ccy": str}',
                target_concept="nsdp:Premium",
                distortion=FieldDistortion.NESTED_BLOB,
                mapping_notes="Premium details, not directly FBO but informs financial context.",
            ),
            ExternalField(
                name="indicativeTerms", data_type="boolean", nullable=False,
                description="Whether these are indicative (true) or firm (false) terms",
                target_concept="mork:reviewStatus",
                distortion=FieldDistortion.SEMANTIC_SHIFT,
                mapping_notes="indicative=true maps to DRAFT status; false maps to APPROVED",
            ),
            ExternalField(
                name="specialConditions", data_type="string", nullable=True,
                description="Free text special conditions, endorsements, warranties",
                target_concept="nsdp:Clause",
                distortion=FieldDistortion.FLATTEN_CHAIN,
                mapping_notes="Unstructured text containing multiple clauses. Needs NLP decomposition at Intent Agent level.",
            ),
        ]

        return ExternalSchema(
            schema_id=sid,
            schema_name="Insurer Quote API Response",
            description="Nested JSON response from an insurer's underwriting platform",
            source_system=self.rng.choice(["Underwrite.ai", "GuideWire", "Duck Creek", "Custom REST API"]),
            fields=fields,
            target_domain="quote",
            naming_convention=convention,
            structural_notes=[
                "Uses 'sections' instead of 'layers'",
                "Insured details are a nested blob, not separate fields",
                "Perils use EXCLUDING: prefix for exclusions",
                "Territory is split into primary/subnational/worldwide",
                "Financial details mixed in with structural data",
            ],
        )

    def _archetype_legacy_bordereaux(self) -> ExternalSchema:
        """
        Mimics a legacy bordereaux (bound policy register).
        Uses SCREAMING_SNAKE_CASE, fixed-width-inspired field names,
        Hungarian-ish prefixes, and encodes everything as strings.
        """
        convention = "SCREAMING_SNAKE"
        sid = self._uid("SCH")

        fields = [
            ExternalField(
                name="REC_ID", data_type="string", nullable=False,
                description="Record identifier (6-digit sequential)",
                target_concept="nsdp:Placement",
                distortion=FieldDistortion.CODE_ENCODE,
                mapping_notes="Sequential ID, maps to placement identifier",
            ),
            ExternalField(
                name="POL_NO", data_type="string", nullable=False,
                description="Policy number (format: B0241-XXXX-XXXX)",
                target_concept="nsdp:policyNumber",
                distortion=FieldDistortion.CODE_ENCODE,
                mapping_notes="Structured policy number with embedded year and sequence",
            ),
            ExternalField(
                name="ASRD_NM", data_type="string", nullable=False,
                description="Assured name (truncated to 40 chars)",
                target_concept="nsdp:insuredName",
                distortion=FieldDistortion.DOMAIN_RENAME,
                mapping_notes="'Assured' = 'Insured'. Truncated, may need reconciliation.",
            ),
            ExternalField(
                name="EFF_DT", data_type="string", nullable=False,
                description="Effective date (YYYYMMDD)",
                target_concept="nsdp:inceptionDate",
                distortion=FieldDistortion.DATE_VARIANT,
                mapping_notes="Compact date format YYYYMMDD, no separators",
            ),
            ExternalField(
                name="EXP_DT", data_type="string", nullable=False,
                description="Expiry date (YYYYMMDD)",
                target_concept="nsdp:expiryDate",
                distortion=FieldDistortion.DATE_VARIANT,
                mapping_notes="Same compact format",
            ),
            ExternalField(
                name="LMT_AMT", data_type="string", nullable=False,
                description="Limit amount in cents (12-digit zero-padded)",
                target_concept="fbo:hasCapacity",
                distortion=FieldDistortion.CODE_ENCODE,
                mapping_notes="Amount in CENTS, zero-padded to 12 digits. Divide by 100 for actual value.",
            ),
            ExternalField(
                name="DED_AMT", data_type="string", nullable=False,
                description="Deductible amount in cents (12-digit zero-padded)",
                target_concept="fbo:hasAttachment",
                distortion=FieldDistortion.CODE_ENCODE,
                mapping_notes="Deductible in cents. Maps to primary layer attachment.",
            ),
            ExternalField(
                name="CCY_CD", data_type="string", nullable=False,
                description="ISO 4217 currency code",
                target_concept="nsdp:currency",
                distortion=FieldDistortion.CODE_ENCODE,
                mapping_notes="Standard ISO currency code",
            ),
            ExternalField(
                name="COB_CD", data_type="string", nullable=False,
                description="Class of business code (2-digit internal code)",
                target_concept="fbo:hasLineOfBusiness",
                distortion=FieldDistortion.CODE_ENCODE,
                mapping_notes="Internal 2-digit code: 01=Property, 02=Casualty, 03=Marine, 04=Aviation, 05=Energy, 06=Cyber, 99=Other. Needs lookup table.",
            ),
            ExternalField(
                name="PRL_CD1", data_type="string", nullable=True,
                description="Primary peril code",
                target_concept="fbo:hasPeril",
                distortion=FieldDistortion.SPLIT,
                mapping_notes="Up to 3 peril code fields (PRL_CD1, PRL_CD2, PRL_CD3). Internal codes, need lookup.",
            ),
            ExternalField(
                name="PRL_CD2", data_type="string", nullable=True,
                description="Secondary peril code",
                target_concept="fbo:hasPeril",
                distortion=FieldDistortion.SPLIT,
                mapping_notes="See PRL_CD1",
            ),
            ExternalField(
                name="PRL_CD3", data_type="string", nullable=True,
                description="Tertiary peril code",
                target_concept="fbo:hasPeril",
                distortion=FieldDistortion.SPLIT,
                mapping_notes="See PRL_CD1",
            ),
            ExternalField(
                name="TERR_CD", data_type="string", nullable=False,
                description="Territory code (3-char)",
                target_concept="fbo:hasTerritory",
                distortion=FieldDistortion.CODE_ENCODE,
                mapping_notes="3-character internal territory code. Needs lookup.",
            ),
            ExternalField(
                name="LYR_CNT", data_type="string", nullable=True,
                description="Number of layers",
                target_concept="fbo:Tower",
                distortion=FieldDistortion.FLATTEN_CHAIN,
                mapping_notes="Metadata — no direct FBO equivalent",
            ),
            ExternalField(
                name="REIN_FL", data_type="string", nullable=True,
                description="Reinstatement flag (Y/N)",
                target_concept="fbo:hasReinstatementStatus",
                distortion=FieldDistortion.BOOLEAN_VARIANT,
                mapping_notes="Y → Available, N → NotApplicable",
            ),
            ExternalField(
                name="SIG_LN_AMT", data_type="string", nullable=True,
                description="Signed line amount in cents",
                target_concept="nsdp:signedLineAmount",
                distortion=FieldDistortion.CODE_ENCODE,
                mapping_notes="Our participation amount in cents",
            ),
        ]

        return ExternalSchema(
            schema_id=sid,
            schema_name="Legacy Bordereaux Extract",
            description="Fixed-width-inspired CSV from a legacy policy administration system",
            source_system="LPAS (Legacy Policy Admin System)",
            fields=fields,
            target_domain="placement",
            naming_convention=convention,
            structural_notes=[
                "All values are strings (legacy fixed-width heritage)",
                "Monetary amounts are in CENTS, zero-padded",
                "Dates use YYYYMMDD format without separators",
                "Perils split across 3 separate code fields",
                "Internal codes for LOB, territories, perils — need lookup tables",
                "Field names are truncated abbreviations",
            ],
        )

    def _archetype_api_response(self) -> ExternalSchema:
        """
        Mimics a modern REST API response from a data vendor.
        camelCase JSON, deeply nested, uses UUIDs, mixes
        reference data inline.
        """
        convention = "camelCase"
        sid = self._uid("SCH")

        fields = [
            ExternalField(
                name="submissionUuid", data_type="string", nullable=False,
                description="UUID v4 submission identifier",
                target_concept="nsdp:Placement",
                distortion=FieldDistortion.DOMAIN_RENAME,
                mapping_notes="UUID, maps to placement identifier",
            ),
            ExternalField(
                name="riskProfile", data_type="json", nullable=False,
                description='{"naics": str, "sicCode": str, "annualRevenue": {"amount": number, "currency": str}, "employeeCount": number, "publiclyTraded": bool}',
                target_concept="nsdp:InsuredParty",
                distortion=FieldDistortion.NESTED_BLOB,
                mapping_notes="Nested risk profile. annualRevenue maps to FinancialDetails. naics/sicCode need SKOS lookup. publiclyTraded is advisory metadata.",
            ),
            ExternalField(
                name="exposureGeography", data_type="json", nullable=False,
                description='[{"country": str, "region": str, "tiv": number, "percentage": number}]',
                target_concept="fbo:hasTerritory",
                distortion=FieldDistortion.NESTED_BLOB,
                mapping_notes="Array of exposure locations. Each entry maps to a territory scope dimension. TIV (Total Insured Value) is supplementary A-Box data.",
            ),
            ExternalField(
                name="coverageRequirements", data_type="json", nullable=False,
                description='{"totalLimit": number, "primaryDeductible": number, "aggregateLimit": number, "desiredLayers": [{"name": str, "attachmentPoint": number, "width": number}], "requestedPerils": [str], "excludedPerils": [str]}',
                target_concept="fbo:CapacityTank",
                distortion=FieldDistortion.NESTED_BLOB,
                mapping_notes="Massive nested blob. totalLimit → programme aggregate. primaryDeductible → first layer attachment. desiredLayers → Tower/Layer/Tank. requestedPerils/excludedPerils → ScopeQualifier inclusion/exclusion.",
            ),
            ExternalField(
                name="marketingStatus", data_type="string", nullable=False,
                description="Pipeline status: PROSPECT/SUBMITTED/QUOTED/BOUND/DECLINED",
                target_concept="mork:reviewStatus",
                distortion=FieldDistortion.DOMAIN_RENAME,
                mapping_notes="Pipeline stage → maps to different MORK lifecycle states",
            ),
            ExternalField(
                name="catModelResults", data_type="json", nullable=True,
                description='{"modelVendor": str, "returnPeriod": number, "aal": number, "oel": number, "pml250": number}',
                target_concept="nsdp:RiskAnalysis",
                distortion=FieldDistortion.NESTED_BLOB,
                mapping_notes="Catastrophe model output. Not directly FBO scope but informs pricing and gap analysis.",
            ),
            ExternalField(
                name="previousPlacements", data_type="json", nullable=True,
                description='[{"year": number, "leadMarket": str, "premium": number, "claims": number}]',
                target_concept="nsdp:PlacementHistory",
                distortion=FieldDistortion.NESTED_BLOB,
                mapping_notes="Historical placement array. Each entry is a prior year's placement summary.",
            ),
        ]

        return ExternalSchema(
            schema_id=sid,
            schema_name="Risk Data Vendor API",
            description="Modern JSON API response from a risk data aggregation platform",
            source_system=self.rng.choice(["RiskStream", "Verisk API", "CyberCube", "Moody's RMS"]),
            fields=fields,
            target_domain="submission",
            naming_convention=convention,
            structural_notes=[
                "Everything is nested JSON — no flat fields except the ID and status",
                "Combines risk profile, exposure, coverage, and analytics in one response",
                "Uses 'width' instead of 'limit' for layer sizing",
                "Includes cat model results that have no direct FBO mapping",
                "Mixes structural data (layers) with analytical data (PML)",
            ],
        )

    def _archetype_spreadsheet_extract(self) -> ExternalSchema:
        """
        Mimics a manually maintained Excel spreadsheet extract.
        Inconsistent naming, mixed types in columns, free-text annotations.
        """
        convention = "terse"
        sid = self._uid("SCH")

        fields = [
            ExternalField(
                name="ref", data_type="string", nullable=False,
                description="Our reference",
                target_concept="nsdp:Placement",
                distortion=FieldDistortion.DOMAIN_RENAME,
                mapping_notes="Free-form reference string",
            ),
            ExternalField(
                name="insured / client", data_type="string", nullable=False,
                description="Insured name (sometimes includes broker in parens)",
                target_concept="nsdp:insuredName",
                distortion=FieldDistortion.CONCATENATE,
                mapping_notes="May contain 'ClientName (BrokerName)' — needs parsing",
            ),
            ExternalField(
                name="cov", data_type="string", nullable=False,
                description="Coverage type abbreviation",
                target_concept="fbo:hasCoverageType",
                distortion=FieldDistortion.CODE_ENCODE,
                mapping_notes="Abbreviated: PD=PropertyDamage, BI=BusinessInterruption, GL=GeneralLiability, CY=Cyber, PI=ProfessionalIndemnity",
            ),
            ExternalField(
                name="lim", data_type="string", nullable=False,
                description="Limit — sometimes just a number, sometimes '10m', sometimes '10,000,000'",
                target_concept="fbo:hasCapacity",
                distortion=FieldDistortion.INLINE_UNIT,
                mapping_notes="Inconsistent format: bare number, 'm' suffix, or comma-separated. Always in the placement currency.",
            ),
            ExternalField(
                name="xs", data_type="string", nullable=True,
                description="Excess / deductible — same format issues as lim",
                target_concept="fbo:hasAttachment",
                distortion=FieldDistortion.INLINE_UNIT,
                mapping_notes="'xs' = attachment. Same parsing challenges as lim.",
            ),
            ExternalField(
                name="ccy", data_type="string", nullable=False,
                description="Currency",
                target_concept="nsdp:currency",
                distortion=FieldDistortion.LABEL_REFERENCE,
                mapping_notes="Sometimes ISO code, sometimes symbol ($, £, €), sometimes full name",
            ),
            ExternalField(
                name="inc/exp", data_type="string", nullable=False,
                description="Inception/Expiry as a single field: 'DD/MM/YY - DD/MM/YY'",
                target_concept="nsdp:inceptionDate",
                distortion=FieldDistortion.CONCATENATE,
                mapping_notes="TWO dates in one field separated by ' - '. First is inception, second is expiry. 2-digit year.",
            ),
            ExternalField(
                name="perils", data_type="string", nullable=True,
                description="Free text peril description",
                target_concept="fbo:hasPeril",
                distortion=FieldDistortion.LABEL_REFERENCE,
                mapping_notes="Free text like 'All risks excl. war & terror'. Needs NLP decomposition.",
            ),
            ExternalField(
                name="terr", data_type="string", nullable=True,
                description="Territory — free text",
                target_concept="fbo:hasTerritory",
                distortion=FieldDistortion.LABEL_REFERENCE,
                mapping_notes="Free text like 'USA - Gulf states' or 'Worldwide' or 'EU27'",
            ),
            ExternalField(
                name="notes", data_type="string", nullable=True,
                description="Free text notes — may contain material underwriting info",
                target_concept="nsdp:Clause",
                distortion=FieldDistortion.FLATTEN_CHAIN,
                mapping_notes="Unstructured. May contain sublimit info, conditions, endorsement references.",
            ),
            ExternalField(
                name="our line %", data_type="string", nullable=True,
                description="Our signed line percentage",
                target_concept="nsdp:signedLinePercentage",
                distortion=FieldDistortion.INLINE_UNIT,
                mapping_notes="Sometimes '15%', sometimes '0.15', sometimes '15'. Needs normalisation.",
            ),
        ]

        return ExternalSchema(
            schema_id=sid,
            schema_name="Manual Spreadsheet Extract",
            description="CSV exported from a manually maintained Excel tracking spreadsheet",
            source_system="Excel (manual)",
            fields=fields,
            target_domain="placement",
            naming_convention=convention,
            structural_notes=[
                "Human-generated data with inconsistent formatting",
                "Multiple concepts crammed into single fields",
                "Free-text fields containing structured information",
                "Dates combined in a single field",
                "Percentage format varies row to row",
                "Field names contain spaces and special characters",
            ],
        )

    def _archetype_reinsurance_slip(self) -> ExternalSchema:
        """
        Mimics reinsurance treaty/facultative data.
        Uses reinsurance-specific terminology.
        """
        convention = "snake_case"
        sid = self._uid("SCH")

        fields = [
            ExternalField(
                name="contract_ref", data_type="string", nullable=False,
                description="Contract reference",
                target_concept="nsdp:Placement",
                distortion=FieldDistortion.DOMAIN_RENAME,
                mapping_notes="Reinsurance contract reference",
            ),
            ExternalField(
                name="cedent_name", data_type="string", nullable=False,
                description="Name of the ceding company",
                target_concept="nsdp:insuredName",
                distortion=FieldDistortion.SEMANTIC_SHIFT,
                mapping_notes="'Cedent' in reinsurance = 'Insured' in direct. Maps to insuredName with PartyRole=Cedent.",
            ),
            ExternalField(
                name="reinsurer_panel", data_type="json", nullable=False,
                description='[{"name": str, "share_pct": number, "signed_line": number}]',
                target_concept="nsdp:Participant",
                distortion=FieldDistortion.NESTED_BLOB,
                mapping_notes="Array of reinsurers. Each maps to a market participant with PartyRole=Reinsurer.",
            ),
            ExternalField(
                name="treaty_type", data_type="string", nullable=False,
                description="QS (Quota Share), XL (Excess of Loss), FAC (Facultative)",
                target_concept="fbo:CapacityTank",
                distortion=FieldDistortion.CODE_ENCODE,
                mapping_notes="Treaty type determines tank structure: QS=proportional, XL=excess tower, FAC=single layer.",
            ),
            ExternalField(
                name="retention", data_type="number", nullable=False,
                description="Cedent's retention amount",
                target_concept="fbo:hasAttachment",
                distortion=FieldDistortion.SEMANTIC_SHIFT,
                mapping_notes="'Retention' in reinsurance = 'attachment' for the ceded layer.",
            ),
            ExternalField(
                name="cession_limit", data_type="number", nullable=False,
                description="Maximum amount ceded to reinsurers",
                target_concept="fbo:hasCapacity",
                distortion=FieldDistortion.SEMANTIC_SHIFT,
                mapping_notes="'Cession limit' = FBO capacity of the reinsured layer.",
            ),
            ExternalField(
                name="aggregate_limit", data_type="number", nullable=True,
                description="Annual aggregate deductible or limit",
                target_concept="fbo:AnnualAggregate",
                distortion=FieldDistortion.FLATTEN_CHAIN,
                mapping_notes="Maps to a separate AnnualAggregate tank with basis=AnnualAggregate.",
            ),
            ExternalField(
                name="number_of_reinstatements", data_type="number", nullable=True,
                description="Number of reinstatements available",
                target_concept="fbo:hasReinstatementStatus",
                distortion=FieldDistortion.SEMANTIC_SHIFT,
                mapping_notes="0 → NotApplicable, >0 → Available. The count informs reinstatement configuration.",
            ),
            ExternalField(
                name="subject_perils", data_type="string", nullable=False,
                description="Covered perils as slash-separated codes",
                target_concept="fbo:hasPeril",
                distortion=FieldDistortion.CONCATENATE,
                mapping_notes="Slash-separated: 'NATCAT/FLOOD/QUAKE'. Reinsurance peril codes.",
            ),
            ExternalField(
                name="territory_of_risk", data_type="string", nullable=False,
                description="Geographic scope",
                target_concept="fbo:hasTerritory",
                distortion=FieldDistortion.LABEL_REFERENCE,
                mapping_notes="Free text or ISO-like codes",
            ),
        ]

        return ExternalSchema(
            schema_id=sid,
            schema_name="Reinsurance Treaty Slip Data",
            description="Structured data from a reinsurance slip/contract",
            source_system=self.rng.choice(["Sequel Impact", "ACORD", "RMS ReSolution"]),
            fields=fields,
            target_domain="placement",
            naming_convention=convention,
            structural_notes=[
                "Reinsurance-specific terminology throughout",
                "'Cedent' instead of 'Insured', 'Retention' instead of 'Attachment'",
                "Treaty type determines the entire structural mapping strategy",
                "Reinstatement count rather than status enum",
                "Reinsurer panel is an array of participants",
            ],
        )

    def _archetype_claims_feed(self) -> ExternalSchema:
        """Mimics a claims notification feed."""
        convention = "snake_case"
        sid = self._uid("SCH")

        fields = [
            ExternalField(
                name="claim_number", data_type="string", nullable=False,
                description="Unique claim identifier",
                target_concept="nsdp:ClaimEvent",
                distortion=FieldDistortion.DOMAIN_RENAME,
                mapping_notes="Claim ID",
            ),
            ExternalField(
                name="policy_ref", data_type="string", nullable=False,
                description="Associated policy reference",
                target_concept="nsdp:Placement",
                distortion=FieldDistortion.CODE_ENCODE,
                mapping_notes="Foreign key to placement",
            ),
            ExternalField(
                name="loss_amount_100pct", data_type="number", nullable=False,
                description="100% loss amount",
                target_concept="fbo:EventAmount",
                distortion=FieldDistortion.DOMAIN_RENAME,
                mapping_notes="Total loss amount. Our share is loss_amount_100pct × our_share_pct.",
            ),
            ExternalField(
                name="our_share_pct", data_type="number", nullable=False,
                description="Our participation percentage",
                target_concept="nsdp:signedLinePercentage",
                distortion=FieldDistortion.DOMAIN_RENAME,
                mapping_notes="Decimal percentage (0.15 = 15%)",
            ),
            ExternalField(
                name="date_of_loss", data_type="string", nullable=False,
                description="Date of loss occurrence (various formats)",
                target_concept="fbo:EventTime",
                distortion=FieldDistortion.DATE_VARIANT,
                mapping_notes="Date format varies: ISO, US, UK formats all appear",
            ),
            ExternalField(
                name="cause_of_loss", data_type="string", nullable=False,
                description="Cause/peril code or description",
                target_concept="fbo:hasPeril",
                distortion=FieldDistortion.LABEL_REFERENCE,
                mapping_notes="Mix of codes and free text. E.g., 'HURRICANE', 'Flood damage', 'Cyber - ransomware'",
            ),
            ExternalField(
                name="loss_location", data_type="string", nullable=True,
                description="Location of loss",
                target_concept="fbo:hasTerritory",
                distortion=FieldDistortion.LABEL_REFERENCE,
                mapping_notes="Free text: 'Miami, FL', 'London, UK', 'Multiple locations'",
            ),
            ExternalField(
                name="reserve_status", data_type="string", nullable=False,
                description="O (Open), C (Closed), R (Reopened)",
                target_concept="nsdp:claimStatus",
                distortion=FieldDistortion.CODE_ENCODE,
                mapping_notes="Single-character status code",
            ),
        ]

        return ExternalSchema(
            schema_id=sid,
            schema_name="Claims Notification Feed",
            description="Batch claims data from a TPA or insurer's claims system",
            source_system=self.rng.choice(["ClaimCenter", "FINEOS", "Custom TPA"]),
            fields=fields,
            target_domain="claim",
            naming_convention=convention,
            structural_notes=[
                "Claims data, not placement/tower data — different mapping target",
                "Loss amount at 100% requires multiplication by share",
                "Cause of loss is free text, not structured peril codes",
                "Date formats are inconsistent across records",
            ],
        )

    def _archetype_catastrophe_model_output(self) -> ExternalSchema:
        """Mimics catastrophe model output with analytics data."""
        convention = "camelCase"
        sid = self._uid("SCH")

        fields = [
            ExternalField(
                name="analysisId", data_type="string", nullable=False,
                description="Model run identifier",
                target_concept="nsdp:RiskAnalysis",
                distortion=FieldDistortion.DOMAIN_RENAME,
                mapping_notes="Analysis run ID",
            ),
            ExternalField(
                name="perilSet", data_type="json", nullable=False,
                description='[{"perilCode": str, "subPerilCode": str}]',
                target_concept="fbo:hasPeril",
                distortion=FieldDistortion.NESTED_BLOB,
                mapping_notes="Hierarchical peril structure with vendor-specific codes",
            ),
            ExternalField(
                name="eventTable", data_type="json", nullable=False,
                description='[{"eventId": int, "rate": number, "meanLoss": number, "stdDev": number, "maxLoss": number}]',
                target_concept="fbo:Event",
                distortion=FieldDistortion.NESTED_BLOB,
                mapping_notes="Stochastic event table. Maps to FBO scenario evaluation inputs.",
            ),
            ExternalField(
                name="exceedanceProbability", data_type="json", nullable=False,
                description='{"oep": {"10": number, "50": number, "100": number, "250": number, "500": number}, "aep": {"10": number, "50": number, "100": number, "250": number, "500": number}}',
                target_concept="nsdp:ExceedanceCurve",
                distortion=FieldDistortion.NESTED_BLOB,
                mapping_notes="OEP/AEP curves. Return period → loss amount. Maps to risk analytics, not directly to FBO tanks.",
            ),
            ExternalField(
                name="aal", data_type="number", nullable=False,
                description="Average Annual Loss",
                target_concept="nsdp:AAL",
                distortion=FieldDistortion.DOMAIN_RENAME,
                mapping_notes="Direct numeric value, maps to risk metric",
            ),
            ExternalField(
                name="modelVersion", data_type="string", nullable=False,
                description="Vendor model version identifier",
                target_concept="mork:provenanceVersion",
                distortion=FieldDistortion.DOMAIN_RENAME,
                mapping_notes="Provenance metadata for the analysis",
            ),
        ]

        return ExternalSchema(
            schema_id=sid,
            schema_name="Catastrophe Model Output",
            description="Results from a probabilistic catastrophe model run",
            source_system=self.rng.choice(["RMS RiskLink", "AIR Touchstone", "CoreLogic", "JBA FloodRe"]),
            fields=fields,
            target_domain="analysis",
            naming_convention=convention,
            structural_notes=[
                "Analytical data — not directly placement structure",
                "Uses vendor-specific peril codes, not industry standard",
                "Contains stochastic event tables (potentially thousands of events)",
                "Exceedance curves need interpretation for gap analysis",
                "Model version is critical provenance",
            ],
        )


# ═══════════════════════════════════════════════════════════════════
# SECTION 3: External Instance Data Generation
# ═══════════════════════════════════════════════════════════════════

class ExternalInstanceGenerator:
    """
    Generates instance data that conforms to external schemas.
    Uses the placement data as ground truth to ensure internal consistency.
    """

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.vocab = VocabularyPool()
        self._counter = 0

    def _uid(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter:04d}"

    def generate_instances(
        self,
        schema: ExternalSchema,
        placements: list[GeneratedPlacement],
        count: int,
    ) -> list[ExternalInstance]:
        """
        Generate instances conforming to the given external schema,
        sourcing ground truth from the generated placements.
        """
        instances = []
        for i in range(count):
            placement = self.rng.choice(placements)
            instance = self._generate_instance_from_placement(schema, placement)
            instances.append(instance)
        return instances

    def _generate_instance_from_placement(
        self,
        schema: ExternalSchema,
        placement: GeneratedPlacement,
    ) -> ExternalInstance:
        """Generate one external instance from a placement."""
        values = {}
        for field_def in schema.fields:
            values[field_def.name] = self._generate_field_value(field_def, placement)

        return ExternalInstance(
            instance_id=self._uid("INST"),
            schema_id=schema.schema_id,
            field_values=values,
            ground_truth_iris=[
                f"synth:{placement.placement_id}",
            ] + [
                f"synth:{t.tower_id}" for t in placement.towers
            ] + [
                f"synth:{l.layer_id}" for t in placement.towers for l in t.layers
            ],
        )

    def _generate_field_value(
        self,
        field_def: ExternalField,
        placement: GeneratedPlacement,
    ) -> Any:
        """Generate a value for a field based on its distortion type."""
        dist = field_def.distortion
        target = field_def.target_concept

        # ── Identifier fields ────────────────────────────
        if "Placement" in target and dist in (
            FieldDistortion.DOMAIN_RENAME, FieldDistortion.CODE_ENCODE
        ):
            if dist == FieldDistortion.CODE_ENCODE:
                return f"{self.rng.randint(100000, 999999)}"
            return f"SUB-{placement.placement_id}-{self.rng.randint(1000, 9999)}"

        # ── Name fields ──────────────────────────────────
        if "insuredName" in target or "cedent" in target.lower():
            if dist == FieldDistortion.CONCATENATE:
                # Sometimes includes broker in parens
                if self.rng.random() < 0.3:
                    return f"{placement.insured_name} ({placement.broker})"
                return placement.insured_name
            return placement.insured_name[:40]  # Truncated for legacy

        # ── Date fields ──────────────────────────────────
        if "inception" in target.lower() or "Date" in target:
            d = placement.inception
            if dist == FieldDistortion.DATE_VARIANT:
                formats = [
                    d.strftime("%d/%m/%Y"),      # DD/MM/YYYY
                    d.strftime("%Y%m%d"),          # YYYYMMDD
                    d.strftime("%m/%d/%Y"),         # MM/DD/YYYY (US)
                    d.strftime("%d-%b-%Y"),         # DD-Mon-YYYY
                ]
                return self.rng.choice(formats)
            if dist == FieldDistortion.CONCATENATE:
                # Combined inception/expiry
                return f"{d.strftime('%d/%m/%y')} - {placement.expiry.strftime('%d/%m/%y')}"
            return d.isoformat()

        if "expiry" in target.lower():
            d = placement.expiry
            if dist == FieldDistortion.DATE_VARIANT:
                formats = [
                    d.strftime("%d/%m/%Y"),
                    d.strftime("%Y%m%d"),
                ]
                return self.rng.choice(formats)
            return d.isoformat()

        # ── Capacity / limit fields ──────────────────────
        if "Capacity" in target or "limit" in target.lower():
            total_limit = sum(
                l.limit for t in placement.towers for l in t.layers
            )
            if dist == FieldDistortion.INLINE_UNIT:
                # "25M USD" or "25,000,000" or "25m"
                fmt = self.rng.choice(["compact", "full", "bare"])
                if fmt == "compact":
                    m = total_limit / Decimal("1000000")
                    return f"{m}M {placement.currency}"
                elif fmt == "full":
                    return f"{total_limit:,.0f}"
                else:
                    m = total_limit / Decimal("1000000")
                    return f"{m}m"
            if dist == FieldDistortion.CODE_ENCODE:
                # Cents, zero-padded to 12
                cents = int(total_limit * 100)
                return f"{cents:012d}"
            return float(total_limit)

        # ── Attachment / deductible fields ────────────────
        if "Attachment" in target or "deductible" in target.lower() or "retention" in target.lower():
            first_layer = placement.towers[0].layers[0] if placement.towers else None
            attachment = first_layer.attachment if first_layer else Decimal("0")
            if dist == FieldDistortion.CODE_ENCODE:
                cents = int(attachment * 100)
                return f"{cents:012d}"
            if dist == FieldDistortion.INLINE_UNIT:
                if attachment == 0:
                    return "nil"
                m = attachment / Decimal("1000000")
                return f"{m}m"
            return float(attachment)

        # ── Peril fields ─────────────────────────────────
        if "Peril" in target or "peril" in target.lower():
            perils = placement.programme.peril_scope
            if dist == FieldDistortion.CONCATENATE:
                sep = self.rng.choice([", ", ";", "/"])
                peril_names = [self._peril_to_external(p) for p in perils]
                return sep.join(peril_names)
            if dist == FieldDistortion.SPLIT:
                # Return just one peril for a single-peril field
                return self._peril_to_external_code(perils[0]) if perils else None
            if dist == FieldDistortion.LABEL_REFERENCE:
                return self._perils_to_freetext(perils)
            if dist == FieldDistortion.BOOLEAN_VARIANT:
                has_cyber = any("Cyber" in p for p in perils)
                return self.rng.choice(["Y", "Yes", "true", "1"]) if has_cyber else self.rng.choice(["N", "No", "false", "0"])
            if dist == FieldDistortion.NESTED_BLOB:
                return [{"perilCode": self._peril_to_external_code(p), "subPerilCode": None} for p in perils]
            return perils

        # ── Territory fields ─────────────────────────────
        if "Territory" in target or "territory" in target.lower():
            territories = placement.programme.territory_scope
            if dist == FieldDistortion.CONCATENATE:
                return "; ".join(territories)
            if dist == FieldDistortion.SPLIT:
                return json.dumps({
                    "primary": territories[0] if territories else "Worldwide",
                    "subnational": territories[1:] if len(territories) > 1 else [],
                    "worldwide": len(territories) == 0 or "Worldwide" in territories,
                })
            if dist == FieldDistortion.LABEL_REFERENCE:
                return self._territories_to_freetext(territories)
            if dist == FieldDistortion.CODE_ENCODE:
                return territories[0][:3].upper() if territories else "WLD"
            if dist == FieldDistortion.NESTED_BLOB:
                return [{"country": t, "region": None, "tiv": float(self.rng.randint(10_000_000, 500_000_000)), "percentage": round(100 / max(len(territories), 1), 1)} for t in territories]
            return territories

        # ── Line of business fields ──────────────────────
        if "LineOfBusiness" in target or "business" in target.lower():
            lob = placement.programme.line_of_business
            if dist == FieldDistortion.CODE_ENCODE:
                lob_codes = {"Property": "01", "Casualty": "02", "Marine": "03",
                             "Aviation": "04", "Energy": "05", "CyberInsurance": "06"}
                return lob_codes.get(lob, "99")
            if dist == FieldDistortion.LABEL_REFERENCE:
                # Human-friendly label, not the ontology term
                labels = {"CommercialProperty": "Commercial Property",
                          "GeneralLiability": "General Liability",
                          "CyberInsurance": "Cyber",
                          "DirectorsOfficers": "D&O"}
                return labels.get(lob, lob)
            return lob

        # ── Currency fields ──────────────────────────────
        if "currency" in target.lower():
            ccy = placement.currency
            if dist == FieldDistortion.LABEL_REFERENCE:
                symbols = {"USD": "$", "GBP": "£", "EUR": "€"}
                return self.rng.choice([ccy, symbols.get(ccy, ccy)])
            return ccy

        # ── Broker fields ────────────────────────────────
        if "broker" in target.lower():
            if dist == FieldDistortion.CODE_ENCODE:
                return f"BRK{self.rng.randint(100, 999)}"
            return placement.broker

        # ── Nested blobs ─────────────────────────────────
        if dist == FieldDistortion.NESTED_BLOB:
            # Generic nested blob for fields we haven't specifically handled
            if "InsuredParty" in target:
                return json.dumps({
                    "name": placement.insured_name,
                    "sic": f"{self.rng.randint(1000, 9999)}",
                    "revenue": float(self.rng.randint(10_000_000, 500_000_000)),
                    "domicile": self.rng.choice(["US", "UK", "DE", "JP"]),
                })
            if "Tower" in target or "Layer" in target or "Tank" in target:
                sections = []
                for tower in placement.towers:
                    for layer in tower.layers:
                        sections.append({
                            "sectionRef": f"S{self.rng.randint(1, 99):02d}",
                            "attachment": float(layer.attachment),
                            "limitOfLiability": float(layer.limit),
                            "basisOfSettlement": layer.basis.replace("Per", "Each "),
                            "reinstatements": self.rng.randint(0, 3),
                        })
                return json.dumps({"sections": sections})
            if "Participant" in target:
                return json.dumps([
                    {"name": p.name, "share_pct": float(p.share * 100), "signed_line": float(p.line_stamp)}
                    for p in placement.participants
                ])
            # Generic fallback
            return json.dumps({"data": "placeholder"})

        # ── Reinstatement fields ─────────────────────────
        if "Reinstatement" in target:
            if dist == FieldDistortion.BOOLEAN_VARIANT:
                return self.rng.choice(["Y", "N"])
            return self.rng.randint(0, 3)

        # ── Review status / marketing status ─────────────
        if "review" in target.lower() or "Status" in target:
            if dist == FieldDistortion.SEMANTIC_SHIFT:
                return self.rng.choice([True, False])
            statuses = ["PROSPECT", "SUBMITTED", "QUOTED", "BOUND", "DECLINED"]
            return self.rng.choice(statuses)

        # ── Percentage / share fields ────────────────────
        if "Percentage" in target or "share" in target.lower():
            share = float(self.rng.randint(5, 30))
            if dist == FieldDistortion.INLINE_UNIT:
                fmt = self.rng.choice(["pct", "decimal", "bare"])
                if fmt == "pct":
                    return f"{share}%"
                elif fmt == "decimal":
                    return f"{share / 100:.2f}"
                else:
                    return str(share)
            return share / 100

        # ── Everything else ──────────────────────────────
        if field_def.data_type == "string":
            return f"sample_{self.rng.randint(1000, 9999)}"
        if field_def.data_type == "number":
            return self.rng.randint(1, 1_000_000)
        if field_def.data_type == "boolean":
            return self.rng.choice([True, False])
        if field_def.data_type == "json":
            return json.dumps({"placeholder": True})
        return None

    # ── External representation helpers ──────────────────

    def _peril_to_external(self, peril: str) -> str:
        """Convert ontology peril name to external-looking name."""
        transforms = {
            "Hurricane": self.rng.choice(["Hurricane", "Windstorm - Named", "TC"]),
            "Flood": self.rng.choice(["Flood", "Water Damage", "Inundation"]),
            "Earthquake": self.rng.choice(["Earthquake", "Seismic", "EQ"]),
            "Wildfire": self.rng.choice(["Wildfire", "Bushfire", "Forest Fire"]),
            "CyberPeril": self.rng.choice(["Cyber", "Cyber Risk", "Information Security"]),
            "Ransomware": self.rng.choice(["Ransomware", "Extortion - Cyber", "Crypto Ransom"]),
            "DataBreach": self.rng.choice(["Data Breach", "Privacy Event", "PII Exposure"]),
            "NationStateAttack": self.rng.choice(["Nation-State Attack", "State-Sponsored Cyber", "APT"]),
            "Terrorism": self.rng.choice(["Terrorism", "Terror", "Political Violence - Terror"]),
            "Fire": self.rng.choice(["Fire", "Conflagration", "Fire & Lightning"]),
        }
        return transforms.get(peril, peril)

    def _peril_to_external_code(self, peril: str) -> str:
        codes = {
            "Hurricane": "HU", "Flood": "FL", "Earthquake": "EQ",
            "Wildfire": "WF", "CyberPeril": "CY", "Terrorism": "TE",
            "Fire": "FI", "Explosion": "EX", "Windstorm": "WS",
            "Ransomware": "RW", "DataBreach": "DB", "NationStateAttack": "NS",
        }
        return codes.get(peril, peril[:2].upper())

    def _perils_to_freetext(self, perils: list[str]) -> str:
        """Generate a realistic free-text peril description."""
        if not perils:
            return "All risks"
        named = [self._peril_to_external(p) for p in perils]
        if len(named) == 1:
            return named[0]
        return f"{', '.join(named[:-1])} and {named[-1]}"

    def _territories_to_freetext(self, territories: list[str]) -> str:
        if not territories:
            return "Worldwide"
        labels = {
            "US_FL": "Florida", "US_TX": "Texas", "US_CA": "California",
            "US_NY": "New York", "US_LA": "Louisiana",
            "US_GulfCoast": "US Gulf Coast", "US": "United States",
            "UK": "United Kingdom", "Germany": "Germany",
            "Japan": "Japan", "Australia": "Australia",
            "Worldwide": "Worldwide",
        }
        named = [labels.get(t, t) for t in territories]
        return ", ".join(named)


# ═══════════════════════════════════════════════════════════════════
# SECTION 4: SKOS Vocabulary Generation
# ═══════════════════════════════════════════════════════════════════

class SKOSVocabularyGenerator:
    """
    Generates the SKOS concept schemes that the Intent Agent
    and Mapping Agent query via Graph-RAG.
    """

    def __init__(self):
        self.graph = Graph()
        self.graph.bind("skos", SKOS)
        self.graph.bind("risk", RISK)
        self.graph.bind("geo", GEO)
        self.graph.bind("lob", LOB)
        self.graph.bind("fin", FIN)

    def generate_all_vocabularies(self) -> Graph:
        self._generate_peril_scheme()
        self._generate_territory_scheme()
        self._generate_lob_scheme()
        self._generate_coverage_type_scheme()
        return self.graph

    def _generate_peril_scheme(self):
        g = self.graph
        scheme = RISK["PerilScheme"]
        g.add((scheme, RDF.type, SKOS.ConceptScheme))
        g.add((scheme, SKOS.prefLabel, Literal("Peril Vocabulary")))

        for name, parent in VocabularyPool.PERILS:
            concept = RISK[name]
            g.add((concept, RDF.type, SKOS.Concept))
            g.add((concept, SKOS.inScheme, scheme))
            g.add((concept, SKOS.prefLabel, Literal(name)))
            if parent:
                g.add((concept, SKOS.broader, RISK[parent]))

    def _generate_territory_scheme(self):
        g = self.graph
        scheme = GEO["TerritoryScheme"]
        g.add((scheme, RDF.type, SKOS.ConceptScheme))
        g.add((scheme, SKOS.prefLabel, Literal("Territory Vocabulary")))

        for name, parent in VocabularyPool.TERRITORIES:
            concept = GEO[name]
            g.add((concept, RDF.type, SKOS.Concept))
            g.add((concept, SKOS.inScheme, scheme))
            g.add((concept, SKOS.prefLabel, Literal(name)))
            if parent:
                g.add((concept, SKOS.broader, GEO[parent]))

    def _generate_lob_scheme(self):
        g = self.graph
        scheme = LOB["LOBScheme"]
        g.add((scheme, RDF.type, SKOS.ConceptScheme))
        g.add((scheme, SKOS.prefLabel, Literal("Line of Business Vocabulary")))

        for name, parent in VocabularyPool.LINES_OF_BUSINESS:
            concept = LOB[name]
            g.add((concept, RDF.type, SKOS.Concept))
            g.add((concept, SKOS.inScheme, scheme))
            g.add((concept, SKOS.prefLabel, Literal(name)))
            if parent:
                g.add((concept, SKOS.broader, LOB[parent]))

    def _generate_coverage_type_scheme(self):
        g = self.graph
        scheme = FBO["CoverageTypeScheme"]
        g.add((scheme, RDF.type, SKOS.ConceptScheme))
        g.add((scheme, SKOS.prefLabel, Literal("Coverage Type Vocabulary")))

        for name in VocabularyPool.COVERAGE_TYPES:
            concept = FBO[name]
            g.add((concept, RDF.type, SKOS.Concept))
            g.add((concept, SKOS.inScheme, scheme))
            g.add((concept, SKOS.prefLabel, Literal(name)))


# ═══════════════════════════════════════════════════════════════════
# SECTION 5: Lookup Table Generation for External Schemas
# ═══════════════════════════════════════════════════════════════════

class LookupTableGenerator:
    """
    Generates the reference data lookup tables that external schemas
    require for code-to-IRI resolution. These are the tables that
    MORK's ReferenceDataLookup precedence rule (P9) would use.
    """

    @staticmethod
    def generate_all() -> dict[str, list[dict]]:
        return {
            "peril_codes": [
                {"code": "HU", "label": "Hurricane", "iri": "risk:Hurricane"},
                {"code": "FL", "label": "Flood", "iri": "risk:Flood"},
                {"code": "EQ", "label": "Earthquake", "iri": "risk:Earthquake"},
                {"code": "WF", "label": "Wildfire", "iri": "risk:Wildfire"},
                {"code": "WS", "label": "Windstorm", "iri": "risk:Windstorm"},
                {"code": "CY", "label": "Cyber", "iri": "risk:CyberPeril"},
                {"code": "RW", "label": "Ransomware", "iri": "risk:Ransomware"},
                {"code": "DB", "label": "Data Breach", "iri": "risk:DataBreach"},
                {"code": "NS", "label": "Nation-State Attack", "iri": "risk:NationStateAttack"},
                {"code": "TE", "label": "Terrorism", "iri": "risk:Terrorism"},
                {"code": "FI", "label": "Fire", "iri": "risk:Fire"},
                {"code": "EX", "label": "Explosion", "iri": "risk:Explosion"},
                {"code": "PV", "label": "Political Violence", "iri": "risk:PoliticalViolence"},
                {"code": "NATCAT", "label": "Natural Catastrophe", "iri": "risk:NaturalPeril"},
            ],
            "lob_codes": [
                {"code": "01", "label": "Property", "iri": "lob:Property"},
                {"code": "02", "label": "Casualty", "iri": "lob:Casualty"},
                {"code": "03", "label": "Marine", "iri": "lob:Marine"},
                {"code": "04", "label": "Aviation", "iri": "lob:Aviation"},
                {"code": "05", "label": "Energy", "iri": "lob:Energy"},
                {"code": "06", "label": "Cyber", "iri": "lob:CyberInsurance"},
                {"code": "07", "label": "Financial Lines", "iri": "lob:FinancialLines"},
                {"code": "08", "label": "Surety", "iri": "lob:Surety"},
                {"code": "99", "label": "Other", "iri": "lob:Other"},
            ],
            "territory_codes": [
                {"code": "USA", "label": "United States", "iri": "geo:US"},
                {"code": "GBR", "label": "United Kingdom", "iri": "geo:UK"},
                {"code": "DEU", "label": "Germany", "iri": "geo:Germany"},
                {"code": "FRA", "label": "France", "iri": "geo:France"},
                {"code": "JPN", "label": "Japan", "iri": "geo:Japan"},
                {"code": "AUS", "label": "Australia", "iri": "geo:Australia"},
                {"code": "CAN", "label": "Canada", "iri": "geo:Canada"},
                {"code": "WLD", "label": "Worldwide", "iri": "geo:Worldwide"},
                {"code": "FLR", "label": "Florida", "iri": "geo:US_FL"},
                {"code": "TEX", "label": "Texas", "iri": "geo:US_TX"},
                {"code": "CAL", "label": "California", "iri": "geo:US_CA"},
                {"code": "NYK", "label": "New York", "iri": "geo:US_NY"},
                {"code": "LAI", "label": "Louisiana", "iri": "geo:US_LA"},
            ],
            "broker_codes": [
                {"code": "BRK100", "label": "Marsh", "iri": "nsdp:Marsh"},
                {"code": "BRK200", "label": "Aon", "iri": "nsdp:Aon"},
                {"code": "BRK300", "label": "WTW", "iri": "nsdp:WTW"},
                {"code": "BRK400", "label": "Gallagher", "iri": "nsdp:Gallagher"},
                {"code": "BRK500", "label": "Lockton", "iri": "nsdp:Lockton"},
            ],
            "currency_symbols": [
                {"symbol": "$", "code": "USD"},
                {"symbol": "£", "code": "GBP"},
                {"symbol": "€", "code": "EUR"},
                {"symbol": "¥", "code": "JPY"},
            ],
        }


# ═══════════════════════════════════════════════════════════════════
# SECTION 6: Natural Language Input Generation
# ═══════════════════════════════════════════════════════════════════

class NaturalLanguageInputGenerator:
    """
    Generates realistic natural language specifications that would
    be fed into the MORK pipeline's Intent Agent (Stage 1).
    These exercise the full range of intent types: quantitative,
    spatial, temporal, inclusion, exclusion, conditional.
    """

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.vocab = VocabularyPool()

    def generate_specifications(self, placements: list[GeneratedPlacement], count: int) -> list[dict]:
        """Generate NL specifications based on placement data."""
        specs = []
        generators = [
            self._revenue_band_spec,
            self._territory_restriction_spec,
            self._peril_exclusion_spec,
            self._conditional_coverage_spec,
            self._aggregate_constraint_spec,
            self._parametric_trigger_spec,
            self._pool_participation_spec,
            self._surety_requirement_spec,
            self._compound_spec,
            self._ambiguous_spec,
        ]

        for _ in range(count):
            placement = self.rng.choice(placements)
            generator = self.rng.choice(generators)
            spec = generator(placement)
            specs.append(spec)
        return specs

    def _revenue_band_spec(self, placement: GeneratedPlacement) -> dict:
        low = self.rng.choice([1, 5, 10, 25, 50])
        high = self.rng.choice([x for x in [25, 50, 100, 250, 500] if x > low])
        return {
            "text": f"Revenue between ${low}M and ${high}M for {placement.programme.line_of_business} companies",
            "expected_intents": ["QuantitativeConstraint"],
            "expected_confidence": 0.95,
            "placement_context": placement.placement_id,
        }

    def _territory_restriction_spec(self, placement: GeneratedPlacement) -> dict:
        territories = placement.programme.territory_scope
        terr_text = ", ".join(territories[:2])
        return {
            "text": f"Coverage applies only to operations in {terr_text}",
            "expected_intents": ["SpatialScope"],
            "expected_confidence": 0.93,
            "placement_context": placement.placement_id,
        }

    def _peril_exclusion_spec(self, placement: GeneratedPlacement) -> dict:
        excluded = self.rng.choice(["war and terrorism", "nation-state cyber attacks",
                                     "nuclear events", "pandemic-related losses"])
        return {
            "text": f"Excluding {excluded} from all layers",
            "expected_intents": ["ExclusionIntent"],
            "expected_confidence": 0.91,
            "placement_context": placement.placement_id,
        }

    def _conditional_coverage_spec(self, placement: GeneratedPlacement) -> dict:
        condition = self.rng.choice([
            "If the insured operates in Florida",
            "For cyber-exposed risks",
            "When annual revenue exceeds $100M",
            "If the policy includes business interruption",
        ])
        consequence = self.rng.choice([
            "then a minimum deductible of $500K applies",
            "the aggregate limit must be at least $25M",
            "sub-limits apply as per the schedule",
            "a 72-hour waiting period is required",
        ])
        return {
            "text": f"{condition}, {consequence}",
            "expected_intents": ["CoverageIntent", "QuantitativeConstraint"],
            "expected_confidence": 0.88,
            "placement_context": placement.placement_id,
        }

    def _aggregate_constraint_spec(self, placement: GeneratedPlacement) -> dict:
        agg = self.rng.choice([50, 75, 100, 150, 200])
        return {
            "text": f"Annual aggregate limit of ${agg}M across all layers in the {placement.towers[0].tower_name if placement.towers else 'primary'} tower",
            "expected_intents": ["QuantitativeConstraint"],
            "expected_confidence": 0.94,
            "placement_context": placement.placement_id,
        }

    def _parametric_trigger_spec(self, placement: GeneratedPlacement) -> dict:
        index = self.rng.choice(["PCS industry loss index", "CAT-in-a-Box", "PERILS AG index"])
        threshold = self.rng.choice(["$5B", "$10B", "$15B", "$20B"])
        return {
            "text": f"Parametric trigger based on {index} exceeding {threshold} for named hurricanes in the Gulf Coast",
            "expected_intents": ["CoverageIntent", "QuantitativeConstraint", "SpatialScope"],
            "expected_confidence": 0.86,
            "placement_context": placement.placement_id,
        }

    def _pool_participation_spec(self, placement: GeneratedPlacement) -> dict:
        pool_name = self.rng.choice(["cyber mutual pool", "climate risk facility", "terrorism backstop pool"])
        share = self.rng.choice([5, 10, 15, 20])
        return {
            "text": f"Participation in the {pool_name} at {share}% share with exposure-weighted allocation",
            "expected_intents": ["CoverageIntent", "QuantitativeConstraint"],
            "expected_confidence": 0.85,
            "placement_context": placement.placement_id,
        }

    def _surety_requirement_spec(self, placement: GeneratedPlacement) -> dict:
        bond_type = self.rng.choice(["performance bond", "payment bond", "bid bond"])
        return {
            "text": f"Contractor {bond_type} with principal as the construction company and obligee as the project owner, limit $5M per project",
            "expected_intents": ["CoverageIntent", "QuantitativeConstraint"],
            "expected_confidence": 0.89,
            "placement_context": placement.placement_id,
        }

    def _compound_spec(self, placement: GeneratedPlacement) -> dict:
        return {
            "text": f"Revenue between $10M and $100M for technology companies in the US, excluding nation-state attacks, with a minimum deductible of $250K and an annual aggregate of $50M",
            "expected_intents": ["QuantitativeConstraint", "SpatialScope", "ExclusionIntent", "CoverageIntent"],
            "expected_confidence": 0.92,
            "placement_context": placement.placement_id,
        }

    def _ambiguous_spec(self, placement: GeneratedPlacement) -> dict:
        """Generate deliberately ambiguous specs that should trigger clarification."""
        ambiguous_texts = [
            "Reasonable limits for this type of risk",
            "Standard market terms apply",
            "Coverage as expiring but with improvements",
            "Competitive pricing with broad coverage",
            "Appropriate sub-limits for the exposure",
        ]
        return {
            "text": self.rng.choice(ambiguous_texts),
            "expected_intents": ["CoverageIntent"],
            "expected_confidence": 0.45,  # Low confidence → triggers clarification
            "should_trigger_clarification": True,
            "placement_context": placement.placement_id,
        }


# ═══════════════════════════════════════════════════════════════════
# SECTION 7: Dataset Assembly and Output
# ═══════════════════════════════════════════════════════════════════

@dataclass
class SyntheticDataset:
    """The complete generated dataset."""
    # Target-side data
    placements: list[GeneratedPlacement]
    cover_spans: list[GeneratedCoverSpan]
    vocabularies: Graph

    # Source-side data
    external_schemas: list[ExternalSchema]
    external_instances: dict[str, list[ExternalInstance]]  # schema_id → instances

    # Reference data
    lookup_tables: dict[str, list[dict]]

    # Pipeline test inputs
    nl_specifications: list[dict]

    # Metadata
    seed: int
    generation_timestamp: str

    def write_all(self, output_dir: str):
        """Write all generated data to the output directory."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # 1. Target-side RDF
        target_graph = Graph()
        target_graph.bind("fbo", FBO)
        target_graph.bind("nsdp", NSDP)
        target_graph.bind("synth", SYNTH)
        target_graph.bind("risk", RISK)
        target_graph.bind("geo", GEO)
        target_graph.bind("lob", LOB)

        for placement in self.placements:
            for s, p, o in placement.graph:
                target_graph.add((s, p, o))

        target_graph.serialize(str(out / "target_instances.ttl"), format="turtle")

        # 2. Vocabularies
        self.vocabularies.serialize(str(out / "vocabularies.ttl"), format="turtle")

        # 3. External schemas
        schemas_dir = out / "external_schemas"
        schemas_dir.mkdir(exist_ok=True)

        for schema in self.external_schemas:
            schema_data = {
                "schema_id": schema.schema_id,
                "schema_name": schema.schema_name,
                "description": schema.description,
                "source_system": schema.source_system,
                "target_domain": schema.target_domain,
                "naming_convention": schema.naming_convention,
                "structural_notes": schema.structural_notes,
                "fields": [
                    {
                        "name": f.name,
                        "data_type": f.data_type,
                        "nullable": f.nullable,
                        "description": f.description,
                        "target_concept": f.target_concept,
                        "distortion": f.distortion.value,
                        "mapping_notes": f.mapping_notes,
                    }
                    for f in schema.fields
                ],
            }
            with open(schemas_dir / f"{schema.schema_id}.json", "w") as fh:
                json.dump(schema_data, fh, indent=2)

        # 4. External instances
        instances_dir = out / "external_instances"
        instances_dir.mkdir(exist_ok=True)

        for schema_id, instances in self.external_instances.items():
            instance_records = [
                {
                    "instance_id": inst.instance_id,
                    "schema_id": inst.schema_id,
                    "values": inst.field_values,
                    "ground_truth_iris": inst.ground_truth_iris,
                }
                for inst in instances
            ]
            with open(instances_dir / f"{schema_id}_instances.json", "w") as fh:
                json.dump(instance_records, fh, indent=2, default=str)

        # 5. Lookup tables
        with open(out / "lookup_tables.json", "w") as fh:
            json.dump(self.lookup_tables, fh, indent=2)

        # 6. NL specifications
        with open(out / "nl_specifications.json", "w") as fh:
            json.dump(self.nl_specifications, fh, indent=2)

        # 7. Manifest
        manifest = {
            "seed": self.seed,
            "generation_timestamp": self.generation_timestamp,
            "counts": {
                "placements": len(self.placements),
                "towers": sum(len(p.towers) for p in self.placements),
                "layers": sum(len(l.layers) for p in self.placements for l in p.towers),
                "tanks": sum(
                    len(l.layers) for p in self.placements for l in p.towers
                ),
                "flows": sum(
                    len(f.flows)
                    for p in self.placements
                    for t in p.towers
                    for f in t.layers
                ),
                "cover_spans": len(self.cover_spans),
                "external_schemas": len(self.external_schemas),
                "external_instances": sum(
                    len(v) for v in self.external_instances.values()
                ),
                "nl_specifications": len(self.nl_specifications),
            },
            "schema_archetypes": [s.schema_name for s in self.external_schemas],
            "distortion_types_used": list(set(
                f.distortion.value
                for s in self.external_schemas
                for f in s.fields
            )),
        }
        with open(out / "manifest.json", "w") as fh:
            json.dump(manifest, fh, indent=2)

        # 8. Summary report (human-readable)
        self._write_summary(out / "SUMMARY.md")

    def _write_summary(self, path: Path):
        """Write a human-readable summary of the generated dataset."""
        lines = [
            "# Synthetic Dataset Summary",
            "",
            f"**Seed:** {self.seed}",
            f"**Generated:** {self.generation_timestamp}",
            "",
            "## Target-Side Data (FBO/NSDP)",
            "",
            f"- **Placements:** {len(self.placements)}",
        ]

        for p in self.placements:
            lines.append(f"  - {p.placement_id}: {p.insured_name} ({p.programme.line_of_business})")
            for t in p.towers:
                lines.append(f"    - {t.tower_name}: {len(t.layers)} layers")
                for l in t.layers:
                    lines.append(f"      - {l.tank.tank_type} ${l.limit:,.0f} xs ${l.attachment:,.0f}")

        lines.extend([
            "",
            "## External Schemas",
            "",
        ])

        for s in self.external_schemas:
            lines.append(f"### {s.schema_name} ({s.schema_id})")
            lines.append(f"- Source: {s.source_system}")
            lines.append(f"- Domain: {s.target_domain}")
            lines.append(f"- Fields: {len(s.fields)}")
            lines.append(f"- Naming: {s.naming_convention}")
            lines.append(f"- Distortions: {', '.join(set(f.distortion.value for f in s.fields))}")
            lines.append(f"- Instances: {len(self.external_instances.get(s.schema_id, []))}")
            lines.append("")
            for note in s.structural_notes:
                lines.append(f"  > {note}")
            lines.append("")

        lines.extend([
            "## NL Specifications",
            "",
            f"- **Total:** {len(self.nl_specifications)}",
            f"- **Ambiguous (should trigger clarification):** "
            f"{sum(1 for s in self.nl_specifications if s.get('should_trigger_clarification'))}",
            "",
        ])

        with open(path, "w") as fh:
            fh.write("\n".join(lines))


# ═══════════════════════════════════════════════════════════════════
# SECTION 8: Main Generator
# ═══════════════════════════════════════════════════════════════════

class MorkSyntheticDataGenerator:
    """
    Top-level generator that orchestrates all sub-generators
    and produces a complete, internally consistent dataset.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)

    def generate_full_dataset(
        self,
        num_placements: int = 10,
        num_external_schemas: int = 5,
        instances_per_schema: int = 20,
        num_nl_specs: int = 30,
    ) -> SyntheticDataset:
        """Generate the complete synthetic dataset."""

        # 1. Generate target-side FBO data
        fbo_gen = FBOTargetGenerator(self.rng)
        placements = [fbo_gen.generate_placement() for _ in range(num_placements)]

        # 2. Materialise cover spans
        all_spans = []
        for placement in placements:
            spans = fbo_gen.generate_cover_spans(placement)
            all_spans.extend(spans)

        # 3. Generate SKOS vocabularies
        vocab_gen = SKOSVocabularyGenerator()
        vocabularies = vocab_gen.generate_all_vocabularies()

        # 4. Generate external schemas
        schema_gen = ExternalSchemaGenerator(self.rng)
        external_schemas = [schema_gen.generate_schema() for _ in range(num_external_schemas)]

        # 5. Generate external instances
        instance_gen = ExternalInstanceGenerator(self.rng)
        external_instances = {}
        for schema in external_schemas:
            instances = instance_gen.generate_instances(
                schema, placements, instances_per_schema
            )
            external_instances[schema.schema_id] = instances

        # 6. Generate lookup tables
        lookup_tables = LookupTableGenerator.generate_all()

        # 7. Generate NL specifications
        nl_gen = NaturalLanguageInputGenerator(self.rng)
        nl_specs = nl_gen.generate_specifications(placements, num_nl_specs)

        return SyntheticDataset(
            placements=placements,
            cover_spans=all_spans,
            vocabularies=vocabularies,
            external_schemas=external_schemas,
            external_instances=external_instances,
            lookup_tables=lookup_tables,
            nl_specifications=nl_specs,
            seed=self.seed,
            generation_timestamp=datetime.utcnow().isoformat(),
        )


# ═══════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="MORK Synthetic Data Generator"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--placements", type=int, default=10, help="Number of placements")
    parser.add_argument("--schemas", type=int, default=5, help="Number of external schemas")
    parser.add_argument("--instances", type=int, default=20, help="Instances per schema")
    parser.add_argument("--nl-specs", type=int, default=30, help="NL specifications")
    parser.add_argument("--output", type=str, default="./synthetic_data", help="Output directory")
    args = parser.parse_args()

    print(f"Generating synthetic dataset (seed={args.seed})...")
    generator = MorkSyntheticDataGenerator(seed=args.seed)
    dataset = generator.generate_full_dataset(
        num_placements=args.placements,
        num_external_schemas=args.schemas,
        instances_per_schema=args.instances,
        num_nl_specs=args.nl_specs,
    )

    print(f"Writing to {args.output}/...")
    dataset.write_all(args.output)

    print(f"Done. Manifest at {args.output}/manifest.json")
    print(f"Summary at {args.output}/SUMMARY.md")


if __name__ == "__main__":
    main()
