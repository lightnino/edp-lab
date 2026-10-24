-- Planned, unexecuted migration. Replace {{SCHEMA}} only after protected
-- controlled-write authorization and isolated namespace permission are verified.
-- No DROP, REPLACE, overwrite or write to source/frozen tables is permitted.
CREATE SCHEMA IF NOT EXISTS {{SCHEMA}};

CREATE TABLE IF NOT EXISTS {{SCHEMA}}.h_filing (
  filing_hk STRING NOT NULL, source_namespace STRING NOT NULL, adsh STRING NOT NULL,
  first_load_dts TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{SCHEMA}}.h_concept (
  concept_hk STRING NOT NULL, source_namespace STRING NOT NULL, tag STRING NOT NULL,
  version STRING NOT NULL, first_load_dts TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{SCHEMA}}.l_fact_slot (
  fact_slot_hk STRING NOT NULL, filing_hk STRING NOT NULL, concept_hk STRING NOT NULL,
  context_json STRING NOT NULL, first_load_dts TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{SCHEMA}}.r_source_occurrence (
  occurrence_hk STRING NOT NULL, source_instance_id STRING NOT NULL,
  archive_member STRING NOT NULL, member_sha256 STRING NOT NULL,
  byte_offset BIGINT NOT NULL, byte_length BIGINT NOT NULL,
  source_line BIGINT NOT NULL, raw_path STRING NOT NULL, raw_sha256 STRING NOT NULL,
  binding_sha256 STRING NOT NULL, m1_run_id STRING NOT NULL,
  record_kind STRING NOT NULL, fields_json STRING NOT NULL,
  first_load_dts TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{SCHEMA}}.s_fact_assertion (
  assertion_hk STRING NOT NULL, fact_slot_hk STRING NOT NULL,
  occurrence_hk STRING NOT NULL, parser_contract_version STRING NOT NULL,
  parser_profile_id STRING NOT NULL, m1_model_version STRING NOT NULL,
  m1_rule_version STRING NOT NULL, payload_hashdiff STRING NOT NULL,
  value_lexical STRING NOT NULL, footnote_lexical STRING NOT NULL,
  first_load_dts TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{SCHEMA}}.s_num_m2_value (
  occurrence_hk STRING NOT NULL, field_ordinal INT NOT NULL,
  source_rule_version STRING NOT NULL, model_version STRING NOT NULL,
  conversion_rule_version STRING NOT NULL, lexical_value STRING NOT NULL,
  value_decimal DECIMAL(38,4), conversion_outcome STRING NOT NULL,
  conversion_reason STRING NOT NULL, first_load_dts TIMESTAMP NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{SCHEMA}}.r_load_event (
  occurrence_hk STRING NOT NULL, execution_id STRING NOT NULL,
  load_dts TIMESTAMP NOT NULL, event_kind STRING NOT NULL,
  statement_id STRING, input_manifest_sha256 STRING NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS {{SCHEMA}}.vault_reject_quarantine (
  input_identity STRING NOT NULL, execution_id STRING NOT NULL,
  rejected_dts TIMESTAMP NOT NULL, reason_code STRING NOT NULL,
  reason_detail STRING NOT NULL, source_instance_id STRING,
  archive_member STRING, member_sha256 STRING, byte_offset BIGINT,
  byte_length BIGINT, source_line BIGINT, raw_sha256 STRING,
  binding_sha256 STRING, input_json STRING NOT NULL,
  synthetic_negative_control BOOLEAN NOT NULL
) USING DELTA;
