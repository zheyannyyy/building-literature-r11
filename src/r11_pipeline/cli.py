"""Plan, checkpoint and export the project's V2.1-r11 screening records."""
import argparse
import json
from pathlib import Path
import sys

from .config import project_paths
from .evidence import save
from .extraction import paper_draft
from .project import Project, batch_validation, manifest, plan
from .reporting import export_batch, merge
from .retrieval import fetch_pdf


def main(only=None):
    descriptions = {
        "draft": "为下一篇文献生成未填写的证据 JSON 草稿。",
        "validate": "核对指定批次的逐篇证据或已交付工作簿。",
    }
    parser = argparse.ArgumentParser(description=descriptions.get(only, __doc__))
    parser.add_argument("--config", type=Path)
    parser.add_argument("--master", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--deliveries", type=Path)
    if only == "validate":
        parser.add_argument("--batch", type=int, choices=range(1, 19), required=True)
    elif only != "draft":
        commands = parser.add_subparsers(dest="command", required=True)
        if only is None:
            commands.add_parser("plan")
            commands.add_parser("manifest")
            commands.add_parser("save").add_argument("draft", type=Path)
            fetch = commands.add_parser("fetch-pdf")
            fetch.add_argument("url")
            fetch.add_argument("--output", type=Path, required=True)
        export = commands.add_parser("export")
        export.add_argument("--batch", type=int, choices=range(1, 19), required=True)
        export.add_argument("--snapshot", action="store_true")
        master = commands.add_parser("merge")
        master.add_argument("--through", type=int, choices=range(1, 19), required=True)
        master.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    command = getattr(args, "command", None)
    if command == "fetch-pdf":
        print(json.dumps(fetch_pdf(args.url, args.output), ensure_ascii=False, indent=2))
        return
    project = Project(*project_paths(args, parser))
    if only == "draft":
        result = paper_draft(project)
    elif only == "validate":
        result = batch_validation(project, args.batch)
    elif args.command == "plan":
        result = plan(project)
    elif args.command == "manifest":
        result = manifest(project)
    elif args.command == "save":
        result = save(project, args.draft)
    elif args.command == "export":
        result = export_batch(project, args.batch, args.snapshot)
    else:
        result = merge(project, args.through, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def run_cli(only=None):
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        main(only)
    except (ValueError, KeyError, TypeError, OSError, IndexError) as error:
        sys.exit(f"无法继续：{error}")
