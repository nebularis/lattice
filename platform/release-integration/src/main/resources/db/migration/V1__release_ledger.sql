-- SPDX-License-Identifier: MPL-2.0

create table release_ledger_intent (
    release_id varchar(255) primary key,
    correlation_id varchar(255) not null,
    intent_json jsonb not null,
    recorded_at timestamptz not null default current_timestamp
);

create table release_ledger_receipt (
    release_id varchar(255) primary key references release_ledger_intent (release_id),
    correlation_id varchar(255) not null,
    receipt_json jsonb not null,
    recorded_at timestamptz not null default current_timestamp
);

create table release_ledger_event (
    event_id bigserial primary key,
    release_id varchar(255) not null references release_ledger_intent (release_id),
    kind varchar(64) not null,
    correlation_id varchar(255) not null,
    recorded_at timestamptz not null,
    evidence_reference text not null
);

create index release_ledger_event_release_idx on release_ledger_event (release_id, recorded_at, event_id);