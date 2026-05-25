#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def alpha_margins(path: Path, alpha_threshold: int = 16) -> Dict[str, Any] | None:
    image = Image.open(path).convert("RGBA")
    alpha = image.getchannel("A").point(lambda value: 255 if value > alpha_threshold else 0)
    box = alpha.getbbox()
    if not box:
        return None
    w, h = image.size
    return {
        "size": [w, h],
        "alpha_bbox": list(box),
        "margins": {
            "left": box[0],
            "top": box[1],
            "right": w - box[2],
            "bottom": h - box[3],
        },
    }


def file_for_asset(assets_dir: Path, asset: Dict[str, Any]) -> Path | None:
    name = asset.get("transparent_file") or asset.get("file")
    if not name:
        return None
    path = assets_dir / name
    return path if path.exists() else None


def process_slide(root: Path, slide: Dict[str, Any]) -> List[Dict[str, Any]]:
    plan = load_json(root / slide["plan"])
    assets_dir = root / slide["assets_dir"]
    results: List[Dict[str, Any]] = []
    for asset in plan.get("assets", []):
        transparency = asset.get("transparency") or {}
        if transparency.get("status") != "cleaned" and asset.get("asset_mode") != "transparent_subject":
            continue
        integrity = asset.get("integrity") or {}
        required = bool(integrity.get("required", False))
        allowed = set(integrity.get("allow_edge_touch") or [])
        min_margin = int(integrity.get("min_clear_margin_px", 8) or 0)
        file = file_for_asset(assets_dir, asset)
        if not file:
            results.append(
                {
                    "slide_id": slide.get("id"),
                    "asset_id": asset.get("id"),
                    "status": "missing",
                    "required": required,
                    "message": "foreground output file is missing",
                }
            )
            continue
        bounds = alpha_margins(file)
        if not bounds:
            results.append(
                {
                    "slide_id": slide.get("id"),
                    "asset_id": asset.get("id"),
                    "status": "empty",
                    "required": required,
                    "file": str(file),
                    "message": "transparent output has no visible subject pixels",
                }
            )
            continue
        touched = [
            side
            for side, gap in bounds["margins"].items()
            if side not in allowed and gap < min_margin
        ]
        status = "edge_risk" if touched else "pass"
        results.append(
            {
                "slide_id": slide.get("id"),
                "asset_id": asset.get("id"),
                "status": status,
                "required": required,
                "file": str(file),
                "min_clear_margin_px": min_margin,
                "touched_sides": touched,
                **bounds,
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit transparent foreground assets for crop-edge clipping risks.")
    parser.add_argument("deck_plan", type=Path)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when a required foreground fails.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = args.deck_plan.resolve().parent
    deck = load_json(args.deck_plan)
    results: List[Dict[str, Any]] = []
    for slide in deck.get("slides", []):
        results.extend(process_slide(root, slide))
    failures = [
        item
        for item in results
        if item.get("required") and item.get("status") in {"edge_risk", "missing", "empty"}
    ]
    risks = [item for item in results if item.get("status") == "edge_risk"]
    summary = {
        "checked": len(results),
        "edge_risks": len(risks),
        "required_failures": len(failures),
        "results": results,
    }
    (root / "asset_integrity_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"checked: {len(results)}; edge risks: {len(risks)}; required failures: {len(failures)}")
        for item in failures:
            print(f"FAIL: {item['slide_id']}:{item['asset_id']} touches {','.join(item.get('touched_sides', []))}")
    if args.strict and failures:
        sys.exit(2)


if __name__ == "__main__":
    main()

