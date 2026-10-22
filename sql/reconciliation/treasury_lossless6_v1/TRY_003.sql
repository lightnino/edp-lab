-- TRY_003_V1: structural absence and multiplicity, including present-empty controls.
WITH p AS (
 SELECT * FROM workspace.edp_lab.clean_n750_m1_treasury_properties_step8_v1 VERSION AS OF 0
), m AS (
 SELECT * FROM workspace.edp_lab.clean_n750_m2_treasury_rates_step8_v1 VERSION AS OF 0
), selected AS (
 SELECT m.*, count(p.source_instance_id) OVER
  (PARTITION BY m.source_instance_id,m.entry_ordinal,m.property_qname,m.property_ordinal) AS join_matches
 FROM m LEFT JOIN p ON m.source_instance_id=p.source_instance_id
  AND m.entry_ordinal=p.entry_ordinal AND m.property_ordinal=p.property_ordinal
  AND m.property_qname=p.property_qname
), missing AS (
 SELECT m.*, EXISTS(SELECT 1 FROM p WHERE p.source_instance_id=m.source_instance_id
   AND p.entry_ordinal=m.entry_ordinal AND p.property_qname=m.property_qname) AS source_has_qname
 FROM m WHERE present=false
), duplicates AS (
 SELECT source_instance_id,entry_ordinal,property_qname,count(*) n FROM m
 GROUP BY source_instance_id,entry_ordinal,property_qname HAVING count(*) <> 1
), missing_by_source AS (
 SELECT source_instance_id, count(*) n FROM missing GROUP BY source_instance_id
)
SELECT 'TRY_003_V1' AS control_id, count(*) AS actual_evaluations,
  12948 AS expected_evaluations,
  count_if(present) AS actual_present, 12793 AS expected_present,
  count_if(NOT present) AS actual_missing, 155 AS expected_missing,
  count_if(NOT present AND (conversion_outcome <> 'MISSING'
    OR conversion_reason <> 'SOURCE_FIELD_ABSENT' OR value_decimal IS NOT NULL
    OR lexical_value IS NOT NULL OR property_ordinal IS NOT NULL
    OR byte_offset IS NOT NULL OR byte_length IS NOT NULL OR span_sha256 IS NOT NULL))
    AS invalid_missing,
  (SELECT count(*) FROM missing WHERE source_has_qname) AS false_absences,
  count_if(present AND join_matches <> 1) AS present_join_violations,
  (SELECT count(*) FROM duplicates) AS duplicate_keys,
  (SELECT count(*) FROM p WHERE lexical_value=''
    AND property_qname='{http://schemas.microsoft.com/ado/2007/08/dataservices}BOND_MKT_UNAVAIL_REASON')
    AS present_empty_context,
  (SELECT count(*) FROM missing_by_source WHERE
    (source_instance_id='SRC010451' AND n<>31)
    OR (source_instance_id='SRC010452' AND n<>124)
    OR source_instance_id NOT IN ('SRC010451','SRC010452')) AS missing_source_violations
FROM selected;
