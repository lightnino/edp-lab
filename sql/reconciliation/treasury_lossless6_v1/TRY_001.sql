-- TRY_001_V1. Runner expands fixture VALUES from the separately pinned fixture.
WITH pins(source_instance_id, source_identity, raw_sha256, expected_entries,
          expected_evaluations, expected_valid, expected_missing) AS (
  VALUES {{PINS}}
), allowed(source_instance_id, property_qname) AS (
  VALUES {{ALLOWLIST}}
),
m1 AS (
  SELECT p.* FROM workspace.edp_lab.clean_n750_m1_treasury_properties_step8_v1 VERSION AS OF 0 p
  WHERE p.source_instance_id IN (SELECT source_instance_id FROM pins)
), m2 AS (
  SELECT m.* FROM workspace.edp_lab.clean_n750_m2_treasury_rates_step8_v1 VERSION AS OF 0 m
), entries AS (
  SELECT DISTINCT source_instance_id, entry_ordinal FROM m1
), required AS (
  SELECT e.source_instance_id, e.entry_ordinal, a.property_qname
  FROM entries e JOIN allowed a ON e.source_instance_id = a.source_instance_id
), actual AS (
  SELECT source_instance_id, entry_ordinal, property_qname, count(*) AS n
  FROM m2 GROUP BY source_instance_id, entry_ordinal, property_qname
), coverage AS (
  SELECT coalesce(r.source_instance_id, a.source_instance_id) AS sid,
         count_if(r.source_instance_id IS NULL OR a.source_instance_id IS NULL OR a.n <> 1) AS violations
  FROM required r FULL OUTER JOIN actual a
    ON r.source_instance_id = a.source_instance_id AND r.entry_ordinal = a.entry_ordinal
   AND r.property_qname = a.property_qname
  GROUP BY coalesce(r.source_instance_id, a.source_instance_id)
), m1_pin AS (
  SELECT p.source_instance_id, count_if(p.source_identity <> s.source_identity
          OR p.raw_sha256 <> s.raw_sha256) AS violations
  FROM m1 p JOIN pins s ON p.source_instance_id=s.source_instance_id
  GROUP BY p.source_instance_id
), m2_pin AS (
  SELECT m.source_instance_id, count_if(m.source_identity <> s.source_identity
          OR m.raw_sha256 <> s.raw_sha256) AS violations
  FROM m2 m JOIN pins s ON m.source_instance_id=s.source_instance_id
  GROUP BY m.source_instance_id
), observed AS (
  SELECT source_instance_id, count(*) AS evaluations,
         count_if(conversion_outcome='VALID') AS valid,
         count_if(conversion_outcome='MISSING') AS missing
  FROM m2 GROUP BY source_instance_id
), entry_counts AS (
  SELECT source_instance_id, count(*) AS entries FROM entries GROUP BY source_instance_id
), qname_counts AS (
  SELECT source_instance_id, count(*) AS qnames FROM allowed GROUP BY source_instance_id
)
SELECT 'TRY_001_V1' AS control_id, s.source_instance_id,
       s.expected_entries, coalesce(e.entries,0) AS actual_entries,
       q.qnames AS expected_qnames, count(DISTINCT m.property_qname) AS actual_qnames,
       s.expected_evaluations, coalesce(o.evaluations,0) AS actual_evaluations,
       s.expected_valid, coalesce(o.valid,0) AS actual_valid,
       s.expected_missing, coalesce(o.missing,0) AS actual_missing,
       coalesce(c.violations,0) AS coverage_violations,
       coalesce(p1.violations,0)+coalesce(p2.violations,0) AS pin_violations
FROM pins s LEFT JOIN entry_counts e ON s.source_instance_id=e.source_instance_id
LEFT JOIN qname_counts q ON s.source_instance_id=q.source_instance_id
LEFT JOIN observed o ON s.source_instance_id=o.source_instance_id
LEFT JOIN coverage c ON s.source_instance_id=c.sid
LEFT JOIN m1_pin p1 ON s.source_instance_id=p1.source_instance_id
LEFT JOIN m2_pin p2 ON s.source_instance_id=p2.source_instance_id
LEFT JOIN m2 m ON s.source_instance_id=m.source_instance_id
GROUP BY ALL ORDER BY s.source_instance_id;
