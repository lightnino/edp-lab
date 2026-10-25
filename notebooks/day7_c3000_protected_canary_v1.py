# Databricks notebook source
"""One-row Day 7 protected connectivity canary; no RAW access or cohort work."""

TABLE = "workspace.edp_lab_day7_c3000.canary_pr80_v1"
UNIVERSE = "dcc63767c88ae712eab8f5ba29d52a206b4262710740e591a4b233d9c04c699b"
DECISION = "416efc5f7ab18b2570ba9beab26bba33210c5e0a75ec813a92ccac953af36d74"

spark_session = globals()["spark"]
notebook_utils = globals()["dbutils"]

spark_session.sql(
    f"CREATE TABLE IF NOT EXISTS {TABLE} USING DELTA AS SELECT "
    f"'{UNIVERSE}' AS universe_sha256, '{DECISION}' AS owner_decision_sha256"
)
rows = spark_session.sql(f"SELECT universe_sha256, owner_decision_sha256 FROM {TABLE}").collect()
assert len(rows) == 1 and tuple(rows[0]) == (UNIVERSE, DECISION)
notebook_utils.notebook.exit("DAY7_PROTECTED_CANARY_PASS")
