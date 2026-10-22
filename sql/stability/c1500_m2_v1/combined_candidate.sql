-- Read-only C1500 candidate, sourced exclusively from pinned historical M2 and
-- N750 version-0 outputs. Each source row retains its complete original schema
-- as JSON plus its source, run and technical locator. M2 projection rows remain
-- a separate occurrence class and are never counted as new physical sources.
WITH combined AS (
  SELECT 'OLD_C750_RECORD' AS occurrence_class, o.source_instance_id,
         o.run_id, o.binding_sha256 AS binding_ref,
         concat_ws(':', o.binding_sha256, cast(o.source_line AS STRING),
                   cast(o.byte_offset AS STRING)) AS locator,
         to_json(struct(o.*), map('ignoreNullFields', 'false')) AS payload
  FROM workspace.edp_lab.o_c750_m2_records_historical_20261022_v1 o
  UNION ALL
  SELECT 'NEW_N750_SEC_RECORD', n.source_instance_id, n.run_id,
         n.raw_sha256,
         concat_ws(':', n.source_instance_id, cast(n.source_line AS STRING),
                   cast(n.byte_offset AS STRING)),
         to_json(struct(n.*), map('ignoreNullFields', 'false'))
  FROM workspace.edp_lab.clean_n750_m1_sec_records_step8_v1 VERSION AS OF 0 n
  UNION ALL
  SELECT 'NEW_N750_XML_PROPERTY', x.source_instance_id, x.run_id,
         x.raw_sha256,
         concat_ws(':', x.source_instance_id, cast(x.entry_ordinal AS STRING),
                   cast(x.property_ordinal AS STRING)),
         to_json(struct(x.*), map('ignoreNullFields', 'false'))
  FROM workspace.edp_lab.clean_n750_m1_treasury_properties_step8_v1 VERSION AS OF 0 x
  UNION ALL
  SELECT 'NEW_N750_M2_EVALUATION', m.source_instance_id, m.run_id,
         m.raw_sha256,
         concat_ws(':', m.source_instance_id, cast(m.entry_ordinal AS STRING),
                   m.property_qname),
         to_json(struct(m.*), map('ignoreNullFields', 'false'))
  FROM workspace.edp_lab.clean_n750_m2_treasury_rates_step8_v1 VERSION AS OF 0 m
)
SELECT occurrence_class, count(*) AS occurrences,
       count(DISTINCT source_instance_id) AS physical_sources,
       count_if(payload IS NULL OR locator IS NULL OR run_id IS NULL
                OR binding_ref IS NULL) AS incomplete_envelopes
FROM combined GROUP BY occurrence_class ORDER BY occurrence_class;
