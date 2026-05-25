#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageDraw


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def box(el: Dict[str, Any]) -> Tuple[float, float, float, float]:
    return (float(el.get("x", 0)), float(el.get("y", 0)), float(el.get("w", 0)), float(el.get("h", 0)))


def intersect(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    if x2 <= x1 or y2 <= y1:
        return None
    return (x1, y1, x2 - x1, y2 - y1)


def layer_index(deck: Dict[str, Any]) -> Dict[str, int]:
    policy = deck.get("layer_policy") or ["background", "fallback", "decor", "structure", "underlay_recovered", "media", "chart", "icon", "text", "annotation", "debug"]
    return {name: i for i, name in enumerate(policy)}


def above(a: Dict[str, Any], b: Dict[str, Any], layers: Dict[str, int]) -> bool:
    la = layers.get(a.get("layer", "media"), 0)
    lb = layers.get(b.get("layer", "media"), 0)
    return (la, float(a.get("z", 0) or 0)) > (lb, float(b.get("z", 0) or 0))


def asset_map(plan: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {a.get("id"): a for a in plan.get("assets", [])}


def make_task(slide_id: str, lower: Dict[str, Any], upper: Dict[str, Any], overlap, normalized: Path, recovery_dir: Path) -> Dict[str, Any]:
    lx, ly, lw, lh = box(lower)
    ox, oy, ow, oh = overlap
    img = Image.open(normalized).convert("RGBA")
    partial = img.crop((round(lx), round(ly), round(lx + lw), round(ly + lh)))
    mask = Image.new("L", (round(lw), round(lh)), 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle((round(ox - lx), round(oy - ly), round(ox - lx + ow), round(oy - ly + oh)), fill=255)
    task_id = f"{slide_id}__{lower['id']}__covered_by__{upper['id']}".replace(".", "_")
    recovery_dir.mkdir(parents=True, exist_ok=True)
    input_image = recovery_dir / f"{task_id}_partial.png"
    mask_image = recovery_dir / f"{task_id}_mask.png"
    output_image = recovery_dir / f"{task_id}_recovered.png"
    partial.save(input_image)
    mask.save(mask_image)
    return {
        "id": task_id,
        "slide_id": slide_id,
        "lower_element_id": lower["id"],
        "upper_element_id": upper["id"],
        "input_image": str(input_image),
        "mask_image": str(mask_image),
        "output_image": str(output_image),
        "prompt": "Restore the masked hidden part of the lower image so it continues naturally behind the foreground object. Preserve lighting, perspective, texture, style, and avoid inventing readable text or factual chart data.",
        "recovery_mode": "image_edit",
        "content_safety": "non_factual_visual",
        "validation_required": True,
        "status": "recovered" if output_image.exists() else "needs_recovery",
    }


def apply_recovered(task: Dict[str, Any], plan: Dict[str, Any], plan_path: Path, assets_dir: Path) -> bool:
    out = Path(task["output_image"])
    if not out.exists():
        return False
    elements = {e.get("id"): e for e in plan.get("elements", [])}
    lower = elements.get(task["lower_element_id"])
    if not lower:
        return False
    assets = asset_map(plan)
    asset = assets.get(lower.get("asset_id"))
    if not asset:
        return False
    recovered_name = f"{asset['id']}_recovered.png"
    assets_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out, assets_dir / recovered_name)
    asset["file"] = recovered_name
    asset.setdefault("occlusion", {})["status"] = "recovered"
    asset["occlusion"]["recovered_file"] = str(out.relative_to(plan_path.parent)).replace("\\", "/") if out.is_relative_to(plan_path.parent) else str(out)
    lower["layer"] = "underlay_recovered"
    lower["occlusion_role"] = "lower"
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate masks/tasks for overlapped lower image recovery and apply recovered outputs when present.")
    parser.add_argument("deck_plan", type=Path)
    args = parser.parse_args()

    root = args.deck_plan.resolve().parent
    deck = load_json(args.deck_plan)
    layers = layer_index(deck)
    all_tasks = []
    applied = []
    for slide in deck.get("slides", []):
        plan_path = root / slide["plan"]
        plan = load_json(plan_path)
        normalized = root / slide["normalized"]
        recovery_dir = root / slide.get("recovery_dir", str(plan_path.parent / "recovery"))
        assets_dir = root / slide["assets_dir"]
        elems = [e for e in plan.get("elements", []) if e.get("type") == "image"]
        tasks: List[Dict[str, Any]] = []
        assets = asset_map(plan)
        for lower in elems:
            lower_asset = assets.get(lower.get("asset_id"), {})
            lower_occ = lower_asset.get("occlusion") or {}
            explicit_recovery = lower.get("occlusion_role") == "lower" or lower_occ.get("status") == "needs_recovery" or bool(lower_occ.get("hidden_by"))
            if not explicit_recovery:
                continue
            for upper in elems:
                if lower is upper or not above(upper, lower, layers):
                    continue
                overlap = intersect(box(lower), box(upper))
                if not overlap:
                    continue
                task = make_task(slide["id"], lower, upper, overlap, normalized, recovery_dir)
                tasks.append(task)
                asset = assets.get(lower.get("asset_id"))
                if asset:
                    asset.setdefault("occlusion", {})
                    asset["occlusion"].update({"status": task["status"], "hidden_by": [upper["id"]]})
                if apply_recovered(task, plan, plan_path, assets_dir):
                    applied.append(task["id"])
        save_json(recovery_dir / "occlusion_tasks.json", {"slide_id": slide["id"], "tasks": tasks})
        save_json(plan_path, plan)
        all_tasks.extend(tasks)
    save_json(root / "occlusion_tasks.json", {"tasks": all_tasks, "applied": applied})
    print(json.dumps({"tasks": len(all_tasks), "applied": applied}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
