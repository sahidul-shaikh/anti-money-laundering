-- =====================================================================
--  AML Alert Investigator — Physical Database Schema
--  Document ID : AMLI-DDL-001
--  Version     : 0.1  (Draft)
--  Owner       : Data Architect
--  Target      : PostgreSQL 16 / Amazon Aurora PostgreSQL-Compatible
--  Date        : 18 November 2026
--
--  Scope: the thirteen core entities of ADR-018 plus the spine tables
--  required to make them useful (model_call, run_evidence, security_event,
--  policy_version, detection_version, audit_event).
--
--  Conventions
--    * UUID v7 surrogate keys, time-ordered for index locality.
--    * All timestamps timestamptz, stored UTC. Business dates are `date`.
--    * Money is numeric(18,2) with an explicit currency column. Never float.
--    * Every customer-bearing table carries institution_id + jurisdiction_code
--      and is protected by row-level security (section 9).
--    * Append-only tables grant INSERT only to the application role.
--    * Monthly range partitioning on high-volume time-series tables.
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS amli;
SET search_path = amli, public;

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- digest() for the audit hash chain
CREATE EXTENSION IF NOT EXISTS btree_gist; -- exclusion constraints on validity ranges
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- trigram index on party.legal_name

-- ---------------------------------------------------------------------
-- 1. Enumerations
-- ---------------------------------------------------------------------

CREATE TYPE party_type          AS ENUM ('individual', 'organisation');
CREATE TYPE txn_direction       AS ENUM ('credit', 'debit');
CREATE TYPE alert_status        AS ENUM ('ingested', 'ready_for_investigation',
                                         'investigating', 'awaiting_review',
                                         'decided', 'quarantined', 'manual_queue');
CREATE TYPE alert_outcome       AS ENUM ('closed_no_action', 'escalated_to_case',
                                         'sar_filed', 'ctr_filed', 'still_open');
CREATE TYPE disposition         AS ENUM ('close_no_further_action',
                                         'escalate_to_case',
                                         'insufficient_information');
CREATE TYPE label_value         AS ENUM ('escalate', 'close');
CREATE TYPE label_basis         AS ENUM ('adjudicated_qa', 'adjudicated_dual',
                                         'filing_inferred', 'synthetic');
CREATE TYPE case_status         AS ENUM ('open', 'investigating', 'pending_review',
                                         'closed', 'referred');
CREATE TYPE actor_kind          AS ENUM ('human', 'system');
CREATE TYPE decision_outcome    AS ENUM ('accept_recommendation', 'override_close',
                                         'override_escalate', 'request_information',
                                         'approve_report');
CREATE TYPE evidence_stance     AS ENUM ('supports', 'contradicts');
CREATE TYPE run_status          AS ENUM ('running', 'completed', 'failed',
                                         'aborted_budget', 'aborted_control');
CREATE TYPE call_status         AS ENUM ('ok', 'provider_error', 'timeout',
                                         'blocked', 'unparseable');
CREATE TYPE control_outcome     AS ENUM ('allow', 'block', 'escalate');
CREATE TYPE security_severity   AS ENUM ('info', 'low', 'medium', 'high', 'critical');

-- ---------------------------------------------------------------------
-- 2. Reference and supporting entities
-- ---------------------------------------------------------------------

