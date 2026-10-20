# GOLD_V2 evidence closeout and native Databricks execution

Databricks is the primary platform. This experiment covers only the registered
`SRC000002 / nasdaqlisted.txt` snapshot. DuckDB remains a local fallback; there is
no engine comparison, C300 ingestion, semantic integration or production rollout.

§2.7 is COMPLETE and §2.8 is TESTED. The durable reference is
[`metadata/native_nasdaq_checkpoint_v1.json`](../metadata/native_nasdaq_checkpoint_v1.json).
Native query results, Delta history, terminal execution status, integrity checks
and local validation logs remain in the referenced gitignored checkpoint bundle.
The final execution required no Free Edition workaround or remaining intervention.

## §2.7 closeout

The existing §2.6 V1 and V2 references and their sealed artifact hashes were
verified without rerunning profiling. All 13 GOLD_V2 observation reports retain
source/configuration identity, profiling outputs, execution traces, errors,
result fingerprints, runtime/code provenance, independent evaluation and replay
evidence. Each report preserves unresolved semantic decisions and empty semantic
promotions. The evidence index is `runs/databricks-native-v1/evidence-closeout.json`.
Historical C300 checkpoints and exclusions remain unchanged.

## §2.8 bounded implementation

`scripts/prepare_native_nasdaq.py` checks the retained evidence and registered RAW
SHA-256 before generating the execution contract. It uses exclusive output writes.
`notebooks/bronze_nasdaq_listed.py` reads the original uploaded bytes with native
Spark binaryFile, checks the registered hash, strictly decodes UTF-8 and validates
the exact header, CRLF framing, data widths and registered footer. Spark splits
literal fields without quote interpretation, trimming, inference or NULL mapping.
The exact original column names and string values are stored in Delta with name
column mapping enabled. Every occurrence retains line number, byte interval,
original record bytes, source identity, source paths, hashes and contract references.

The only Bronze table is `workspace.edp_lab.bronze_nasdaq_listed`. The notebook
creates it only if absent, and compares every row in both directions with
`exceptAll`, including occurrence lineage. Existing tables are never overwritten.
Native Spark SQL records counts, literal duplicate groups, blank/NULL counts,
literal NA witnesses, provenance, Delta history and detail. Full byte reconstruction
and exact per-occurrence text checks establish coverage of every persisted record.
Header/footer bytes and locators are retained separately in native results, and
the original RAW file remains in the Unity Catalog Volume.

The source has no literal empty fields or duplicate rows; a separate SQL probe
checks empty-string versus SQL NULL behavior. This probe does not establish source
NULL semantics, which remain unresolved. Duplicate multiplicity is verified over
the actual snapshot; no duplicate fixture is inserted into Bronze.

## Reproduction

Use existing local CLI OAuth profile `edp-lab`; never export tokens or enable debug
logging. The execution artifacts live in the gitignored `runs/databricks-native-v1/`.
The exact submission payload, notebook, input contract, run output, SQL statement
request/response and checkpoint hashes provide the reproduction inputs. For a new
execution, choose new local and Volume artifact directories and update the notebook
BASE accordingly. Reuse the unchanged registered RAW only after its hash passes.
Results and RAW bytes must remain uncommitted.

The SQL warehouse request is `sql-request.json`; submit it with
`databricks api post /api/2.0/sql/statements --json @runs/databricks-native-v1/sql-request.json -p edp-lab -o json`.
Poll the returned statement ID if its state is pending. The successful warehouse
response is `warehouse-sql-v2.json`; all notebook SQL texts and results are in
`native-results.json`. `environment.json` records connectivity and permissions
demonstrated by actual resource lookup, Volume reads/writes and table creation.

The native CLI sequence is:

```sh
.venv/bin/python scripts/prepare_native_nasdaq.py
databricks fs mkdir dbfs:/Volumes/workspace/edp_lab/raw/edp-native-v1 -p edp-lab
databricks fs cp data/raw/nasdaq/nasdaqlisted.txt dbfs:/Volumes/workspace/edp_lab/raw/edp-native-v1/nasdaqlisted.txt -p edp-lab
databricks fs cp runs/databricks-native-v1/contract.json dbfs:/Volumes/workspace/edp_lab/raw/edp-native-v1/contract.json -p edp-lab
databricks fs cp notebooks/bronze_nasdaq_listed.py dbfs:/Volumes/workspace/edp_lab/raw/edp-native-v1/notebook-v3.py -p edp-lab
databricks workspace import /Shared/edp-lab-native-v1/bronze_nasdaq_listed_v3 --file notebooks/bronze_nasdaq_listed.py --format SOURCE --language PYTHON -p edp-lab
databricks jobs submit --json @runs/databricks-native-v1/submit-v3.json --no-wait -p edp-lab -o json
```

Notebook execution writes `native-results.json` exclusively and returns the same
JSON through the Jobs API. Inspect run/task output for exact execution failures;
a pending run or inaccessible capability is not a successful verification.

The first run failed because the native runtime rejected the DataFrame writer's
`errorifexists` mode with `[UNSUPPORTED_OPERATION] errorifexists is not supported`.
Its task output and original notebook are retained. A SQL warehouse query made
before the corrected table creation likewise retains its TABLE_OR_VIEW_NOT_FOUND
failure. The corrected notebook uses SQL CREATE TABLE with Delta properties;
neither failure is hidden or attributed to Free Edition without evidence.
The second notebook attempt created Bronze and passed native queries and byte
reconstruction, then failed a verifier assertion comparing a tuple to a list.
That assertion was corrected to compare tuples. Its error trace is preserved;
the subsequent notebook validates the existing table without overwriting it.

After retrieving native results and terminal run state, execute
`.venv/bin/python scripts/seal_native_nasdaq.py`. This verifies successful notebook
and warehouse execution, hashes native results and code, records local checks and
creates a new exclusive checkpoint plus its metadata reference. It does not run
profiling or ingest any data. Source and result SHA-256 values are distinct from
the checkpoint fingerprint (canonical JSON excluding the fingerprint field).
