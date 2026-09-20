-- SPDX-License-Identifier: MPL-2.0

create table processed_surface_job (
    job_id varchar(255) primary key,
    request_digest varchar(71) not null,
    result_json jsonb not null,
    processed_at timestamptz not null default current_timestamp
);
