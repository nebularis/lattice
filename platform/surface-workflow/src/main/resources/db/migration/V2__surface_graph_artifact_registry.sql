-- SPDX-License-Identifier: MPL-2.0

create table surface_graph_artifact (
    tenant_id varchar(255) not null,
    project_id varchar(255) not null,
    graph_iri text not null,
    graph_hash varchar(71) not null,
    family varchar(32) not null,
    owner_revision_id varchar(255) not null,
    registered_at timestamptz not null,
    primary key (tenant_id, project_id, graph_iri)
);

create index surface_graph_artifact_owner_idx on surface_graph_artifact (owner_revision_id, family);