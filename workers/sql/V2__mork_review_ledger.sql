-- SPDX-License-Identifier: MPL-2.0

create table mork_review_snapshot (
    snapshot_id varchar(255) primary key,
    tenant_id varchar(255) not null,
    project_id varchar(255) not null,
    mapping_graph_iri text not null,
    mapping_graph_hash varchar(71) not null,
    snapshot_hash varchar(71) not null,
    section_id varchar(255) not null,
    snapshot_version bigint not null,
    evidence_json jsonb not null,
    recorded_at timestamptz not null default current_timestamp,
    unique (tenant_id, project_id, snapshot_id, snapshot_version)
);

create table mork_review_decision (
    decision_id bigserial primary key,
    snapshot_id varchar(255) not null references mork_review_snapshot (snapshot_id),
    snapshot_hash varchar(71) not null,
    decision varchar(32) not null,
    rationale text not null,
    reviewer_role varchar(64) not null,
    recorded_at timestamptz not null default current_timestamp
);

create index mork_review_snapshot_scope_idx on mork_review_snapshot (tenant_id, project_id, snapshot_id);
create index mork_review_decision_snapshot_idx on mork_review_decision (snapshot_id, recorded_at);