CREATE TABLE institution (
    institution_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code                text NOT NULL UNIQUE,
    name                text NOT NULL,
    jurisdiction_code   char(2) NOT NULL,
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE source_system (
    source_system_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    code                text NOT NULL,          -- 'ACTIMIZE_SAM', 'KYC_MASTER'
    description         text,
    UNIQUE (institution_id, code)
);

CREATE TABLE actor (
    actor_id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    kind                actor_kind NOT NULL,
    external_identity   text NOT NULL,          -- IdP subject, or service principal
    display_name        text NOT NULL,
    created_at          timestamptz NOT NULL DEFAULT now(),
    disabled_at         timestamptz,
    UNIQUE (institution_id, external_identity)
);
COMMENT ON TABLE actor IS
  'Every decision has an actor. A system actor is identified, never anonymous.';

CREATE TABLE policy_version (
    policy_version_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    policy_type         text NOT NULL,          -- 'guardrail','investigation','retention'
    jurisdiction_code   char(2) NOT NULL,
    version             text NOT NULL,
    content_hash        char(64) NOT NULL,
    effective_from      timestamptz NOT NULL,
    effective_to        timestamptz,
    approved_by         uuid REFERENCES actor,
    CONSTRAINT policy_period_valid CHECK (effective_to IS NULL
                                          OR effective_to > effective_from),
    UNIQUE (institution_id, policy_type, jurisdiction_code, version)
);

CREATE TABLE detection_version (
    detection_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    scenario_code       text NOT NULL,          -- 'SAS10014'
    detection_model     text NOT NULL,          -- 'AML-STR'
    rule_id             text,                   -- 'AML-STR-CCE-INN-A-D01-DST'
    rule_version        text NOT NULL,
    source_document     text NOT NULL,
    source_page         integer,
    thresholds          jsonb NOT NULL,
    effective_from      date NOT NULL,
    effective_to        date,
    CONSTRAINT detection_period_valid CHECK (effective_to IS NULL
                                             OR effective_to > effective_from),
    UNIQUE (institution_id, scenario_code, rule_version)
);
COMMENT ON COLUMN detection_version.source_page IS
  'Page in source_document from which the thresholds were extracted (ADR-007).';

CREATE TABLE retention_policy (
    retention_policy_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    entity_name         text NOT NULL,
    retain_years        integer NOT NULL CHECK (retain_years > 0),
    UNIQUE (institution_id, entity_name)
);

CREATE TABLE legal_hold (
    legal_hold_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    case_id             uuid,                   -- FK added after case is created
    reason              text NOT NULL,
    placed_by           uuid NOT NULL REFERENCES actor,
    placed_at           timestamptz NOT NULL DEFAULT now(),
    released_at         timestamptz
);

-- ---------------------------------------------------------------------
-- 3. Domain A — financial crime context
-- ---------------------------------------------------------------------

CREATE TABLE party (
    party_id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    jurisdiction_code   char(2) NOT NULL,
    source_system_id    uuid NOT NULL REFERENCES source_system,
    external_reference  text NOT NULL,
    party_type          party_type NOT NULL,
    legal_name          text NOT NULL,
    date_of_birth       date,
    occupation          text,
    annual_income       numeric(18,2),
    income_currency     char(3),
    customer_indicator  boolean NOT NULL DEFAULT true,
    city                text,
    state_code          text,
    country_code        char(2),
    valid_from          timestamptz NOT NULL DEFAULT now(),
    valid_to            timestamptz,
    ingested_at         timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT party_income_currency CHECK (
        (annual_income IS NULL) = (income_currency IS NULL)),
    CONSTRAINT party_validity CHECK (valid_to IS NULL OR valid_to > valid_from)
);
CREATE UNIQUE INDEX party_current_key
    ON party (institution_id, source_system_id, external_reference)
    WHERE valid_to IS NULL;
CREATE INDEX party_name_trgm ON party USING gin (legal_name gin_trgm_ops);

CREATE TABLE account (
    account_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    jurisdiction_code   char(2) NOT NULL,
    source_system_id    uuid NOT NULL REFERENCES source_system,
    external_reference  text NOT NULL,
    account_type        text,
    product_name        text,
    currency            char(3),
    status              text,
    registration_type   text,
    opened_date         date,
    is_internal         boolean NOT NULL DEFAULT true,
    valid_from          timestamptz NOT NULL DEFAULT now(),
    valid_to            timestamptz,
    CONSTRAINT account_validity CHECK (valid_to IS NULL OR valid_to > valid_from)
);
CREATE UNIQUE INDEX account_current_key
    ON account (institution_id, source_system_id, external_reference)
    WHERE valid_to IS NULL;

CREATE TABLE party_account_role (
    party_id            uuid NOT NULL REFERENCES party,
    account_id          uuid NOT NULL REFERENCES account,
    role_type           text NOT NULL,          -- 'holder','signatory','beneficial_owner'
    valid_from          timestamptz NOT NULL,
    valid_to            timestamptz,
    PRIMARY KEY (party_id, account_id, role_type, valid_from),
    CONSTRAINT par_validity CHECK (valid_to IS NULL OR valid_to > valid_from)
);

-- Partitioned: ~105M rows per year at reference volume.
CREATE TABLE transaction (
    transaction_id      uuid NOT NULL DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    jurisdiction_code   char(2) NOT NULL,
    source_system_id    uuid NOT NULL REFERENCES source_system,
    external_reference  text NOT NULL,
    account_id          uuid NOT NULL REFERENCES account,
    event_date          date NOT NULL,
    booked_at           timestamptz NOT NULL,
    amount              numeric(18,2) NOT NULL,
    currency            char(3) NOT NULL,
    direction           txn_direction NOT NULL,
    medium              text,
    country_code        char(2),
    -- Written by whoever sent the payment. The one attacker-controlled field
    -- in the record (ADR-006). Preserved byte-identical; never sanitised.
    reference_text      text,
    reference_text_untrusted boolean NOT NULL DEFAULT true,
    ingested_at         timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (transaction_id, booked_at),
    CONSTRAINT txn_amount_positive CHECK (amount >= 0),
    CONSTRAINT txn_untrusted_flag CHECK (
        reference_text IS NULL OR reference_text_untrusted = true)
) PARTITION BY RANGE (booked_at);

CREATE UNIQUE INDEX transaction_source_key
    ON transaction (institution_id, source_system_id, external_reference, booked_at);
CREATE INDEX transaction_account_date
    ON transaction (account_id, event_date DESC);

-- ---------------------------------------------------------------------
-- 4. Domain B — alerts, cases, evidence, findings, decisions
-- ---------------------------------------------------------------------

CREATE TABLE alert (
    alert_id            uuid NOT NULL DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    jurisdiction_code   char(2) NOT NULL,
    source_system_id    uuid NOT NULL REFERENCES source_system,
    external_reference  text NOT NULL,
    detection_version_id uuid REFERENCES detection_version,
    scenario_code       text NOT NULL,
    description         text,
    triggered_values    text,          -- ACTUAL_VALUES_TEXT from the detection engine
    run_date            date NOT NULL,
    raised_at           timestamptz NOT NULL,
    priority            integer,
    score               numeric(6,3),
    status              alert_status NOT NULL DEFAULT 'ingested',

    -- Labelling. These five are NEVER rendered to a model (FR-033, ADR-010).
    outcome             alert_outcome,
    adjudication        label_value,
    adjudicated_by      uuid REFERENCES actor,
    adjudicated_at      timestamptz,
    label               label_value,
    label_basis         label_basis,
    label_confidence    numeric(3,2),

    ingested_at         timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (alert_id, raised_at),

    -- A label must carry its basis and confidence, or not exist at all.
    CONSTRAINT alert_label_complete CHECK (
        (label IS NULL AND label_basis IS NULL AND label_confidence IS NULL)
        OR (label IS NOT NULL AND label_basis IS NOT NULL
            AND label_confidence IS NOT NULL
            AND label_confidence BETWEEN 0 AND 1)),

    -- A CTR filing is a threshold obligation, not evidence of suspicion.
    -- It may never, by itself, produce a positive label (AMLI-DM-001 section 6).
    CONSTRAINT alert_ctr_never_labels CHECK (
        NOT (outcome = 'ctr_filed' AND label = 'escalate'
             AND label_basis = 'filing_inferred')),

    CONSTRAINT alert_adjudication_complete CHECK (
        (adjudication IS NULL) = (adjudicated_by IS NULL))
) PARTITION BY RANGE (raised_at);

CREATE UNIQUE INDEX alert_source_key
    ON alert (institution_id, source_system_id, external_reference, raised_at);
CREATE INDEX alert_status_queue ON alert (institution_id, status, raised_at);
CREATE INDEX alert_labelled ON alert (institution_id, label)
    WHERE label IS NOT NULL;

CREATE TABLE alert_party (
    alert_id            uuid NOT NULL,
    alert_raised_at     timestamptz NOT NULL,
    party_id            uuid NOT NULL REFERENCES party,
    subject_role        text NOT NULL DEFAULT 'subject',
    PRIMARY KEY (alert_id, alert_raised_at, party_id),
    FOREIGN KEY (alert_id, alert_raised_at) REFERENCES alert (alert_id, raised_at)
);

CREATE TABLE alert_transaction (
    alert_id            uuid NOT NULL,
    alert_raised_at     timestamptz NOT NULL,
    transaction_id      uuid NOT NULL,
    transaction_booked_at timestamptz NOT NULL,
    relevance_type      text NOT NULL DEFAULT 'triggering',
    PRIMARY KEY (alert_id, alert_raised_at, transaction_id, transaction_booked_at),
    FOREIGN KEY (alert_id, alert_raised_at) REFERENCES alert (alert_id, raised_at),
    FOREIGN KEY (transaction_id, transaction_booked_at)
        REFERENCES transaction (transaction_id, booked_at)
);

CREATE TABLE "case" (
    case_id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    jurisdiction_code   char(2) NOT NULL,
    external_reference  text,                  -- ActOne case id when known
    case_type           text NOT NULL,
    status              case_status NOT NULL DEFAULT 'open',
    owner_actor_id      uuid REFERENCES actor,
    opened_at           timestamptz NOT NULL DEFAULT now(),
    due_at              timestamptz,
    closed_at           timestamptz,
    CONSTRAINT case_closed_consistency CHECK (
        (status = 'closed') = (closed_at IS NOT NULL))
);
CREATE INDEX case_owner_status ON "case" (owner_actor_id, status);

ALTER TABLE legal_hold
    ADD CONSTRAINT legal_hold_case_fk FOREIGN KEY (case_id) REFERENCES "case";

-- Alerts and cases are many-to-many, and the link history is kept.
CREATE TABLE case_alert (
    case_id             uuid NOT NULL REFERENCES "case",
    alert_id            uuid NOT NULL,
    alert_raised_at     timestamptz NOT NULL,
    linked_at           timestamptz NOT NULL DEFAULT now(),
    linked_by           uuid NOT NULL REFERENCES actor,
    unlinked_at         timestamptz,
    unlinked_by         uuid REFERENCES actor,
    reason              text NOT NULL,
    PRIMARY KEY (case_id, alert_id, alert_raised_at, linked_at),
    FOREIGN KEY (alert_id, alert_raised_at) REFERENCES alert (alert_id, raised_at),
    CONSTRAINT case_alert_unlink_consistency CHECK (
        (unlinked_at IS NULL) = (unlinked_by IS NULL))
);
COMMENT ON TABLE case_alert IS
  'Consolidation history. An alert may be linked, unlinked and relinked; every
   transition records actor and reason (FR-055).';

CREATE TABLE case_party (
    case_id             uuid NOT NULL REFERENCES "case",
    party_id            uuid NOT NULL REFERENCES party,
    subject_role        text NOT NULL DEFAULT 'subject',
    PRIMARY KEY (case_id, party_id)
);

-- Evidence: what was available at investigation time. A live reference is
-- not evidence (ADR-011).
CREATE TABLE evidence_item (
    evidence_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    jurisdiction_code   char(2) NOT NULL,
    source_reference    text NOT NULL,
    source_system_id    uuid REFERENCES source_system,
    captured_at         timestamptz NOT NULL,
    content_hash        char(64) NOT NULL,
    storage_uri         text NOT NULL,
    media_type          text NOT NULL,
    byte_size           bigint NOT NULL CHECK (byte_size > 0),
    classification      text NOT NULL,          -- C1..C5 per AMLI-DFD-001
    contains_pii        boolean NOT NULL,
    superseded_by       uuid REFERENCES evidence_item,
    CONSTRAINT evidence_hash_format CHECK (content_hash ~ '^[0-9a-f]{64}$')
);
CREATE UNIQUE INDEX evidence_content_key
    ON evidence_item (institution_id, content_hash, source_reference);

CREATE TABLE case_evidence (
    case_id             uuid NOT NULL REFERENCES "case",
    evidence_id         uuid NOT NULL REFERENCES evidence_item,
    relevance           text,
    added_by            uuid NOT NULL REFERENCES actor,
    added_at            timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (case_id, evidence_id)
);

-- ---------------------------------------------------------------------
-- 5. Domain C — the AI spine
-- ---------------------------------------------------------------------

CREATE TABLE ai_run (
    run_id              uuid NOT NULL DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    jurisdiction_code   char(2) NOT NULL,
    deployment_id       uuid,                   -- FK added in Phase 3
    case_id             uuid REFERENCES "case",
    alert_id            uuid,
    alert_raised_at     timestamptz,
    trace_id            text NOT NULL,
    rule_catalogue_version text NOT NULL,
    agent_config_hash   char(64) NOT NULL,
    status              run_status NOT NULL DEFAULT 'running',
    termination_reason  text,
    started_at          timestamptz NOT NULL DEFAULT now(),
    ended_at            timestamptz,
    cost_usd            numeric(12,6) NOT NULL DEFAULT 0,
    escalations         smallint NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, started_at),
    FOREIGN KEY (alert_id, alert_raised_at) REFERENCES alert (alert_id, raised_at),
    CONSTRAINT run_ended_consistency CHECK (
        (status = 'running') = (ended_at IS NULL)),
    CONSTRAINT run_has_subject CHECK (alert_id IS NOT NULL OR case_id IS NOT NULL)
) PARTITION BY RANGE (started_at);

