#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Block strict PPT export while declared hidden-region recovery tasks remain incomplete.")
    parser.add_argument("deck_plan", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = args.deck_plan.resolve().parent
    source = root / "occlusion_tasks.json"
    report = json.loads(source.read_text(encoding="utf-8")) if source.exists() else {"tasks": [], "applied": []}
    pending = [task for task in report.get("tasks", []) if task.get("status") != "recovered"]
    summary = {"tasks": len(report.get("tasks", [])), "pending": len(pending), "results": pending}
    (root / "recovery_readiness_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"tasks: {summary['tasks']}; pending: {summary['pending']}")
    for task in pending:
        print(f"PENDING: {task.get('id')} -> {task.get('output_image')}")
    if args.strict and pending:
        sys.exit(2)


if __name__ == "__main__":
    main()
