#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def process_slide(root: Path, slide: Dict[str, Any]) -> List[Dict[str, Any]]:
    plan = load_json(root / slide["plan"])
    elements = {item.get("id") for item in plan.get("elements", [])}
    assets = {item.get("id") for item in plan.get("assets", [])}
    results: List[Dict[str, Any]] = []
    for component in plan.get("required_components", []):
        expected_elements = component.get("element_ids") or [component.get("element_id")]
        expected_elements = [value for value in expected_elements if value]
        expected_assets = component.get("asset_ids") or [component.get("asset_id")]
        expected_assets = [value for value in expected_assets if value]
        found_elements = [value for value in expected_elements if value in elements]
        found_assets = [value for value in expected_assets if value in assets]
        omitted = bool(component.get("approved_omission"))
        status = "pass" if found_elements or found_assets or omitted else "missing"
        results.append(
            {
                "slide_id": slide.get("id"),
                "component_id": component.get("id"),
                "status": status,
                "required": bool(component.get("required", True)),
                "expected_elements": expected_elements,
                "expected_assets": expected_assets,
                "found_elements": found_elements,
                "found_assets": found_assets,
                "note": component.get("note", ""),
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify required visual components were represented in the layout plan.")
    parser.add_argument("deck_plan", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = args.deck_plan.resolve().parent
    deck = load_json(args.deck_plan)
    results: List[Dict[str, Any]] = []
    for slide in deck.get("slides", []):
        results.extend(process_slide(root, slide))
    failures = [item for item in results if item.get("required") and item.get("status") == "missing"]
    summary = {"checked": len(results), "missing": len(failures), "results": results}
    (root / "component_recall_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"checked: {len(results)}; missing: {len(failures)}")
        for item in failures:
            print(f"FAIL: {item['slide_id']} missing required component {item['component_id']}")
    if args.strict and failures:
        sys.exit(2)


if __name__ == "__main__":
    main()
