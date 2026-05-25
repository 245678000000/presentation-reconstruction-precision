#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

from PIL import Image, ImageChops, ImageStat


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rms(a: Path, b: Path) -> float | None:
    if not a.exists() or not b.exists():
        return None
    im1 = Image.open(a).convert("RGB")
    im2 = Image.open(b).convert("RGB").resize(im1.size)
    diff = ImageChops.difference(im1, im2)
    stat = ImageStat.Stat(diff)
    return math.sqrt(sum(v * v for v in stat.rms))


def run_json(script: Path, deck_plan: Path) -> Dict:
    result = subprocess.run([sys.executable, str(script), str(deck_plan), "--json"], text=True, capture_output=True)
    if result.stdout.strip():
        return json.loads(result.stdout)
    return {"ok": result.returncode == 0, "warnings": [], "stderr": result.stderr}


def previews(path: Path) -> List[Path]:
    if not path.exists():
        return []
    return sorted(set(path.glob("*.png")) | set(path.glob("*.PNG")))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("deck_plan", type=Path)
    parser.add_argument("--pptx", type=Path, default=Path("work/presentation_reconstruction_pro/reconstructed.pptx"))
    parser.add_argument("--previews", type=Path, default=Path("work/presentation_reconstruction_pro/previews"))
    parser.add_argument("--out", type=Path, default=Path("work/presentation_reconstruction_pro/qa_report.md"))
    args = parser.parse_args()

    root = args.deck_plan.resolve().parent
    skill = Path(__file__).resolve().parents[1]
    deck = load_json(args.deck_plan)
    audit = run_json(skill / "scripts" / "layer_audit.py", args.deck_plan)
    preview_files = previews(args.previews.resolve())
    occlusion = load_json(root / "occlusion_tasks.json") if (root / "occlusion_tasks.json").exists() else {"tasks": [], "applied": []}
    background = load_json(root / "background_separation_report.json") if (root / "background_separation_report.json").exists() else {"cleaned": 0, "results": []}
    transparency = load_json(root / "transparent_assets_report.json") if (root / "transparent_assets_report.json").exists() else {"processed": 0, "skipped": 0, "results": []}
    integrity = load_json(root / "asset_integrity_report.json") if (root / "asset_integrity_report.json").exists() else {"checked": 0, "edge_risks": 0, "required_failures": 0, "results": []}
    recall = load_json(root / "component_recall_report.json") if (root / "component_recall_report.json").exists() else {"checked": 0, "missing": 0, "results": []}
    lines = ["# Presentation Reconstruction Precision QA Report", ""]
    lines += [
        "## Files",
        f"- deck_plan.json: {'OK' if args.deck_plan.exists() else 'MISSING'}",
        f"- reconstructed.pptx: {'OK' if args.pptx.exists() else 'MISSING'}",
        f"- previews: {len(preview_files)}",
        "",
        "## Layer Audit",
        f"- Warnings: {len(audit.get('warnings', []))}",
    ]
    for item in audit.get("warnings", [])[:60]:
        lines.append(f"- WARN: {item}")
    lines += [
        "",
        "## Occlusion Recovery",
        f"- Tasks: {len(occlusion.get('tasks', []))}",
        f"- Applied recovered assets: {len(occlusion.get('applied', []))}",
    ]
    for task in occlusion.get("tasks", [])[:30]:
        lines.append(f"- {task.get('id')}: {task.get('status')} -> {task.get('output_image')}")
    lines += [
        "",
        "## Component Recall",
        f"- Checked components: {recall.get('checked', 0)}",
        f"- Missing required components: {recall.get('missing', 0)}",
    ]
    for item in [r for r in recall.get("results", []) if r.get("status") == "missing"][:30]:
        lines.append(f"- MISSING: {item.get('slide_id')}:{item.get('component_id')}")
    lines += [
        "",
        "## Background Separation",
        f"- Cleaned backgrounds: {background.get('cleaned', 0)}",
    ]
    for item in [r for r in background.get("results", []) if r.get("status") == "cleaned"][:40]:
        lines.append(f"- {item.get('slide_id')}:{item.get('asset_id')} cleaned; mask_pixels={item.get('mask_pixels')}")
    lines += [
        "",
        "## Transparent Assets",
        f"- Cleaned assets: {transparency.get('processed', 0)}",
        f"- Skipped assets: {transparency.get('skipped', 0)}",
    ]
    for item in [r for r in transparency.get("results", []) if r.get("status") == "cleaned"][:40]:
        lines.append(f"- {item.get('slide_id')}:{item.get('asset_id')} cleaned ({item.get('reason')}); removed={item.get('removed_ratio')}, kept={item.get('kept_ratio')}")
    lines += [
        "",
        "## Foreground Integrity",
        f"- Checked assets: {integrity.get('checked', 0)}",
        f"- Edge-contact risks: {integrity.get('edge_risks', 0)}",
        f"- Required failures: {integrity.get('required_failures', 0)}",
    ]
    for item in [r for r in integrity.get("results", []) if r.get("status") == "edge_risk"][:30]:
        lines.append(f"- RISK: {item.get('slide_id')}:{item.get('asset_id')} touches {','.join(item.get('touched_sides', []))}")
    lines += ["", "## Slides"]
    for idx, slide in enumerate(deck.get("slides", [])):
        plan_path = root / slide["plan"]
        plan = load_json(plan_path)
        source = root / slide["normalized"]
        diff = rms(source, preview_files[idx]) if idx < len(preview_files) else None
        text_count = sum(1 for e in plan.get("elements", []) if e.get("type") in {"text", "rich_text"})
        image_count = sum(1 for e in plan.get("elements", []) if e.get("type") in {"image", "fallback_image"})
        recovered_count = sum(1 for a in plan.get("assets", []) if (a.get("occlusion") or {}).get("status") == "recovered")
        background_count = sum(1 for a in plan.get("assets", []) if (a.get("background_cleanup") or {}).get("status") == "cleaned")
        transparent_count = sum(1 for a in plan.get("assets", []) if (a.get("transparency") or {}).get("status") == "cleaned")
        diff_text = "unavailable" if diff is None else f"{diff:.2f}"
        lines.append(f"- {slide['id']}: elements={len(plan.get('elements', []))}, text={text_count}, images={image_count}, cleaned_backgrounds={background_count}, transparent_assets={transparent_count}, recovered_assets={recovered_count}, preview_rms={diff_text}")
    lines += [
        "",
        "## Notes",
        "- Move `bg.*` background objects independently to confirm no content text, cards, or icons move with them.",
        "- Inspect `_background_qa` previews for content masks and ghost text remnants.",
        "- Move recovered lower images independently in PowerPoint to confirm no hidden hole is exposed.",
        "- Inspect `_transparent_qa` previews for white/blue halos, card borders, or clipped subject edges.",
        "- Treat native structure objects as no-shadow unless the layout plan explicitly requests a design effect.",
        "- Do not deliver when required component recall or required foreground integrity fails.",
        "- Use image restoration only for non-factual visual texture, not hidden readable text or chart data.",
        "- Add editable overlays for text inside image assets whenever possible.",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
