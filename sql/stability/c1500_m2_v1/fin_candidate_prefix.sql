-- Read-only FIN projection of the C1500 candidate. The entire historical M2
-- record schema remains in the pinned historical relation; this FIN projection
-- contains only columns used by the existing, unchanged FIN_001/002 SQL.
WITH combined_fin AS (
  SELECT source_instance_id, binding_sha256, run_id, record_kind,
         admission_outcome, fields, value_decimal
  FROM workspace.edp_lab.o_c750_m2_records_historical_20261022_v1
  UNION ALL
  SELECT source_instance_id, raw_sha256, run_id, record_kind,
         'ACCEPTED',
         CAST(NULL AS ARRAY<STRUCT<field_ordinal:INT,original_name:STRING,
              lexical_value:STRING,disposition:STRING>>),
         CAST(NULL AS DECIMAL(38,4))
  FROM workspace.edp_lab.clean_n750_m1_sec_records_step8_v1 VERSION AS OF 0
  UNION ALL
  SELECT source_instance_id, raw_sha256, run_id, 'XML_PROPERTY',
         'ACCEPTED',
         CAST(NULL AS ARRAY<STRUCT<field_ordinal:INT,original_name:STRING,
              lexical_value:STRING,disposition:STRING>>),
         CAST(NULL AS DECIMAL(38,4))
  FROM workspace.edp_lab.clean_n750_m1_treasury_properties_step8_v1 VERSION AS OF 0
  UNION ALL
  SELECT source_instance_id, raw_sha256, run_id, 'M2_EVALUATION',
         'ACCEPTED',
         CAST(NULL AS ARRAY<STRUCT<field_ordinal:INT,original_name:STRING,
              lexical_value:STRING,disposition:STRING>>),
         value_decimal
  FROM workspace.edp_lab.clean_n750_m2_treasury_rates_step8_v1 VERSION AS OF 0
),
