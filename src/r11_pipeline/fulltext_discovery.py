"""Discover legitimate full-text candidates; never infer a screening decision.

Uses DOI-based OpenAlex and optionally Unpaywall. Never logs in, downloads
licensed documents, changes r11 evidence, or marks a paper as screened.
"""
from __future__ import annotations

import argparse
import csv
from difflib import SequenceMatcher
from html import unescape
import json
from pathlib import Path
import re
import sys
from time import sleep
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlsplit
from urllib.request import Request, urlopen

from .config import project_paths
from .project import Project


API_HOSTS = {"api.openalex.org", "api.unpaywall.org"}
PDF_NAMES = re.compile(r"^(?:record[_ -]?id[_ -]?|id[_ -]?)?0*([1-9]\d*)\.pdf$", re.I)
DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.I)


def clean_doi(raw):
    if not isinstance(raw, str):
        return ""
    return unquote(DOI_PREFIX.sub("", raw.strip())).strip()


def clean_title(title):
    value = unescape(unicodedata.normalize("NFKC", str(title or ""))).casefold()
    return " ".join(re.findall(r"\w+", value))


def title_matches(expected, found):
    if not found:
        return False
    a, b = clean_title(expected), clean_title(found)
    return bool(a and b) and (a == b or SequenceMatcher(None, a, b).ratio() >= 0.87)


def api_json(url, timeout=15):
    """Fetch JSON only from hard-coded scholarly APIs, never arbitrary URLs."""
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in API_HOSTS:
        raise ValueError("不允许访问非官方学术API地址")
    req = Request(url, headers={"Accept": "application/json",
                                "User-Agent": "building-literature-r11/0.1 (metadata discovery)"})
    try:
        with urlopen(req, timeout=timeout) as response:
            data = response.read(2_000_001)
    except HTTPError as error:
        if error.code == 404:
            return None
        raise RuntimeError(f"HTTP {error.code}") from error
    except (URLError, TimeoutError, OSError) as error:
        raise RuntimeError(type(error).__name__) from error
    if len(data) > 2_000_000:
        raise RuntimeError("API响应超过2MB")
    return json.loads(data)


def openalex(doi, client=api_json):
    url = "https://api.openalex.org/works/doi:" + quote(doi, safe="/")
    item = client(url)
    if not item:
        return None, []
    locations = []
    chosen = item.get("best_oa_location") or {}
    for location in [chosen] + (item.get("locations") or []):
        if not isinstance(location, dict) or not location.get("is_oa"):
            continue
        locations.append({"provider": "OpenAlex", "landing_url": location.get("landing_page_url"),
                          "pdf_url": location.get("pdf_url"), "license": location.get("license"),
                          "version": location.get("version")})
    return {"doi": clean_doi(item.get("doi")), "title": item.get("display_name", "")}, locations


def unpaywall(doi, email, client=api_json):
    url = "https://api.unpaywall.org/v2/" + quote(doi, safe="/") + "?email=" + quote(email, safe="")
    item = client(url)
    if not item:
        return None, []
    chosen = item.get("best_oa_location") or {}
    locations = []
    for location in [chosen] + (item.get("oa_locations") or []):
        if not isinstance(location, dict):
            continue
        locations.append({"provider": "Unpaywall",
                          "landing_url": location.get("url_for_landing_page") or location.get("url"),
                          "pdf_url": location.get("url_for_pdf"), "license": location.get("license"),
                          "version": location.get("version")})
    return {"doi": clean_doi(item.get("doi")), "title": item.get("title", "")}, locations


def safe_source(source):
    """Discard malformed or non-HTTPS links returned by outside APIs."""
    result = dict(source)
    for key in ("landing_url", "pdf_url"):
        url = result.get(key)
        if not isinstance(url, str) or urlsplit(url).scheme != "https" or not urlsplit(url).hostname:
            result[key] = None
    return result if result["landing_url"] or result["pdf_url"] else None


def pdf_index(folder):
    found = {}
    if not folder.is_dir():
        return found
    for path in sorted(folder.rglob("*.pdf")):
        match = PDF_NAMES.fullmatch(path.name)
        if match:
            found.setdefault(int(match.group(1)), []).append(path)
    return found


def pdf_probe(path):
    with path.open("rb") as file:
        head = file.read(5)
        file.seek(max(0, path.stat().st_size - 2048))
        tail = file.read()
    return {"path": str(path), "pdf_container_ok": head == b"%PDF-" and b"%%EOF" in tail,
            "identity_verified": False}


