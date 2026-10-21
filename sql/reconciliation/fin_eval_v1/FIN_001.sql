-- FIN_001_V1: SEC balance sheet, scoped positive reconciliation.
-- Read-only Databricks SQL. Baseline: SRC000055 / 2023q3.zip / num.txt / M1_LEXICAL_V1.
WITH facts AS (
    SELECT
        fields[0].lexical_value AS adsh,
        fields[1].lexical_value AS tag,
        fields[2].lexical_value AS taxonomy,
        fields[3].lexical_value AS ddate,
        fields[4].lexical_value AS qtrs,
        fields[5].lexical_value AS uom,
        fields[6].lexical_value AS segments,
        fields[7].lexical_value AS coreg,
        TRY_CAST(fields[8].lexical_value AS DECIMAL(38,4)) AS amount
    FROM workspace.edp_lab.q_c300_m1_records_reconciled_recovery_20261021_v2_full
    WHERE source_instance_id = 'SRC000055'
      AND binding_sha256 =
        '341ce895a89fe164c1cc14af2679aa0b4637f593c6887e5c4d3a74bc49bbebcd'
      AND run_id = 'main_recovery_20261021_v4_full'
      AND record_kind = 'DATA'
      AND admission_outcome = 'ACCEPTED'
),
scoped AS (
    SELECT * FROM facts
    WHERE adsh = '0000002178-23-000082'
      AND ddate IN ('20221231', '20230630')
      AND taxonomy = 'us-gaap/2023'
      AND qtrs = '0'
      AND uom = 'USD'
      AND segments = ''
      AND coreg = ''
      AND tag IN (
          'Assets', 'Liabilities', 'StockholdersEquity',
          'LiabilitiesAndStockholdersEquity'
      )
),
pivoted AS (
    SELECT
        ddate,
        COUNT(*) AS fact_count,
        COUNT(DISTINCT tag) AS distinct_tags,
        COUNT(amount) AS valid_amounts,
        MAX(CASE WHEN tag = 'Assets' THEN amount END) AS assets,
        MAX(CASE WHEN tag = 'Liabilities' THEN amount END) AS liabilities,
        MAX(CASE WHEN tag = 'StockholdersEquity' THEN amount END) AS equity,
        MAX(CASE WHEN tag = 'LiabilitiesAndStockholdersEquity' THEN amount END)
            AS reported_total
    FROM scoped
    GROUP BY ddate
)
SELECT
    ddate,
    assets,
    liabilities,
    equity,
    reported_total,
    assets - liabilities - equity AS difference_1,
    assets - reported_total AS difference_2,
    CASE
        WHEN fact_count = 4
         AND distinct_tags = 4
         AND valid_amounts = 4
         AND assets - liabilities - equity = 0
         AND assets - reported_total = 0
        THEN 'PASS'
        ELSE 'FAIL_OR_INCOMPLETE'
    END AS fin_001_result
FROM pivoted
ORDER BY ddate;