CREATE INDEX ai_run_trace ON ai_run (trace_id);
CREATE INDEX ai_run_alert ON ai_run (alert_id, alert_raised_at);
CREATE INDEX ai_run_case  ON ai_run (case_id);
COMMENT ON TABLE ai_run IS
  'The integration point (ADR-008). Every model call, control check, evidence
   access, finding and piece of feedback joins here.';

CREATE TABLE model_call (
    call_id             uuid NOT NULL DEFAULT gen_random_uuid(),
    run_id              uuid NOT NULL,
    run_started_at      timestamptz NOT NULL,
    called_at           timestamptz NOT NULL DEFAULT now(),
    attempt             smallint NOT NULL,
    tier                text NOT NULL,
    provider            text NOT NULL,
    model_identifier    text NOT NULL,
    system_prompt_hash  char(64) NOT NULL,
    user_prompt_hash    char(64) NOT NULL,
    prompt_storage_uri  text NOT NULL,   -- the captured prompt, retained as evidence
    tokens_in           integer NOT NULL DEFAULT 0,
    tokens_out          integer NOT NULL DEFAULT 0,
    tokens_cached       integer NOT NULL DEFAULT 0,
    cost_usd            numeric(12,6) NOT NULL DEFAULT 0,
    latency_ms          integer NOT NULL DEFAULT 0,
    status              call_status NOT NULL,
    error_detail        text,
    PRIMARY KEY (call_id, called_at),
    FOREIGN KEY (run_id, run_started_at) REFERENCES ai_run (run_id, started_at),
    CONSTRAINT model_call_tokens_nonneg CHECK (
        tokens_in >= 0 AND tokens_out >= 0 AND tokens_cached >= 0)
) PARTITION BY RANGE (called_at);
CREATE INDEX model_call_run ON model_call (run_id, run_started_at);

