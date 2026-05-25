#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def bbox(obs: Dict[str, Any]) -> Dict[str, float]:
    b = obs.get("bbox") or {}
    return {"x": b.get("x", 0), "y": b.get("y", 0), "w": b.get("w", 0), "h": b.get("h", 0)}


def existing_ids(plan: Dict[str, Any]) -> set:
    return {e.get("id") for e in plan.get("elements", [])} | {a.get("id") for a in plan.get("assets", [])}


def unique(base: str, ids: set) -> str:
    value = base
    i = 2
    while value in ids:
        value = f"{base}_{i}"
        i += 1
    ids.add(value)
    return value


def observations(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for path in paths:
        if path.exists():
            out.extend(load_json(path).get("observations", []))
    return out


def merge_obs(plan: Dict[str, Any], obs: Dict[str, Any], ids: set) -> None:
    kind = obs.get("kind")
    b = bbox(obs)
    base_id = str(obs.get("id") or f"{kind}_{len(ids)}").replace(" ", "_")
    eid = unique(base_id, ids)
    conf = float(obs.get("confidence", 1) or 1)
    needs_review = bool(obs.get("needs_review") or conf < 0.75)
    if kind == "text":
        style = obs.get("style") or {}
        plan.setdefault("elements", []).append(
            {
                "id": eid,
                "type": "text",
                "text": obs.get("text", ""),
                **b,
                "font_family": style.get("font_family", "Microsoft YaHei"),
                "font_size": style.get("font_size", 22),
                "font_weight": style.get("font_weight", 400),
                "color": style.get("color", "#111111"),
                "align": style.get("align", "left"),
                "valign": style.get("valign", "top"),
                "layer": obs.get("layer", "text"),
                "z": obs.get("z", 50),
                "editability": "editable",
                "shape_name": obs.get("shape_name", eid),
                "needs_review": needs_review,
            }
        )
    elif kind == "shape":
        style = obs.get("style") or {}
        shape = obs.get("shape", "rect")
        plan.setdefault("elements", []).append(
            {
                "id": eid,
                "type": "round_rect" if shape in {"round_rect", "rounded_rect", "panel"} else shape,
                **b,
                "rx": style.get("rx", 0),
                "fill": style.get("fill", "#FFFFFF"),
                "stroke": style.get("stroke", "none"),
                "stroke_width": style.get("stroke_width", 0),
                "layer": obs.get("layer", "structure"),
                "z": obs.get("z", 10),
                "editability": "editable",
                "shape_name": obs.get("shape_name", eid),
                "needs_review": needs_review,
            }
        )
    elif kind in {"image", "chart"}:
        aid = unique(f"{eid}_asset", ids)
        asset = {
            "id": aid,
            "type": "crop",
            "source": "normalized.png",
            "crop": b,
            "file": f"{aid}.png",
            "contains_text": bool(obs.get("contains_text") or kind == "chart"),
            "reason": obs.get("reason", f"{kind} crop from vision annotation"),
            "occlusion": {
                "status": "needs_recovery" if obs.get("needs_recovery") else "none",
                "hidden_by": obs.get("hidden_by", []),
            },
        }
        for key in ("asset_mode", "transparent", "background_removal", "remove_border", "transparent_threshold", "transparent_feather", "edge_clear_px", "editable_text_overlay"):
            if key in obs:
                asset[key] = obs[key]
        plan.setdefault("assets", []).append(asset)
        plan.setdefault("elements", []).append(
            {
                "id": eid,
                "type": "image",
                "asset_id": aid,
                **b,
                "layer": obs.get("layer", "media"),
                "z": obs.get("z", 20),
                "editability": "asset",
                "shape_name": obs.get("shape_name", eid),
                "occlusion_role": obs.get("occlusion_role", "none"),
                "needs_review": needs_review,
            }
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("deck_plan", type=Path)
    parser.add_argument("--auto-only", action="store_true")
    args = parser.parse_args()

    root = args.deck_plan.resolve().parent
    deck = load_json(args.deck_plan)
    for slide in deck.get("slides", []):
        plan_path = root / slide["plan"]
        slide_dir = plan_path.parent
        plan = load_json(plan_path)
        paths = [slide_dir / "vision_annotations.auto.json"]
        if not args.auto_only:
            paths.append(slide_dir / "vision_annotations.json")
        ids = existing_ids(plan)
        for obs in observations(paths):
            merge_obs(plan, obs, ids)
        save_json(plan_path, plan)
    print(args.deck_plan)


if __name__ == "__main__":
    main()
