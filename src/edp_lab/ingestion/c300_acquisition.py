"""SEC C300 candidate discovery and acquisition. Never admits or freezes sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import tempfile
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from html.parser import HTMLParser
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zipfile import BadZipFile, ZipFile

from edp_lab.ingestion.inventory import sha256_file
from edp_lab.ingestion.local_sources import load_availability, local_match

VERSION = "C300_ACQUISITION_V1"
BASE = "https://www.sec.gov"
CATALOGS = {
    "SEC_FSDS": BASE + "/dera/data/financial-statement-data-sets.html",
    "SEC_13F": BASE + "/data-research/sec-markets-data/form-13f-data-sets",
}
DIRECTORIES = [BASE + f"/Archives/edgar/daily-index/2023/QTR{q}/index.json"
               for q in range(1, 5)]
EXPECTED_COUNTS = {"SEC_FSDS": 60, "SEC_13F": 42, "SEC_EDGAR_DAILY_MASTER": 198}


def now():
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode()


def object_hash(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def write_new(path, value):
    with path.open("xb") as stream:
        stream.write(encoded(value))


def specification():
    """Offline approved scope, with no invented publisher observations or source IDs."""
    return {"version": VERSION, "population": EXPECTED_COUNTS,
            "catalogs": CATALOGS, "daily_directories": DIRECTORIES,
            "selection": {"SEC_FSDS": {"first": "2011Q1", "last": "2025Q4"},
                          "SEC_13F": {"first": "2013Q3", "last": "2023Q4"},
                          "SEC_EDGAR_DAILY_MASTER": {
                              "year": 2023, "filename_regex": r"master\.2023[0-9]{4}\.idx",
                              "order": "ASCENDING_FILENAME_DATE", "take": 198}},
            "authority": "User approved population, minimum policy and separate versioned manifest; "
                         "authorized acquisition tooling and candidate preparation only.",
            "authority_timestamp": None, "admission_status": "NOT_ADMITTED",
            "parser_status": "NOT_APPROVED", "cohort_status": "NOT_FROZEN"}


def prepare_specification(directory):
    value = specification()
    value["specification_sha256"] = object_hash(value)
    path = directory / "acquisition-spec.json"
    if path.exists():
        if path.read_bytes() != encoded(value):
            raise ValueError("Existing acquisition specification differs")
    else:
        write_new(path, value)
    return value


def official_url(url):
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.netloc not in {"www.sec.gov", "sec.gov"}
            or parts.query or parts.fragment or ".." in parts.path.split("/")):
        raise ValueError(f"Unsupported publisher URL: {url}")
    return url


def workspace(root, directory):
    root = root.resolve()
    directory = (directory if directory.is_absolute() else root / directory).resolve()
    if not directory.is_relative_to(root / "runs" / "c300"):
        raise ValueError("Candidate evidence must be under runs/c300/")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def local_file(directory, relative):
    path = (directory / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(directory.resolve()):
        raise ValueError("Evidence path escapes candidate workspace")
    return path


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.extend(v for k, v in attrs if k == "href" and v)


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        official_url(newurl)
        time.sleep(1)  # Redirect requests share the same conservative rate budget.
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Fetcher:
    """One process, <=1 request/second; independent, retained attempts on retry."""

    def __init__(self, directory, user_agent):
        if not user_agent or "@" not in user_agent or any(c in user_agent for c in "\r\n"):
            raise ValueError("Supply an actual SEC User-Agent with a contact email")
        self.directory = directory
        self.user_agent = user_agent
        self.opener = build_opener(OfficialRedirects())
        self.last_request = None

    def fetch(self, url, *, attempts=3):
        official_url(url)
        attempts_dir = self.directory / "attempts"
        attempts_dir.mkdir(exist_ok=True)
        for attempt in range(attempts):
            if self.last_request is not None:
                time.sleep(max(0, 1 - (time.monotonic() - self.last_request)))
            folder = Path(tempfile.mkdtemp(prefix="request-", dir=attempts_dir))
            body = folder / "body"
            receipt = {"version": VERSION, "requested_url": url, "started_at_utc": now(),
                       "user_agent": self.user_agent, "accept_encoding": "identity",
                       "publisher_checksum": None, "status": "FAILED"}
            retry = False
            response = None
            self.last_request = time.monotonic()
            try:
                response = self.opener.open(Request(url, headers={
                    "User-Agent": self.user_agent, "Accept-Encoding": "identity"}), timeout=60)
                with response, body.open("xb") as target:
                    receipt.update(final_url=official_url(response.url),
                                   http_status=response.status, headers=list(response.headers.items()))
                    if response.status != 200:
                        raise ValueError(f"Unexpected HTTP status {response.status}")
                    if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                        raise ValueError("Unexpected HTTP content encoding")
                    digest, length = hashlib.sha256(), 0
                    for block in iter(lambda stream=response: stream.read(1024 * 1024), b""):
                        target.write(block)
                        digest.update(block)
                        length += len(block)
                expected = response.headers.get("Content-Length")
                if expected is not None and int(expected) != length:
                    raise ValueError("HTTP Content-Length mismatch")
                if length == 0 or sha256_file(body) != digest.hexdigest():
                    raise ValueError("Empty response or independent SHA-256 mismatch")
                receipt.update(status="COMPLETE", sha256=digest.hexdigest(), bytes=length)
            except HTTPError as exc:
                receipt.update(http_status=exc.code, headers=list(exc.headers.items()),
                               error=f"HTTPError: {exc.code}")
                # Retain error bodies, including SEC access-denial pages.
                with exc, body.open("xb") as target:
                    for block in iter(lambda stream=exc: stream.read(1024 * 1024), b""):
                        target.write(block)
                retry = exc.code in {500, 502, 503, 504}
            except (OSError, URLError, ValueError, HTTPException) as exc:
                receipt["error"] = f"{type(exc).__name__}: {exc}"
                retry = isinstance(exc, (OSError, URLError, HTTPException))
            finally:
                receipt["finished_at_utc"] = now()
                if body.exists():
                    receipt["retained_body_sha256"] = sha256_file(body)
                    receipt["retained_body_bytes"] = body.stat().st_size
                write_new(folder / "receipt.json", receipt)
            if receipt["status"] == "COMPLETE":
                return {"body": str(body.relative_to(self.directory)),
                        "sha256": receipt["sha256"],
                        "receipt": str((folder / "receipt.json").relative_to(self.directory)),
                        "receipt_sha256": sha256_file(folder / "receipt.json")}
            if not retry or attempt == attempts - 1:
                raise ValueError(f"Retrieval failed; retained evidence: {folder}")
            time.sleep(2 ** (attempt + 1))
        raise AssertionError("Unreachable")


def verified_capture(directory, reference, expected_url):
    body = local_file(directory, reference["body"])
    receipt_path = local_file(directory, reference["receipt"])
    if (sha256_file(body) != reference["sha256"]
            or sha256_file(receipt_path) != reference["receipt_sha256"]):
        raise ValueError("Changed acquisition evidence")
    receipt = json.loads(receipt_path.read_bytes())
    if (receipt["status"] != "COMPLETE" or receipt["requested_url"] != expected_url
            or receipt["sha256"] != reference["sha256"]
            or receipt["bytes"] != body.stat().st_size):
        raise ValueError("Receipt/source mismatch")
    official_url(receipt["final_url"])
    return body


def select_candidates(documents):
    """Use actual official links; missing expected editions stop preparation."""
    result = []
    for family, catalog in CATALOGS.items():
        parser = Links()
        parser.feed(documents[catalog].decode("utf-8", errors="strict"))
        links = {urljoin(catalog, href) for href in parser.hrefs}
        quarters = [(y, q) for y in range(2011, 2026) for q in range(1, 5)]
        prefix = "/files/dera/data/financial-statement-data-sets/"
        suffix = ".zip"
        if family == "SEC_13F":
            quarters = [(y, q) for y in range(2013, 2024) for q in range(1, 5)
                        if (y, q) >= (2013, 3)]
            prefix = "/files/structureddata/data/form-13f-data-sets/"
            suffix = "_form13f.zip"
        for year, quarter in quarters:
            filename = f"{year}q{quarter}{suffix}"
            matches = sorted(u for u in links if urlsplit(u).path == prefix + filename)
            if len(matches) != 1:
                raise ValueError(f"Expected one official catalog link: {family}/{filename}")
            result.append({"family": family, "edition": f"{year}Q{quarter}",
                           "url": official_url(matches[0]), "filename": filename,
                           "discovery_url": catalog})
    daily = {}
    for quarter, url in enumerate(DIRECTORIES, 1):
        listing = json.loads(documents[url])["directory"]
        for item in listing["item"]:
            name = item["name"]
            if not re.fullmatch(r"master\.2023[0-9]{4}\.idx", name):
                continue
            date = datetime.strptime(name[7:15], "%Y%m%d")
            if (date.month - 1) // 3 + 1 != quarter:
                raise ValueError("Daily filename/quarter mismatch")
            if name in daily:
                raise ValueError("Repeated daily delivery listing")
            daily[name] = {"family": "SEC_EDGAR_DAILY_MASTER", "edition": name[7:15],
                           "url": urljoin(url, name), "filename": name, "discovery_url": url}
    if len(daily) < 198:
        raise ValueError("Fewer than 198 published daily master indexes")
    result.extend(daily[name] for name in sorted(daily)[:198])
    for index, candidate in enumerate(result, 1):
        candidate.update(candidate_id=f"CAND{index:04d}", status="UNADMITTED_CANDIDATE",
                         real_or_controlled="REAL", source_instance_id=None)
    if (dict(Counter(c["family"] for c in result)) != EXPECTED_COUNTS
            or len({c["url"] for c in result}) != 300):
        raise ValueError("Approved candidate population mismatch")
    return result


def prepare(directory, fetcher):
    prepare_specification(directory)
    if (directory / "candidates.json").exists():
        return load_plan(directory)  # Offline verification; no rediscovery/replacement.
    captures, documents = {}, {}
    for url in [*CATALOGS.values(), *DIRECTORIES]:
        captures[url] = fetcher.fetch(url)
        documents[url] = verified_capture(directory, captures[url], url).read_bytes()
    plan = {"version": VERSION, "population": EXPECTED_COUNTS,
            "selection": "FSDS 2011Q1-2025Q4; 13F 2013Q3-2023Q4; first 198 2023 daily masters",
            "captures": captures, "candidates": select_candidates(documents),
            "admission_status": "NOT_ADMITTED", "cohort_status": "NOT_FROZEN",
            "parser_status": "NOT_APPROVED", "python_version": platform.python_version(),
            "tool_sha256": sha256_file(Path(__file__))}
    plan["plan_sha256"] = object_hash(plan)
    write_new(directory / "candidates.json", plan)
    return plan


def load_plan(directory):
    plan = json.loads((directory / "candidates.json").read_bytes())
    if (plan["version"] != VERSION or plan["plan_sha256"] != object_hash(
            {k: v for k, v in plan.items() if k != "plan_sha256"})):
        raise ValueError("Candidate plan hash/version mismatch")
    documents = {url: verified_capture(directory, plan["captures"][url], url).read_bytes()
                 for url in [*CATALOGS.values(), *DIRECTORIES]}
    if plan["candidates"] != select_candidates(documents):
        raise ValueError("Candidate plan differs from captured publisher evidence")
    return plan


def inspect_payload(path, filename):
    """Container integrity only; no parsing, extraction, semantic or header approval."""
    if filename.endswith(".zip"):
        members = []
        with ZipFile(path) as archive:
            for index, info in enumerate(archive.infolist()):
                if info.is_dir():
                    continue
                digest, size = hashlib.sha256(), 0
                with archive.open(info) as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
                        size += len(block)
                if size != info.file_size:
                    raise ValueError("ZIP member length mismatch")
                members.append({"member_index": index, "name": info.filename,
                                "bytes": size, "sha256": digest.hexdigest()})
        if not members:
            raise ValueError("ZIP contains no file members")
        return {"container_status": "PASS", "members": members,
                "uncompressed_bytes": sum(m["bytes"] for m in members)}
    with path.open("rb") as stream:
        prefix = stream.read(4096).lstrip().lower()
    if not prefix or b"<html" in prefix or b"<!doctype html" in prefix:
        raise ValueError("Empty or HTML payload instead of daily index")
    return {"container_status": "NOT_APPLICABLE", "members": [],
            "uncompressed_bytes": path.stat().st_size}


def acquired(directory, plan):
    results = {}
    for path in sorted(directory.glob("payload-*.json")):
        record = json.loads(path.read_bytes())
        if record["plan_sha256"] != plan["plan_sha256"]:
            raise ValueError("Payload evidence belongs to another candidate plan")
        candidate = next((c for c in plan["candidates"]
                          if c["candidate_id"] == record["candidate_id"]), None)
        if candidate is None or candidate["candidate_id"] in results:
            raise ValueError("Unknown or repeated candidate payload record")
        body = verified_capture(directory, record["capture"], candidate["url"])
        if record["inspection"] != inspect_payload(body, candidate["filename"]):
            raise ValueError("Payload inspection differs from retained evidence")
        results[candidate["candidate_id"]] = record
    return results


def download(directory, fetcher, *, limit=None, local_inventory=None):
    plan = load_plan(directory)
    completed = acquired(directory, plan)
    remaining = [c for c in plan["candidates"] if c["candidate_id"] not in completed]
    for candidate in remaining[:limit]:
        if local_inventory is not None:
            local = local_match(candidate, local_inventory)
            if local is not None:
                # Do not manufacture an HTTP receipt for an existing local delivery.
                print(json.dumps({"status": "ALREADY_AVAILABLE_LOCALLY", **local}), flush=True)
                continue
        capture = fetcher.fetch(candidate["url"])
        body = verified_capture(directory, capture, candidate["url"])
        try:
            inspection = inspect_payload(body, candidate["filename"])
        except (OSError, ValueError, BadZipFile, RuntimeError, NotImplementedError) as exc:
            write_new(body.parent / "inspection-failure.json", {
                "version": VERSION, "plan_sha256": plan["plan_sha256"],
                "candidate_id": candidate["candidate_id"], "capture": capture,
                "error": f"{type(exc).__name__}: {exc}", "status": "FAILED"})
            raise ValueError(f"Payload inspection failed; retained evidence: {body.parent}") from exc
        record = {"version": VERSION, "plan_sha256": plan["plan_sha256"],
                  "candidate_id": candidate["candidate_id"], "capture": capture,
                  "inspection": inspection,
                  "admission_status": "NOT_ADMITTED", "parser_status": "NOT_APPROVED"}
        write_new(directory / f"payload-{candidate['candidate_id']}.json", record)


def report(directory):
    plan = load_plan(directory)
    completed = acquired(directory, plan)
    hashes = defaultdict(list)
    for candidate_id, record in completed.items():
        hashes[record["capture"]["sha256"]].append(candidate_id)
    failures = []
    for path in sorted(directory.glob("attempts/*/receipt.json")):
        receipt = json.loads(path.read_bytes())
        if receipt["status"] != "COMPLETE":
            failures.append({"receipt": str(path.relative_to(directory)),
                             "url": receipt["requested_url"], "error": receipt.get("error")})
    return {"version": VERSION, "plan_sha256": plan["plan_sha256"],
            "candidate_counts": dict(Counter(c["family"] for c in plan["candidates"])),
            "candidate_count": 300, "acquired_count": len(completed),
            "pending_candidates": [c["candidate_id"] for c in plan["candidates"]
                                   if c["candidate_id"] not in completed],
            "equal_hash_review_groups": [ids for ids in hashes.values() if len(ids) > 1],
            "payload_bytes": sum(local_file(directory, r["capture"]["body"]).stat().st_size
                                 for r in completed.values()),
            "failed_requests": failures,
            "inspection_failures": [str(p.relative_to(directory)) for p in
                                    sorted(directory.glob("attempts/*/inspection-failure.json"))],
            "admitted_count": 0, "cohort_status": "NOT_FROZEN",
            "parser_status": "NOT_APPROVED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("spec", "prepare", "download", "report"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--directory", type=Path, default=Path("runs/c300/candidates-v1"))
    parser.add_argument("--limit", type=int, help="Maximum new payloads in this invocation")
    parser.add_argument("--local-inventory", type=Path,
                        default=Path("runs/local_inventory/availability.json"))
    args = parser.parse_args()
    try:
        directory = workspace(args.root, args.directory)
        if args.limit is not None and args.limit < 1:
            raise ValueError("--limit must be positive")
        if args.action == "spec":
            print(json.dumps(prepare_specification(directory), sort_keys=True))
            return 0
        if args.action == "prepare" and (directory / "candidates.json").exists():
            load_plan(directory)
        elif args.action != "report":
            fetcher = Fetcher(directory, os.environ.get("SEC_USER_AGENT"))
            if args.action == "prepare":
                prepare(directory, fetcher)
            else:
                inventory_path = args.local_inventory
                if not inventory_path.is_absolute():
                    inventory_path = args.root / inventory_path
                local_inventory = (load_availability(inventory_path)
                                   if inventory_path.exists() else None)
                if local_inventory is not None:
                    from edp_lab.ingestion.whole_lab import corpus_availability

                    local_inventory = corpus_availability(local_inventory, root=args.root)
                download(directory, fetcher, limit=args.limit, local_inventory=local_inventory)
        print(json.dumps(report(directory), sort_keys=True))
    except (OSError, ValueError, KeyError, BadZipFile, RuntimeError, NotImplementedError) as exc:
        parser.exit(1, f"FAIL {type(exc).__name__}: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
