#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Iterable, List

from PIL import Image, ImageOps


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
LAYER_POLICY = ["background", "fallback", "decor", "structure", "underlay_recovered", "media", "chart", "icon", "text", "annotation", "debug"]


def natural_key(path: Path):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", path.name)]


def discover(inputs: Iterable[str]) -> List[Path]:
    paths: List[Path] = []
    for raw in inputs:
        p = Path(raw)
        if p.is_dir():
            paths.extend(x for x in p.iterdir() if x.suffix.lower() in IMAGE_EXTS)
        elif p.exists() and p.suffix.lower() in IMAGE_EXTS:
            paths.append(p)
    return sorted(dict.fromkeys(paths), key=natural_key)


def normalize(src: Path, out: Path, max_width: int) -> tuple[int, int]:
    img = Image.open(src)
    img = ImageOps.exif_transpose(img).convert("RGB")
    if max_width and img.width > max_width:
        scale = max_width / img.width
        img = img.resize((max_width, round(img.height * scale)), Image.Resampling.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return img.width, img.height


def seed_plan(slide_id: str, width: int, height: int) -> dict:
    return {
        "version": "2.0",
        "slide_id": slide_id,
        "canvas": {"width": width, "height": height, "background": "#FFFFFF"},
        "assets": [
            {
                "id": "full_slide_fallback",
                "type": "crop",
                "source": "normalized.png",
                "crop": {"x": 0, "y": 0, "w": width, "h": height},
                "file": "full_slide_fallback.png",
                "contains_text": True,
                "reason": "conservative fallback seed",
            }
        ],
        "elements": [
            {
                "id": "full_slide_fallback",
                "type": "fallback_image",
                "asset_id": "full_slide_fallback",
                "x": 0,
                "y": 0,
                "w": width,
                "h": height,
                "layer": "fallback",
                "z": 0,
                "editability": "fallback",
                "shape_name": f"{slide_id}.fallback",
            }
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap a Presentation Reconstruction Pro workspace.")
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--work", type=Path, default=Path("work/presentation_reconstruction_pro"))
    parser.add_argument("--max-width", type=int, default=2400)
    parser.add_argument("--quality-mode", choices=["balanced", "max_editable", "visual_locked"], default="balanced")
    args = parser.parse_args()

    images = discover(args.inputs)
    if not images:
        raise SystemExit("No input images found.")

    args.work.mkdir(parents=True, exist_ok=True)
    slides = []
    canvas = None
    for i, src in enumerate(images, start=1):
        slide_id = f"slide_{i:02d}"
        slide_dir = args.work / "slides" / slide_id
        slide_dir.mkdir(parents=True, exist_ok=True)
        source = slide_dir / f"source{src.suffix.lower()}"
        shutil.copy2(src, source)
        normalized = slide_dir / "normalized.png"
        w, h = normalize(source, normalized, args.max_width)
        if canvas is None:
            canvas = {"width": w, "height": h, "aspect": f"{w}:{h}"}
        plan_path = slide_dir / "layout_plan.json"
        plan_path.write_text(json.dumps(seed_plan(slide_id, w, h), ensure_ascii=False, indent=2), encoding="utf-8")
        slides.append(
            {
                "id": slide_id,
                "source": str(source.relative_to(args.work)).replace("\\", "/"),
                "normalized": str(normalized.relative_to(args.work)).replace("\\", "/"),
                "plan": str(plan_path.relative_to(args.work)).replace("\\", "/"),
                "assets_dir": str((slide_dir / "assets").relative_to(args.work)).replace("\\", "/"),
                "recovery_dir": str((slide_dir / "recovery").relative_to(args.work)).replace("\\", "/"),
            }
        )

    deck = {
        "version": "2.0",
        "canvas": canvas,
        "quality_mode": args.quality_mode,
        "theme": {"font_family": "Microsoft YaHei", "colors": {"primary": "#003B91", "text": "#081B3A", "background": "#FFFFFF"}},
        "layer_policy": LAYER_POLICY,
        "slides": slides,
    }
    out = args.work / "deck_plan.json"
    out.write_text(json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
