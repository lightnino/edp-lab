-- FIN_002_V1: detect wrong equity definition; positive and negative controls.
-- PASS means incorrect parent-only equity is detected, not accepted.
WITH facts AS (
    SELECT
        fields[1].lexical_value AS tag,
        TRY_CAST(fields[8].lexical_value AS DECIMAL(38,4)) AS amount
    FROM workspace.edp_lab.q_c300_m1_records_reconciled_recovery_20261021_v2_full
    WHERE source_instance_id = 'SRC000055'
      AND binding_sha256 =
        '341ce895a89fe164c1cc14af2679aa0b4637f593c6887e5c4d3a74bc49bbebcd'
      AND run_id = 'main_recovery_20261021_v4_full'
      AND record_kind = 'DATA'
      AND admission_outcome = 'ACCEPTED'
      AND fields[0].lexical_value = '0000002969-23-000037'
      AND fields[2].lexical_value = 'us-gaap/2023'
      AND fields[3].lexical_value = '20230630'
      AND fields[4].lexical_value = '0'
      AND fields[5].lexical_value = 'USD'
      AND fields[6].lexical_value = ''
      AND fields[7].lexical_value = ''
      AND fields[1].lexical_value IN (
          'Assets', 'Liabilities', 'StockholdersEquity',
          'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
          'LiabilitiesAndStockholdersEquity'
      )
),
p AS (
    SELECT
        COUNT(*) AS n_facts,
        COUNT(DISTINCT tag) AS n_tags,
        COUNT(amount) AS n_valid_amounts,
        MAX(CASE WHEN tag = 'Assets' THEN amount END) AS assets,
        MAX(CASE WHEN tag = 'Liabilities' THEN amount END) AS liabilities,
        MAX(CASE WHEN tag = 'StockholdersEquity' THEN amount END) AS equity_parent,
        MAX(CASE WHEN tag =
            'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'
            THEN amount END) AS equity_including_nci,
        MAX(CASE WHEN tag = 'LiabilitiesAndStockholdersEquity' THEN amount END)
            AS reported_total
    FROM facts
)
SELECT
    assets - liabilities - equity_including_nci AS correct_difference,
    assets - liabilities - equity_parent AS wrong_equity_difference,
    equity_including_nci - equity_parent AS implied_nci,
    CASE
        WHEN n_facts = 5
         AND n_tags = 5
         AND n_valid_amounts = 5
         AND assets = reported_total
         AND assets - liabilities - equity_including_nci = 0
         AND assets - liabilities - equity_parent =
             equity_including_nci - equity_parent
         AND equity_including_nci <> equity_parent
        THEN 'PASS'
        ELSE 'FAIL_OR_INCOMPLETE'
    END AS fin_002_result
FROM p;