CREATE TABLE run_evidence (
    run_id              uuid NOT NULL,
    run_started_at      timestamptz NOT NULL,
    evidence_id         uuid NOT NULL REFERENCES evidence_item,
    accessed_at         timestamptz NOT NULL DEFAULT now(),
    access_purpose      text NOT NULL,
    PRIMARY KEY (run_id, run_started_at, evidence_id, accessed_at),
    FOREIGN KEY (run_id, run_started_at) REFERENCES ai_run (run_id, started_at)
);

CREATE TABLE control_check (
    check_id            uuid NOT NULL DEFAULT gen_random_uuid(),
    run_id              uuid NOT NULL,
    run_started_at      timestamptz NOT NULL,
    policy_version_id   uuid NOT NULL REFERENCES policy_version,
    control_name        text NOT NULL,
    phase               text NOT NULL,          -- 'pre_call' | 'post_call' | 'pre_tool'
    outcome             control_outcome NOT NULL,
    action              text,
    detail              jsonb,
    evaluated_at        timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (check_id, evaluated_at),
    FOREIGN KEY (run_id, run_started_at) REFERENCES ai_run (run_id, started_at)
) PARTITION BY RANGE (evaluated_at);
CREATE INDEX control_check_run ON control_check (run_id, run_started_at);

