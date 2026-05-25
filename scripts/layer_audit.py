#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def box(el: Dict[str, Any]) -> Tuple[float, float, float, float] | None:
    if all(k in el for k in ("x", "y", "w", "h")):
        return (float(el["x"]), float(el["y"]), float(el["w"]), float(el["h"]))
    return None


def overlaps(a, b) -> bool:
    if not a or not b:
        return False
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def layer_map(deck: Dict[str, Any]) -> Dict[str, int]:
    policy = deck.get("layer_policy") or ["background", "fallback", "decor", "structure", "underlay_recovered", "media", "chart", "icon", "text", "annotation", "debug"]
    return {name: idx for idx, name in enumerate(policy)}


def order_key(el: Dict[str, Any], layers: Dict[str, int]):
    return (layers.get(el.get("layer", "media"), 99), float(el.get("z", 0) or 0))


def audit_plan(deck: Dict[str, Any], plan: Dict[str, Any], fix: bool) -> List[str]:
    layers = layer_map(deck)
    warnings: List[str] = []
    assets = {a.get("id"): a for a in plan.get("assets", [])}
    for el in plan.get("elements", []):
        t = el.get("type")
        if fix:
            if t == "fallback_image":
                el["layer"], el["z"] = "fallback", 0
            elif t in {"text", "rich_text"}:
                el.setdefault("layer", "text")
            elif t == "image" and assets.get(el.get("asset_id"), {}).get("occlusion", {}).get("status") == "recovered":
                el["layer"] = "underlay_recovered"
        if el.get("layer") not in layers:
            warnings.append(f"{plan.get('slide_id')}:{el.get('id')}: unknown layer {el.get('layer')}")
            if fix:
                el["layer"] = "media"
    elements = plan.get("elements", [])
    text_like = [e for e in elements if e.get("type") in {"text", "rich_text"} and not e.get("covered")]
    images = [e for e in elements if e.get("type") in {"image", "fallback_image"}]
    for txt in text_like:
        for img in images:
            if overlaps(box(txt), box(img)) and order_key(img, layers) > order_key(txt, layers):
                warnings.append(f"{plan.get('slide_id')}:{txt.get('id')} may be covered by {img.get('id')}")
    for asset in plan.get("assets", []):
        if asset.get("contains_text"):
            warnings.append(f"{plan.get('slide_id')}: asset {asset.get('id')} contains non-editable text")
        wants_background_cleanup = (asset.get("background_cleanup") or {}).get("enabled") is True
        background_status = (asset.get("background_cleanup") or {}).get("status")
        if wants_background_cleanup and background_status != "cleaned":
            warnings.append(f"{plan.get('slide_id')}: background asset {asset.get('id')} has not been separated from content")
        wants_transparent = asset.get("transparent") is True or asset.get("background_removal") is True or asset.get("asset_mode") in {"transparent", "transparent_subject"}
        transparency_status = (asset.get("transparency") or {}).get("status")
        if wants_transparent and transparency_status != "cleaned":
            warnings.append(f"{plan.get('slide_id')}: asset {asset.get('id')} is marked for transparency but has not been cleaned")
        if asset.get("contains_text") and transparency_status == "cleaned" and not asset.get("editable_text_overlay"):
            warnings.append(f"{plan.get('slide_id')}: transparent asset {asset.get('id')} contains text without an editable overlay flag")
    quality_mode = plan.get("quality_mode") or deck.get("quality_mode") or "balanced"
    if quality_mode != "visual_locked":
        meaningful = [e for e in elements if e.get("type") != "fallback_image" and e.get("editability") != "fallback"]
        structures = [e for e in elements if e.get("type") in {"rect", "round_rect", "circle", "line", "arrow", "table"}]
        has_large_fallback = False
        canvas = plan.get("canvas", {})
        area = float(canvas.get("width", 0) or 0) * float(canvas.get("height", 0) or 0)
        for el in elements:
            b = box(el)
            if el.get("type") == "fallback_image" and b and area and b[2] * b[3] >= area * 0.8:
                has_large_fallback = True
                break
        if len(meaningful) < 12:
            warnings.append(f"{plan.get('slide_id')}: low semantic split count ({len(meaningful)} non-fallback elements); likely too bitmap-heavy")
        if not text_like:
            warnings.append(f"{plan.get('slide_id')}: no editable text elements detected")
        if has_large_fallback and len(text_like) + len(structures) < 8:
            warnings.append(f"{plan.get('slide_id')}: full-slide fallback is still doing most of the reconstruction")
    image_pairs = [e for e in elements if e.get("type") == "image"]
    for img in image_pairs:
        asset = assets.get(img.get("asset_id"), {})
        is_bg = asset.get("asset_mode") in {"background_decor", "background_clean", "clean_background"} or asset.get("background_role") in {"decor", "background", "ornament"} or img.get("background_role") in {"decor", "background", "ornament"}
        if is_bg and img.get("layer") not in {"background", "decor"}:
            warnings.append(f"{plan.get('slide_id')}:{img.get('id')} background image should be on background/decor layer")
    for i, a in enumerate(image_pairs):
        for b in image_pairs[i + 1 :]:
            if overlaps(box(a), box(b)) and not a.get("occlusion_role") and not b.get("occlusion_role"):
                warnings.append(f"{plan.get('slide_id')}: overlapping images {a.get('id')} and {b.get('id')} lack occlusion_role")
    if fix:
        plan["elements"] = sorted(elements, key=lambda e: order_key(e, layers))
    return warnings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("deck_plan", type=Path)
    parser.add_argument("--fix-order", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = args.deck_plan.resolve().parent
    deck = load_json(args.deck_plan)
    warnings: List[str] = []
    for slide in deck.get("slides", []):
        plan_path = root / slide["plan"]
        plan = load_json(plan_path)
        warnings.extend(audit_plan(deck, plan, args.fix_order))
        if args.fix_order:
            save_json(plan_path, plan)
    result = {"ok": True, "warnings": warnings, "warning_count": len(warnings)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"warnings: {len(warnings)}")
        for item in warnings:
            print(f"WARN: {item}")


if __name__ == "__main__":
    main()
