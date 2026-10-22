-- TRY_004_V1: targeted live noninterference; runner also validates immutable FIN,
-- witness and eight-direction combined SQL receipts before assigning PASS.
{{FIN_CANDIDATE_PREFIX}}
SELECT 'TRY_004_V1' AS control_id,
  count_if(source_instance_id BETWEEN 'SRC010451' AND 'SRC010455') AS treasury_fin_rows,
  count_if(source_instance_id BETWEEN 'SRC010451' AND 'SRC010455'
    AND record_kind='DATA') AS treasury_data_rows,
  count_if(source_instance_id BETWEEN 'SRC010451' AND 'SRC010455'
    AND fields IS NOT NULL) AS treasury_fsds_field_rows,
  count_if(source_instance_id BETWEEN 'SRC010451' AND 'SRC010455'
    AND value_decimal IS NOT NULL) AS treasury_typed_rows,
  count(DISTINCT CASE WHEN source_instance_id BETWEEN 'SRC010451' AND 'SRC010455'
    THEN source_instance_id END) AS treasury_sources
FROM combined_fin;