CREATE TABLE security_event (
    security_event_id   uuid NOT NULL DEFAULT gen_random_uuid(),
    run_id              uuid,
    run_started_at      timestamptz,
    institution_id      uuid NOT NULL REFERENCES institution,
    threat_type         text NOT NULL,          -- 'prompt_injection','exfiltration',...
    severity            security_severity NOT NULL,
    detected_at         timestamptz NOT NULL DEFAULT now(),
    detector            text NOT NULL,
    resolution          text,
    detail              jsonb,
    PRIMARY KEY (security_event_id, detected_at),
    FOREIGN KEY (run_id, run_started_at) REFERENCES ai_run (run_id, started_at)
) PARTITION BY RANGE (detected_at);

-- ---------------------------------------------------------------------
-- 6. Findings, recommendations and decisions
-- ---------------------------------------------------------------------

CREATE TABLE recommendation (
    recommendation_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id              uuid NOT NULL,
    run_started_at      timestamptz NOT NULL,
    alert_id            uuid,
    alert_raised_at     timestamptz,
    case_id             uuid REFERENCES "case",
    disposition         disposition NOT NULL,
    reasoning           text NOT NULL,
    confidence          numeric(3,2) CHECK (confidence BETWEEN 0 AND 1),
    groundedness        numeric(3,2) NOT NULL CHECK (groundedness BETWEEN 0 AND 1),
    cited_count         integer NOT NULL DEFAULT 0,
    invented_count      integer NOT NULL DEFAULT 0,
    created_at          timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (run_id, run_started_at) REFERENCES ai_run (run_id, started_at),
    FOREIGN KEY (alert_id, alert_raised_at) REFERENCES alert (alert_id, raised_at)
);
COMMENT ON TABLE recommendation IS
  'What the agent proposes. Never what the institution decided — see decision.';

