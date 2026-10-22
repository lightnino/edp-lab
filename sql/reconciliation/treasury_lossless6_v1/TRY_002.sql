-- TRY_002_V1: compare persisted M2 with independent source M1 text via exact SQL DECIMAL cast.
WITH p AS (
 SELECT * FROM workspace.edp_lab.clean_n750_m1_treasury_properties_step8_v1 VERSION AS OF 0
), m AS (
 SELECT * FROM workspace.edp_lab.clean_n750_m2_treasury_rates_step8_v1 VERSION AS OF 0
 WHERE present=true
), joined AS (
 SELECT m.*, p.source_instance_id AS matched_source, p.property_qname AS original_qname,
        p.lexical_value AS original_text, p.raw_sha256 AS original_raw_sha,
        p.span_sha256 AS original_span_sha, p.byte_offset AS original_byte_offset,
        p.byte_length AS original_byte_length, p.attributes_json AS original_attributes,
        p.null_marker AS original_null_marker, p.model_version AS original_model,
        p.rule_version AS original_rule,
        try_cast(p.lexical_value AS DECIMAL(38,4)) AS independently_cast_value,
        count(p.source_instance_id) OVER
         (PARTITION BY m.source_instance_id,m.entry_ordinal,m.property_ordinal) AS join_matches
 FROM m LEFT JOIN p ON m.source_instance_id=p.source_instance_id
  AND m.entry_ordinal=p.entry_ordinal AND m.property_ordinal=p.property_ordinal
)
SELECT 'TRY_002_V1' AS control_id, count(*) AS actual_present,
  12793 AS expected_present,
  count_if(join_matches <> 1) AS join_violations,
  count_if(conversion_outcome <> 'VALID' OR conversion_reason <> 'EXACT_PROJECTION'
    OR value_decimal IS NULL) AS outcome_violations,
  count_if(original_text IS NULL OR NOT original_text RLIKE '^[+-]?[0-9]+(\\.[0-9]{1,4})?$'
    OR independently_cast_value IS NULL OR value_decimal <> independently_cast_value) AS numeric_violations,
  count_if(NOT (property_qname <=> original_qname) OR NOT (lexical_value <=> original_text)
    OR NOT (raw_sha256 <=> original_raw_sha) OR NOT (span_sha256 <=> original_span_sha)
    OR NOT (byte_offset <=> original_byte_offset) OR NOT (byte_length <=> original_byte_length)
    OR NOT (attributes_json <=> original_attributes) OR NOT (null_marker <=> original_null_marker)
    OR NOT (model_version <=> original_model) OR NOT (rule_version <=> original_rule))
    AS lineage_violations,
  count_if(model_version <> 'M1_LEXICAL_V1' OR m2_model_version <> 'M2_ADDITIVE_TYPED_NUMERIC_V1'
    OR conversion_rule_version <> 'EXACT_DECIMAL_38_4_V1'
    OR source_rule_version <> 'TREASURY_RATE_QNAME_SCOPE_V1') AS version_violations
FROM joined;
