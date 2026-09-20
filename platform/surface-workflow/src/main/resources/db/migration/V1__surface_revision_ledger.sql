-- SPDX-License-Identifier: MPL-2.0

create table surface_revision_ledger (
    revision_id varchar(255) primary key,
    contract_id varchar(255) not null,
    tenant_id varchar(255) not null,
    project_id varchar(255) not null,
    state varchar(32) not null,
    contract_graph_iri text not null,
    contract_graph_hash varchar(71) not null,
    profile_graph_iri text not null,
    profile_graph_hash varchar(71) not null,
    generated_graph_iri text,
    generated_graph_hash varchar(71),
    approval_id varchar(255),
    revision_version bigint not null,
    recorded_at timestamptz not null default current_timestamp,
    check (revision_version >= 0),
    check ((generated_graph_iri is null) = (generated_graph_hash is null))
);

create index surface_revision_ledger_contract_idx on surface_revision_ledger (contract_id);
create index surface_revision_ledger_scope_idx on surface_revision_ledger (tenant_id, project_id);