CREATE TABLE finding (
    finding_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    case_id             uuid REFERENCES "case",
    run_id              uuid,
    run_started_at      timestamptz,
    authored_by         uuid REFERENCES actor,   -- null when agent-authored
    statement           text NOT NULL,
    confidence          numeric(3,2) CHECK (confidence BETWEEN 0 AND 1),
    grounded            boolean NOT NULL,
    review_status       text NOT NULL DEFAULT 'draft',
    created_at          timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (run_id, run_started_at) REFERENCES ai_run (run_id, started_at),
    CONSTRAINT finding_has_author CHECK (authored_by IS NOT NULL OR run_id IS NOT NULL)
);

CREATE TABLE finding_evidence (
    finding_id          uuid NOT NULL REFERENCES finding ON DELETE CASCADE,
    evidence_id         uuid NOT NULL REFERENCES evidence_item,
    citation            text NOT NULL,          -- the transaction reference cited
    stance              evidence_stance NOT NULL,
    resolved            boolean NOT NULL,       -- did the citation resolve?
    PRIMARY KEY (finding_id, evidence_id, citation)
);
COMMENT ON COLUMN finding_evidence.stance IS
  'supports | contradicts. A finding may cite evidence that weighs against it.';

-- A finalised, evidence-dependent finding must have at least one resolved
-- supporting citation. Drafts may not. Enforced by trigger (section 8).

CREATE TABLE decision (
    decision_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    case_id             uuid REFERENCES "case",
    alert_id            uuid,
    alert_raised_at     timestamptz,
    recommendation_id   uuid REFERENCES recommendation,
    actor_id            uuid NOT NULL REFERENCES actor,
    outcome             decision_outcome NOT NULL,
    rationale           text NOT NULL,
    override_reason_code text,
    agreed_with_recommendation boolean,
    supersedes          uuid REFERENCES decision,
    decided_at          timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (alert_id, alert_raised_at) REFERENCES alert (alert_id, raised_at),
    CONSTRAINT decision_override_reason CHECK (
        outcome NOT IN ('override_close','override_escalate')
        OR override_reason_code IS NOT NULL),
    CONSTRAINT decision_no_self_supersede CHECK (supersedes <> decision_id)
);
CREATE INDEX decision_case ON decision (case_id, decided_at DESC);
CREATE INDEX decision_actor ON decision (actor_id, decided_at DESC);

