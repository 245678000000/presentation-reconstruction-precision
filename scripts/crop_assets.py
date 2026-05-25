#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("deck_plan", type=Path)
    args = parser.parse_args()

    root = args.deck_plan.resolve().parent
    deck = load_json(args.deck_plan)
    written = []
    for slide in deck.get("slides", []):
        plan_path = root / slide["plan"]
        plan = load_json(plan_path)
        normalized = root / slide["normalized"]
        assets_dir = root / slide["assets_dir"]
        assets_dir.mkdir(parents=True, exist_ok=True)
        img = Image.open(normalized).convert("RGBA")
        for asset in plan.get("assets", []):
            if asset.get("type") != "crop":
                continue
            occ = asset.get("occlusion") or {}
            recovered = occ.get("recovered_file")
            if occ.get("status") == "recovered" and recovered:
                src = (plan_path.parent / recovered).resolve() if not Path(recovered).is_absolute() else Path(recovered)
                if src.exists():
                    out = assets_dir / (asset.get("file") or f"{asset.get('id')}.png")
                    shutil.copy2(src, out)
                    written.append(str(out))
                    continue
            crop = asset.get("crop", {})
            x = max(0, int(round(crop.get("x", 0))))
            y = max(0, int(round(crop.get("y", 0))))
            w = int(round(crop.get("w", 0)))
            h = int(round(crop.get("h", 0)))
            if w <= 0 or h <= 0:
                continue
            out = assets_dir / (asset.get("file") or f"{asset.get('id', 'asset')}.png")
            img.crop((x, y, min(img.width, x + w), min(img.height, y + h))).save(out)
            asset["file"] = out.name
            written.append(str(out))
        save_json(plan_path.parent / "layout_plan.resolved.json", plan)
        save_json(plan_path, plan)
    print(json.dumps({"written": written}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