def discover_one(project, record_id, pdfs, email=None, client=api_json, pause=0):
    row = project.indexes[2][record_id][1]
    title, original_doi = row[1], row[2]
    doi = clean_doi(original_doi)
    report = {"record_id": record_id, "batch": row[17], "title": title, "doi": original_doi,
              "local_pdf_candidates": [], "oa_candidates": [], "identity_warnings": [], "errors": []}
    for file in pdfs.get(record_id, []):
        try:
            report["local_pdf_candidates"].append(pdf_probe(file))
        except OSError as error:
            report["errors"].append(f"本地PDF无法读取: {file.name} ({type(error).__name__})")
    if any(p["pdf_container_ok"] for p in report["local_pdf_candidates"]):
        report["status"] = "local_pdf_pending_identity_check"
        return report
    if not doi:
        report["status"] = "manual_access_needed"
        report["errors"].append("主表无DOI，需要人工根据题名和作者确认")
        return report
    if not doi.lower().startswith("10."):
        report["status"] = "manual_access_needed"
        report["errors"].append("DOI格式异常，需要人工核对")
        return report
    seen = set()
    providers = [("OpenAlex", lambda: openalex(doi, client))]
    if email:
        providers.append(("Unpaywall", lambda: unpaywall(doi, email, client)))
    for name, request in providers:
        try:
            metadata, candidates = request()
            if metadata:
                other_doi = clean_doi(metadata.get("doi"))
                if other_doi and other_doi.casefold() != doi.casefold():
                    report["identity_warnings"].append(f"{name} DOI不一致: {other_doi}")
                other_title = metadata.get("title")
                if other_title and not title_matches(title, other_title):
                    report["identity_warnings"].append(f"{name} 题名待核: {other_title}")
            for candidate in candidates:
                source = safe_source(candidate)
                if source:
                    key = (source["landing_url"], source["pdf_url"])
                    if key not in seen:
                        seen.add(key)
                        report["oa_candidates"].append(source)
        except (RuntimeError, ValueError, json.JSONDecodeError) as error:
            report["errors"].append(f"{name}: {error}")
        if pause:
            sleep(pause)
    report["status"] = ("oa_candidate_pending_verification" if report["oa_candidates"]
                        else "manual_access_needed")
    return report


def select_ids(project, args):
    if args.batch:
        return list(project.batches[args.batch])
    if args.ids:
        tokens = args.ids.split(",")
    elif args.ids_file:
        path = args.ids_file
        content = path.read_text(encoding="utf-8-sig")
        if path.suffix.lower() == ".json":
            value = json.loads(content)
            if isinstance(value, dict):
                value = next((value[key] for key in ("pending_ids", "needs_fulltext", "待核", "补证队列")
                              if isinstance(value.get(key), list)), None)
            if not isinstance(value, list):
                raise ValueError("JSON须为Record_ID数组或含pending_ids/needs_fulltext/待核/补证队列数组")
            tokens = [str(item["record_id"] if isinstance(item, dict) and "record_id" in item else item)
                      for item in value]
        else:
            tokens = [line.strip() for line in content.splitlines()
                      if line.strip() and not line.lstrip().startswith("#")]
    else:
        raise ValueError("必须指定 --batch、--ids 或 --ids-file 之一")
    selected, seen = [], set()
    for token in tokens:
        if not token.isdecimal():
            raise ValueError(f"非法Record_ID: {token}")
        record_id = int(token)
        if record_id not in project.indexes[2]:
            raise ValueError(f"Record_ID不在主表: {record_id}")
        if record_id not in seen:
            selected.append(record_id)
            seen.add(record_id)
    return selected


def write_reports(output, rows):
    csv_path = output.with_suffix(".csv")
    if output.exists() or csv_path.exists():
        raise FileExistsError("报告路径已存在；不会覆盖历史获取记录")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {"purpose": "fulltext-source-discovery-only", "rows": rows,
               "warning": "候选链接不等于真实全文；不得据此进行r11纳排，PDF须核对题名、DOI及原页"}
    with output.open("x", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")
    with csv_path.open("x", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["record_id", "batch", "title", "doi", "status",
                                                   "local_pdf", "candidate_pdf_urls",
                                                   "candidate_pages", "warnings", "errors"])
        writer.writeheader()
        for record in rows:
            writer.writerow({"record_id": record["record_id"], "batch": record["batch"],
                             "title": record["title"], "doi": record["doi"], "status": record["status"],
                             "local_pdf": " | ".join(p["path"] for p in record["local_pdf_candidates"]),
                             "candidate_pdf_urls": " | ".join(s["pdf_url"] for s in record["oa_candidates"] if s["pdf_url"]),
                             "candidate_pages": " | ".join(s["landing_url"] for s in record["oa_candidates"] if s["landing_url"]),
                             "warnings": " | ".join(record["identity_warnings"]),
                             "errors": " | ".join(record["errors"])})
    return csv_path


def main():
    parser = argparse.ArgumentParser(description="合法全文来源线索发现（不下载PDF、不执行r11筛选）")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--master", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--deliveries", type=Path)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--batch", type=int, choices=range(1, 19))
    selection.add_argument("--ids", help="逗号分隔Record_ID，例如1,12,256")
    selection.add_argument("--ids-file", type=Path, help="每行一个Record_ID，或JSON数组")
    parser.add_argument("--pdf-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="新建JSON报告路径，同时生成CSV")
    parser.add_argument("--email", help="可选：Unpaywall API所需联系邮箱（不会写入报告）")
    parser.add_argument("--limit", type=int, default=20, help="默认最多处理20篇，防止误扫897篇")
    parser.add_argument("--pause", type=float, default=0.5, help="每次API请求间隔秒数")
    args = parser.parse_args()
    if args.limit <= 0 or args.pause < 0:
        parser.error("--limit须为正整数，--pause须不小于0")
    try:
        project = Project(*project_paths(args, parser))
        ids = select_ids(project, args)
        if not ids:
            parser.error("未选择任何Record_ID")
        pdfs = pdf_index(args.pdf_dir)
        rows = [discover_one(project, record_id, pdfs, args.email, pause=args.pause)
                for record_id in ids[:args.limit]]
        csv_path = write_reports(args.output, rows)
        print(json.dumps({"checked": len(rows), "selected": len(ids), "remaining": ids[args.limit:],
                          "report_json": str(args.output), "report_csv": str(csv_path),
                          "local_pdf_candidates": sum(bool(r["local_pdf_candidates"]) for r in rows),
                          "oa_candidates": sum(bool(r["oa_candidates"]) for r in rows)},
                         ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        sys.exit(f"无法继续: {error}")


if __name__ == "__main__":
    main()