-- The actor on a decision must be human for any disposition-bearing outcome.
-- This is the database-level expression of BR-003.
CREATE OR REPLACE FUNCTION assert_human_decision() RETURNS trigger AS $$
DECLARE k actor_kind;
BEGIN
    SELECT kind INTO k FROM actor WHERE actor_id = NEW.actor_id;
    IF k <> 'human' AND NEW.outcome <> 'request_information' THEN
        RAISE EXCEPTION
          'BR-003: a disposition decision requires a human actor (actor % is %)',
          NEW.actor_id, k;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER decision_requires_human
    BEFORE INSERT OR UPDATE ON decision
    FOR EACH ROW EXECUTE FUNCTION assert_human_decision();

-- ---------------------------------------------------------------------
-- 7. Append-only audit
-- ---------------------------------------------------------------------

CREATE TABLE audit_event (
    audit_event_id      uuid NOT NULL DEFAULT gen_random_uuid(),
    institution_id      uuid NOT NULL REFERENCES institution,
    occurred_at         timestamptz NOT NULL DEFAULT now(),
    actor_id            uuid REFERENCES actor,
    run_id              uuid,
    entity_name         text NOT NULL,
    entity_id           uuid,
    action              text NOT NULL,
    before_value        jsonb,
    after_value         jsonb,
    trace_id            text,
    prev_hash           char(64),
    row_hash            char(64) NOT NULL,
    PRIMARY KEY (audit_event_id, occurred_at)
) PARTITION BY RANGE (occurred_at);
CREATE INDEX audit_event_entity ON audit_event (entity_name, entity_id, occurred_at);
COMMENT ON TABLE audit_event IS
  'Append-only, hash-chained. The application role holds INSERT only; UPDATE and
   DELETE are revoked (section 9). Chain verified daily (NFR-030).';

-- ---------------------------------------------------------------------
-- 8. Integrity triggers
-- ---------------------------------------------------------------------

-- A finalised finding that depends on evidence needs a resolved supporting
-- citation. Drafts may lack one (AMLI-DM-001 section 4, "finding rule").
CREATE OR REPLACE FUNCTION assert_finalised_finding_cited() RETURNS trigger AS $$
BEGIN
    IF NEW.review_status = 'final' THEN
        IF NOT EXISTS (SELECT 1 FROM finding_evidence fe
                       WHERE fe.finding_id = NEW.finding_id
                         AND fe.stance = 'supports'
                         AND fe.resolved) THEN
            RAISE EXCEPTION
              'FR-050: a final finding requires at least one resolved supporting citation';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER finding_final_requires_citation
    BEFORE UPDATE ON finding
    FOR EACH ROW WHEN (NEW.review_status = 'final')
    EXECUTE FUNCTION assert_finalised_finding_cited();

-- Hash-chain each audit row to its predecessor within the institution.
CREATE OR REPLACE FUNCTION chain_audit_event() RETURNS trigger AS $$
DECLARE prev char(64);
BEGIN
    SELECT row_hash INTO prev FROM audit_event
     WHERE institution_id = NEW.institution_id
     ORDER BY occurred_at DESC, audit_event_id DESC LIMIT 1;
    NEW.prev_hash := prev;
    NEW.row_hash := encode(digest(
        coalesce(prev,'') || NEW.entity_name || coalesce(NEW.entity_id::text,'')
        || NEW.action || coalesce(NEW.after_value::text,'')
        || NEW.occurred_at::text, 'sha256'), 'hex');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_event_chain
    BEFORE INSERT ON audit_event
    FOR EACH ROW EXECUTE FUNCTION chain_audit_event();

-- ---------------------------------------------------------------------
-- 9. Row-level security — jurisdiction isolation (ADR-014)
-- ---------------------------------------------------------------------

CREATE ROLE amli_app   NOLOGIN;
CREATE ROLE amli_read  NOLOGIN;
CREATE ROLE amli_audit NOLOGIN;

-- Session context is set once on connection acquisition and cannot be
-- opted out of by application code.
CREATE OR REPLACE FUNCTION current_institution() RETURNS uuid AS $$
  SELECT nullif(current_setting('amli.institution_id', true), '')::uuid;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION current_jurisdictions() RETURNS text[] AS $$
  SELECT string_to_array(
           coalesce(nullif(current_setting('amli.jurisdictions', true), ''), ''), ',');
