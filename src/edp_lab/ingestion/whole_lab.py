"""Publisher-native physical-delivery acquisition; no admission or cohort freeze."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from zipfile import BadZipFile

from edp_lab.ingestion.c300_acquisition import (
    CATALOGS,
    DIRECTORIES,
    Links,
    inspect_payload,
    now,
    object_hash,
    select_candidates,
    write_new,
)
from edp_lab.ingestion.inventory import sha256_file
from edp_lab.ingestion.local_sources import (
    load_availability,
    local_match,
    move_existing,
    verify_representation,
)

VERSION = "WHOLE_LAB_CANDIDATES_V1"
PAGES = {
    "ECB": "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/"
           "euro_reference_exchange_rates/html/index.en.html",
    "CFTC": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/"
            "HistoricalCompressed/index.htm",
    "NYC_TLC": "https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page",
    "TREASURY": "https://home.treasury.gov/treasury-daily-interest-rate-xml-feed",
    "NASDAQ": "https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs",
}
HOSTS = {"www.sec.gov", "sec.gov", "www.ecb.europa.eu", "www.cftc.gov", "www.nyc.gov",
         "home.treasury.gov", "www.nasdaqtrader.com", "nasdaqtrader.com",
         "d37ci6vzurychx.cloudfront.net"}


def checked_url(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc not in HOSTS:
        raise ValueError(f"Unexpected publisher host: {url}")
    return url


class CurlFetcher:
    """Use native macOS TLS verification, with retained bodies and transfer metadata."""

    def __init__(self, directory, user_agent, requests_per_second=3):
        if not 0 < requests_per_second <= 3:
            raise ValueError("Request rate must be positive and at most 3/second")
        self.directory = directory
        self.user_agent = user_agent
        self.interval = 1 / requests_per_second
        self.last = None
        self.blocked_hosts = set()
        self.request_lock = threading.Lock()

    def fetch(self, url):
        checked_url(url)
        host = urlsplit(url).netloc
        if host in self.blocked_hosts:
            raise ValueError(f"Publisher access blocked earlier: {host}")
        for number in range(3):
            with self.request_lock:
                if self.last is not None:
                    time.sleep(max(0, self.interval - (time.monotonic() - self.last)))
                self.last = time.monotonic()
            attempts = self.directory / "attempts"
            attempts.mkdir(parents=True, exist_ok=True)
            folder = Path(tempfile.mkdtemp(prefix="request-", dir=attempts))
            body = folder / "body"
            started = now()
            result = subprocess.run([
                "/usr/bin/curl", "--silent", "--show-error", "--http1.1", "--location",
                "--max-redirs", "5", "--proto", "=https", "--proto-redir", "=https",
                "--connect-timeout", "20", "--max-time", "600",
                "--speed-time", "60", "--speed-limit", "1024", "--user-agent",
                (self.user_agent if host in {"www.sec.gov", "sec.gov"}
                 else "EDP-Lab-source-inventory/1.0"),
                "--header", "Accept-Encoding: identity", "--output", str(body),
                "--dump-header", str(folder / "headers.txt"), "--write-out", "%{json}", url,
            ], capture_output=True, text=True, check=False)
            try:
                transfer = json.loads(result.stdout)
            except ValueError:
                transfer = {}
            status = int(transfer.get("http_code", 0))
            receipt = {"version": VERSION, "requested_url": url, "started_at_utc": started,
                       "finished_at_utc": now(), "curl_exit_code": result.returncode,
                       "transfer": transfer,
                       "user_agent": (self.user_agent if host in {"www.sec.gov", "sec.gov"}
                                      else "EDP-Lab-source-inventory/1.0"),
                       "error": result.stderr, "status": "FAILED"}
            if body.exists():
                receipt.update(sha256=sha256_file(body), bytes=body.stat().st_size)
            if (result.returncode == 0 and status == 200 and body.exists()
                    and body.stat().st_size > 0):
                try:
                    checked_url(transfer["url_effective"])
                    if body.stat().st_size != int(transfer["size_download"]):
                        raise ValueError("Transfer byte accounting mismatch")
                    receipt["status"] = "COMPLETE"
                except ValueError as exc:
                    receipt["error"] = str(exc)
            write_new(folder / "receipt.json", receipt)
            if receipt["status"] == "COMPLETE":
                return {"body": str(body.relative_to(self.directory)), "sha256": receipt["sha256"],
                        "receipt": str((folder / "receipt.json").relative_to(self.directory)),
                        "receipt_sha256": sha256_file(folder / "receipt.json")}
            if status in {403, 429}:
                self.blocked_hosts.add(host)
            retry_transport = result.returncode in {5, 6, 7, 18, 28, 52, 55, 56}
            if (not retry_transport and status not in {0, 500, 502, 503, 504}) or number == 2:
                raise ValueError(f"Publisher retrieval failed HTTP {status}; evidence {folder}")
            time.sleep(2 ** (number + 1))
        raise AssertionError("unreachable")


PUBLISHER_DIRECTORIES = {
    "SEC": "sec", "NASDAQ": "nasdaq", "TREASURY": "treasury",
    "CFTC": "cftc", "ECB": "ecb", "NYC_TLC": "nyc_tlc",
}


def canonical_delivery_path(plan, candidate, capture):
    """Physical edition identity includes plan, publisher URL and actual SHA-256."""
    family = candidate["family"].lower()
    filename = (candidate["edition"] + ".xml" if candidate["publisher"] == "TREASURY"
                else candidate["filename"])
    if any(Path(part).name != part or part in {"", ".", ".."}
           for part in (family, filename)):
        raise ValueError("Unsafe publisher path component")
    root = Path.cwd() / "data/raw" / PUBLISHER_DIRECTORIES[candidate["publisher"]]
    return root / family / delivery_candidate_id(plan, candidate, capture) / filename


def capture_body(directory, capture, expected_url=None):
    body = (directory / capture["body"]).resolve()
    receipt = (directory / capture["receipt"]).resolve()
    if not body.is_relative_to(directory.resolve()) or not receipt.is_relative_to(
            directory.resolve()):
        raise ValueError("Evidence path escape")
    relocation = directory / "relocations" / f"{object_hash(capture['body'])}.json"
    if not body.exists() and relocation.exists():
        audit = json.loads(relocation.read_bytes())
        relocated = Path(audit["final_path"]).resolve()
        if (audit["original_body"] != capture["body"] or audit["sha256"] != capture["sha256"]
                or not relocated.is_relative_to((Path.cwd() / "data/raw/whole_lab").resolve())):
            raise ValueError("Invalid candidate relocation audit")
        body = relocated
    current = directory / "publisher-relocations" / f"{object_hash(capture['body'])}.json"
    if current.exists():
        audit = json.loads(current.read_bytes())
        plan = json.loads((directory / "candidates.json").read_bytes())
        candidate = next(c for c in plan["candidates"]
                         if c["candidate_id"] == audit["candidate_id"])
        target = canonical_delivery_path(plan, candidate, capture).resolve()
        if (audit["old_path"] != str(body) or audit["final_path"] != str(target)
                or audit["sha256"] != capture["sha256"]
                or audit["original_body"] != capture["body"]
                or (relocation.exists() and audit["previous_audit_sha256"] !=
                    sha256_file(relocation))):
            raise ValueError("Invalid publisher relocation audit")
        if target.exists():
            if body.exists() and body != target:
                raise ValueError("Duplicate relocation source and destination")
            body = target
    if sha256_file(body) != capture["sha256"] or sha256_file(receipt) != capture["receipt_sha256"]:
        raise ValueError("Retained evidence changed")
    evidence = json.loads(receipt.read_bytes())
    if (evidence.get("status") != "COMPLETE" or evidence.get("sha256") != capture["sha256"]
            or evidence.get("bytes") != body.stat().st_size
            or (expected_url is not None and evidence.get("requested_url") != expected_url)):
        raise ValueError("Receipt/body/publisher association mismatch")
    return body


def links(raw, base):
    parser = Links()
    parser.feed(raw.decode("utf-8", errors="strict"))
    return sorted({urljoin(base, h) for h in parser.hrefs})


def discover(directory, fetcher):
    plan_path = directory / "candidates.json"
    if plan_path.exists():
        return load_plan(directory)
    captures, failures, candidates = {}, [], {}

    def metadata(url):
        try:
            capture = fetcher.fetch(url)
            captures[url] = capture
            return capture_body(directory, capture).read_bytes()
        except (OSError, ValueError) as exc:
            failures.append({"url": url, "error": str(exc)})
            print(json.dumps(failures[-1]), flush=True)
            return None

    def add(publisher, family, edition, url, discovery_url):
        checked_url(url)
        if url not in candidates:
            candidates[url] = {"publisher": publisher, "family": family, "edition": edition,
                               "url": url, "filename": Path(urlsplit(url).path).name,
                               "discovery_url": discovery_url, "candidate_id": object_hash(url),
                               "status": "UNADMITTED_CANDIDATE"}

    # Reuse the previously approved C300 selection verbatim when discovery succeeds.
    sec_docs = {}
    for url in [*CATALOGS.values(), *DIRECTORIES]:
        raw = metadata(url)
        if raw is not None:
            sec_docs[url] = raw
    if len(sec_docs) == 6:
        for item in select_candidates(sec_docs):
            add("SEC", item["family"], item["edition"], item["url"], item["discovery_url"])

    for publisher, page in PAGES.items():
        raw = metadata(page)
        if raw is None:
            continue
        published_links = links(raw, page)
        if publisher == "ECB":
            for url in published_links:
                if urlsplit(url).path.endswith("/eurofxref-hist.zip"):
                    add(publisher, "ECB_REFERENCE_RATES", "PUBLISHER_SNAPSHOT_AT_RETRIEVAL", url, page)
        elif publisher == "CFTC":
            for url in published_links:
                if re.search(r"/files/dea/history/[^/]+_?202[45]\.zip$", urlsplit(url).path):
                    add(publisher, "CFTC_COT", Path(urlsplit(url).path).stem, url, page)
        elif publisher == "NYC_TLC":
            # Exactly native monthly Parquet releases, no converted exports/record slicing.
            for url in published_links:
                if re.search(r"/(yellow|green|fhv|fhvhv)_tripdata_2025-0[123]\.parquet$",
                             urlsplit(url).path):
                    add(publisher, "NYC_TLC_TRIPS", Path(urlsplit(url).path).stem, url, page)
        elif publisher == "NASDAQ":
            # Additional native directory product; old local listed/otherlisted stay untouched.
            add(publisher, "NASDAQ_TRADED_DIRECTORY", "PUBLISHER_SNAPSHOT_AT_RETRIEVAL",
                "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt", page)
        elif publisher == "TREASURY":
            for kind in ["daily_treasury_yield_curve", "daily_treasury_bill_rates",
                         "daily_treasury_long_term_rate", "daily_treasury_real_yield_curve",
                         "daily_treasury_real_long_term"]:
                url = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
                       f"pages/xml?data={kind}&field_tdr_date_value=2025")
                add(publisher, "TREASURY_ANNUAL_XML", kind + "_2025", url, page)

    # Additional daily deliveries are actual publisher-listed files, not generated dates.
    # Stop a blocked host; still retain the other publishers' discoveries.
    for year in range(2011, 2024):
        if len(candidates) >= 3300 or "www.sec.gov" in fetcher.blocked_hosts:
            break
        for quarter in range(1, 5):
            url = f"https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{quarter}/index.json"
            raw = metadata(url)
            if raw is None:
                break
            for item in json.loads(raw)["directory"]["item"]:
                name = item["name"]
                if re.fullmatch(rf"master\.{year}[0-9]{{4}}\.idx", name):
                    add("SEC", "SEC_EDGAR_DAILY_MASTER", name[7:15], urljoin(url, name), url)
    plan = {"version": VERSION, "captures": captures, "failures": failures,
            "candidates": list(candidates.values()), "created_at_utc": now(),
            "tool_sha256": sha256_file(Path(__file__)), "target_verified_physical_instances": 3001,
            "requested_nested_sizes": [300, 700, 1500, 2000, 3000],
            "cohort_status": "NOT_FROZEN", "admission_status": "NOT_ADMITTED"}
    plan["plan_sha256"] = object_hash(plan)
    write_new(plan_path, plan)
    return plan


def load_plan(directory):
    plan = json.loads((directory / "candidates.json").read_bytes())
    if plan["version"] != VERSION or plan["plan_sha256"] != object_hash(
            {k: v for k, v in plan.items() if k != "plan_sha256"}):
        raise ValueError("Whole Lab plan hash/version mismatch")
    for capture in plan["captures"].values():
        capture_body(directory, capture)
    return plan


def check_payload(path, candidate):
    filename = candidate["filename"]
    if filename.endswith(".zip"):
        return inspect_payload(path, filename)
    with path.open("rb") as stream:
        prefix = stream.read(4096)
        if filename.endswith(".parquet"):
            stream.seek(-4, 2)
            if prefix[:4] != b"PAR1" or stream.read(4) != b"PAR1":
                raise ValueError("Not a native Parquet container")
    if b"<html" in prefix.lower() or b"<!doctype html" in prefix.lower():
        raise ValueError("HTML response instead of dataset")
    if candidate["publisher"] == "TREASURY":
        tree = ET.parse(path)
        if not tree.findall("{http://www.w3.org/2005/Atom}entry"):
            raise ValueError("Treasury response has no published entries")
    return {"physical_format_check": "PASS", "parser_approval": "NOT_APPROVED"}


def download(directory, fetcher, local_inventory, limit, *, workers=1):
    if not 1 <= workers <= 3:
        raise ValueError("Use one to three workers sharing the request limiter")
    plan = load_plan(directory)
    pending = []
    for candidate in plan["candidates"]:
        path = directory / f"delivery-{candidate['candidate_id']}.json"
        if path.exists():
            record = json.loads(path.read_bytes())
            capture_body(directory, record["capture"])
            continue
        pending.append(candidate)

    def acquire(candidate):
        path = directory / f"delivery-{candidate['candidate_id']}.json"
        if urlsplit(candidate["url"]).netloc in fetcher.blocked_hosts:
            return
        try:
            if local_match(candidate, local_inventory) is not None:
                return
            if shutil.disk_usage(directory).free < 5 * 1024 ** 3:
                raise ValueError("Less than 5 GiB workspace headroom")
            capture = fetcher.fetch(candidate["url"])
            body = capture_body(directory, capture)
            if candidate.get("expected_sha256") and candidate["expected_sha256"] != capture["sha256"]:
                raise ValueError("Delivery differs from expected publisher-edition hash")
            inspection = check_payload(body, candidate)
            record = {"version": VERSION, "plan_sha256": plan["plan_sha256"],
                      "candidate": candidate, "capture": capture, "inspection": inspection,
                      "status": "MECHANICALLY_VERIFIED_CANDIDATE", "admission": "NOT_ADMITTED"}
            write_new(path, record)
            print(json.dumps({"verified_candidate": candidate["candidate_id"],
                              "publisher": candidate["publisher"],
                              "url": candidate["url"], "bytes": body.stat().st_size}), flush=True)
        except (OSError, ValueError, BadZipFile, ET.ParseError) as exc:
            folder = Path(tempfile.mkdtemp(prefix="failure-", dir=directory))
            write_new(folder / "failure.json", {"candidate": candidate, "error": str(exc)})
            print(json.dumps({"failed": candidate["url"], "error": str(exc)}), flush=True)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(acquire, pending[:limit]))


def report(directory):
    plan = load_plan(directory)
    expected = {c["candidate_id"]: c for c in plan["candidates"]}
    counts, hashes = Counter(), defaultdict(list)
    total_bytes = 0
    for path in sorted(directory.glob("delivery-*.json")):
        record = json.loads(path.read_bytes())
        if record["plan_sha256"] != plan["plan_sha256"]:
            raise ValueError("Delivery belongs to another plan")
        candidate = record["candidate"]
        if expected.get(candidate["candidate_id"]) != candidate:
            raise ValueError("Delivery differs from publisher discovery plan")
        body = capture_body(directory, record["capture"], candidate["url"])
        counts[record["candidate"]["publisher"]] += 1
        hashes[record["capture"]["sha256"]].append(record["candidate"]["candidate_id"])
        total_bytes += body.stat().st_size
    return {"version": VERSION, "discovered_candidates": len(plan["candidates"]),
            "verified_downloaded_deliveries": sum(counts.values()), "publishers": dict(counts),
            "bytes": total_bytes, "equal_hash_groups_requiring_review": [
                ids for ids in hashes.values() if len(ids) > 1],
            "discovery_failures": plan["failures"], "admission": "NOT_ADMITTED",
            "cohort_status": "NOT_FROZEN", "requested_nested_sizes": plan["requested_nested_sizes"]}


def review_packet(directory, availability_path):
    """Seal a reproducible review inventory and nested candidate selections, not cohorts."""
    plan = load_plan(directory)
    summary = report(directory)
    availability = load_availability(availability_path)
    entries = []
    for dataset in availability["datasets"]:
        for representation in dataset["representations"]:
            if representation.get("availability") == "VERIFIED":
                verify_representation(representation)
        entries.append({"inventory_id": dataset["dataset_id"], "origin": "EXISTING_LOCAL",
                        "dataset": dataset})
    records = {r["candidate"]["candidate_id"]: r for r in (
        json.loads(p.read_bytes()) for p in directory.glob("delivery-*.json"))}
    review_ids = {identifier for group in summary["equal_hash_groups_requiring_review"]
                  for identifier in group}
    for candidate in plan["candidates"]:
        record = records.get(candidate["candidate_id"])
        if record is not None:
            entries.append({"inventory_id": candidate["candidate_id"], "origin": "ACQUIRED",
                            "delivery_candidate_id": delivery_candidate_id(
                                plan, candidate, record["capture"]),
                            "physical_path": str(capture_body(directory, record["capture"],
                                                               candidate["url"])),
                            "physical_eligibility": ("EQUAL_HASH_DELIVERY_REVIEW_REQUIRED"
                                                     if candidate["candidate_id"] in review_ids
                                                     else "VERIFIED_CANDIDATE_FOR_ADMISSION_REVIEW"),
                            "record": record})
    selections = {}
    for size in plan["requested_nested_sizes"]:
        selected = plan["candidates"][:size]
        unresolved = [c["candidate_id"] for c in selected
                      if c["candidate_id"] not in records or c["candidate_id"] in review_ids]
        selections[f"C{size}"] = {
            "status": "DRAFT_CANDIDATE_SELECTION_NOT_ADMITTED_NOT_FROZEN",
            "requested_size": size, "candidate_ids": [c["candidate_id"] for c in selected],
            "mechanical_readiness": "BLOCKED" if unresolved or len(selected) != size else "PASS",
            "unresolved_candidate_ids": unresolved}
    packet = {"version": "WHOLE_LAB_REVIEW_INVENTORY_V1", "plan_sha256": plan["plan_sha256"],
              "local_availability_sha256": sha256_file(availability_path), "entries": entries,
              "candidate_selections": selections, "summary": summary,
              "verified_candidates_without_equal_hash_review": len(records) - len(review_ids),
              "existing_admitted_gold_instances": sum(d["status"] ==
                  "EXISTING_GOLD_ADMISSION_UNCHANGED" for d in availability["datasets"]),
              "existing_unadmitted_bulk_datasets": sum(d["status"] ==
                  "EXISTING_UNADMITTED_CANDIDATE" for d in availability["datasets"]),
              "new_admissions": 0, "frozen_cohorts_created": 0}
    digest = object_hash(packet)
    output = directory / f"review-inventory-{digest}.json"
    if not output.exists():
        write_new(output, packet)
    elif json.loads(output.read_bytes()) != packet:
        raise ValueError("Existing review inventory differs")
    return {"review_inventory": str(output), "sha256": sha256_file(output),
            "verified_candidates_without_equal_hash_review": len(records) - len(review_ids),
            "existing_local_datasets": len(availability["datasets"]),
            "selection_readiness": {k: v["mechanical_readiness"] for k, v in selections.items()},
            "new_admissions": 0, "frozen_cohorts_created": 0}


def delivery_candidate_id(plan, candidate, capture):
    """Work-list reference including the actual bytes/plan; never an admitted SRC ID."""
    return object_hash({"plan": plan["plan_sha256"], "url": candidate["url"],
                        "raw_sha256": capture["sha256"]})


def organize_acquired(directory):
    """Preflight all deliveries, then exclusively rename with append-only path evidence."""
    plan = load_plan(directory)
    expected = {c["candidate_id"]: c for c in plan["candidates"]}
    audits = directory / "publisher-relocations"
    audits.mkdir(exist_ok=True)
    pending = []
    targets = set()
    for path in sorted(directory.glob("delivery-*.json")):
        record = json.loads(path.read_bytes())
        candidate, capture = record["candidate"], record["capture"]
        if record["plan_sha256"] != plan["plan_sha256"] or expected.get(
                candidate["candidate_id"]) != candidate:
            raise ValueError("Candidate differs from discovery plan")
        body = capture_body(directory, capture, candidate["url"])
        target = canonical_delivery_path(plan, candidate, capture).resolve()
        if target in targets:
            raise ValueError("Duplicate relocation target")
        targets.add(target)
        if body.resolve() == target:
            continue
        if target.exists() or target.is_symlink():
            raise ValueError("Relocation destination already exists")
        audit_path = audits / f"{object_hash(capture['body'])}.json"
        previous = directory / "relocations" / audit_path.name
        audit = {"version": "PUBLISHER_RELOCATION_V1", "original_body": capture["body"],
                 "old_path": str(body), "final_path": str(target),
                 "sha256": capture["sha256"], "bytes": body.stat().st_size,
                 "candidate_id": candidate["candidate_id"],
                 "previous_audit_sha256": sha256_file(previous) if previous.exists() else None,
                 "delivery_evidence_sha256": sha256_file(path), "admission": "NOT_ADMITTED"}
        if audit_path.exists() and json.loads(audit_path.read_bytes()) != audit:
            raise ValueError("Prepared relocation audit differs")
        pending.append((body, target, audit_path, audit, capture, candidate))
    for body, target, audit_path, audit, capture, candidate in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not audit_path.exists():
            write_new(audit_path, audit)
        move_existing(body, target, expected_sha256=audit["sha256"], expected_bytes=audit["bytes"])
        capture_body(directory, capture, candidate["url"])
    return {"organized_verified_deliveries": len(targets), "raw_root": "data/raw/<publisher>",
            "new_admissions": 0, "frozen_cohorts_created": 0}


def corpus_availability(local_inventory, *, root=None):
    """Include verified previous acquisition runs, not just the six imported datasets."""
    datasets = list(local_inventory["datasets"])
    root = Path.cwd() if root is None else Path(root).resolve()
    for plan_path in sorted((root / "runs/whole_lab").rglob("candidates.json")):
        directory = plan_path.parent
        plan = load_plan(directory)
        expected = {c["candidate_id"]: c for c in plan["candidates"]}
        for path in directory.glob("delivery-*.json"):
            record = json.loads(path.read_bytes())
            candidate = record["candidate"]
            if (record["plan_sha256"] != plan["plan_sha256"] or expected.get(
                    candidate["candidate_id"]) != candidate):
                raise ValueError("Existing corpus delivery differs from discovery evidence")
            body = capture_body(directory, record["capture"], candidate["url"])
            datasets.append({"dataset_id": f"ACQUIRED:{plan['plan_sha256']}:"
                                          f"{candidate['candidate_id']}",
                             "family": candidate["family"], "edition_label": candidate["edition"],
                             "publisher_url_hints": [candidate["url"]],
                             "representations": [{"kind": "FILE", "path": str(body),
                                                  "bytes": body.stat().st_size,
                                                  "sha256": record["capture"]["sha256"],
                                                  "availability": "VERIFIED"}]})
    return {"version": local_inventory["version"], "datasets": datasets}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("discover", "download", "report", "organize", "packet"))
    parser.add_argument("--directory", type=Path, default=Path("runs/whole_lab/candidates-v1"))
    parser.add_argument("--limit", type=int, default=3001)
    parser.add_argument("--requests-per-second", type=float, default=3)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not directory.is_relative_to(Path.cwd() / "runs/whole_lab"):
        parser.error("Evidence must be under runs/whole_lab/")
    directory.mkdir(parents=True, exist_ok=True)
    if args.limit < 1:
        parser.error("--limit must be positive")
    if args.action == "organize":
        print(json.dumps(organize_acquired(directory), sort_keys=True))
        return 0
    if args.action == "packet":
        print(json.dumps(review_packet(directory, Path.cwd() /
                                       "runs/local_inventory/availability.json"), sort_keys=True))
        return 0
    if args.action in {"discover", "download"}:
        contact = os.environ.get("SEC_USER_AGENT")
        if not contact:
            email = subprocess.run(['git', 'config', '--get', 'user.email'],
                                   capture_output=True, text=True, check=False).stdout.strip()
            if not email or '@' not in email:
                parser.error("Actual SEC contact is required in SEC_USER_AGENT or Git user.email")
            contact = f"EDP-Lab-source-inventory/1.0 ({email})"
        source_copy = directory / f"tool-{sha256_file(Path(__file__))}.py"
        if not source_copy.exists():
            with source_copy.open('xb') as stream:
                stream.write(Path(__file__).read_bytes())
        fetcher = CurlFetcher(directory, contact, args.requests_per_second)
        if args.action == "discover":
            discover(directory, fetcher)
        else:
            inventory = corpus_availability(load_availability(
                Path.cwd() / "runs/local_inventory/availability.json"))
            download(directory, fetcher, inventory, args.limit, workers=args.workers)
    print(json.dumps(report(directory), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