$$ LANGUAGE sql STABLE;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['party','account','transaction','alert','case',
                           'evidence_item','ai_run','finding','decision',
                           'security_event','audit_event']
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format($f$
      CREATE POLICY %1$I_tenant ON %1$I
        USING (institution_id = current_institution())
        WITH CHECK (institution_id = current_institution())$f$, t);
  END LOOP;
END $$;

-- Jurisdiction narrowing on the customer-bearing tables.
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['party','account','transaction','alert','case',
                           'evidence_item','ai_run']
  LOOP
    EXECUTE format($f$
      CREATE POLICY %1$I_jurisdiction ON %1$I
        USING (jurisdiction_code = ANY (current_jurisdictions()))$f$, t);
  END LOOP;
END $$;

-- Order matters. The broad grant is applied first; the append-only tables are
-- then narrowed. Reversing these two blocks would silently re-grant UPDATE on
-- audit_event and make the tamper-evidence claim false.
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA amli TO amli_app;
REVOKE DELETE ON ALL TABLES IN SCHEMA amli FROM amli_app;
GRANT SELECT ON ALL TABLES IN SCHEMA amli TO amli_read;

-- Append-only tables: INSERT only for the application (NFR-030).
REVOKE UPDATE, DELETE, TRUNCATE ON audit_event      FROM amli_app;
REVOKE UPDATE, DELETE, TRUNCATE ON model_call       FROM amli_app;
REVOKE UPDATE, DELETE, TRUNCATE ON control_check    FROM amli_app;
REVOKE UPDATE, DELETE, TRUNCATE ON security_event   FROM amli_app;
REVOKE UPDATE, DELETE, TRUNCATE ON decision         FROM amli_app;
REVOKE UPDATE, DELETE, TRUNCATE ON evidence_item    FROM amli_app;
GRANT SELECT ON audit_event TO amli_audit;

-- Default privileges for partitions created later by the maintenance job.
ALTER DEFAULT PRIVILEGES IN SCHEMA amli
    GRANT SELECT, INSERT ON TABLES TO amli_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA amli
    GRANT SELECT ON TABLES TO amli_read;

-- ---------------------------------------------------------------------
-- 10. Partition management
-- ---------------------------------------------------------------------
-- Monthly range partitions, created three months ahead by a scheduled job and
-- dropped only after the retention check and the legal-hold interlock pass
-- (FR-027). Example for one month:

CREATE TABLE transaction_2026_11 PARTITION OF transaction
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE alert_2026_11 PARTITION OF alert
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE ai_run_2026_11 PARTITION OF ai_run
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE model_call_2026_11 PARTITION OF model_call
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE control_check_2026_11 PARTITION OF control_check
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE security_event_2026_11 PARTITION OF security_event
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE audit_event_2026_11 PARTITION OF audit_event
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');

-- ---------------------------------------------------------------------
-- 11. Read model for the reviewer workspace (NFR-004)
-- ---------------------------------------------------------------------

CREATE MATERIALIZED VIEW mv_review_queue AS
SELECT a.institution_id,
       a.jurisdiction_code,
       a.alert_id,
       a.raised_at,
       a.scenario_code,
       p.legal_name,
       p.occupation,
       r.recommendation_id,
       r.disposition,
       r.confidence,
       r.groundedness,
       run.cost_usd,
       run.ended_at AS investigated_at
  FROM alert a
  JOIN ai_run run ON run.alert_id = a.alert_id AND run.alert_raised_at = a.raised_at
  JOIN recommendation r ON r.run_id = run.run_id AND r.run_started_at = run.started_at
  LEFT JOIN alert_party ap ON ap.alert_id = a.alert_id AND ap.alert_raised_at = a.raised_at
  LEFT JOIN party p ON p.party_id = ap.party_id AND p.valid_to IS NULL
 WHERE a.status = 'awaiting_review'
   AND run.status = 'completed';

CREATE UNIQUE INDEX mv_review_queue_key
    ON mv_review_queue (alert_id, raised_at);

-- =====================================================================
-- End of AMLI-DDL-001 v0.1
-- =====================================================================
