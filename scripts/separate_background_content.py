#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from PIL import Image, ImageDraw, ImageFilter


BOX_TYPES = {"rect", "round_rect", "text", "rich_text", "image", "fallback_image", "table", "circle"}
LINE_TYPES = {"line", "arrow"}
DEFAULT_MASK_LAYERS = {"structure", "text", "icon", "annotation"}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def bbox(el: Dict[str, Any]) -> Tuple[float, float, float, float] | None:
    t = el.get("type")
    if t == "circle":
        r = float(el.get("r", 0) or 0)
        cx = float(el.get("cx", el.get("x", 0)) or 0)
        cy = float(el.get("cy", el.get("y", 0)) or 0)
        return (cx - r, cy - r, 2 * r, 2 * r)
    if t in BOX_TYPES and all(k in el for k in ("x", "y", "w", "h")):
        return (float(el["x"]), float(el["y"]), float(el["w"]), float(el["h"]))
    if t in LINE_TYPES:
        x1, y1, x2, y2 = [float(el.get(k, 0)) for k in ("x1", "y1", "x2", "y2")]
        return (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
    return None


def intersect(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> Tuple[float, float, float, float] | None:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    if x2 <= x1 or y2 <= y1:
        return None
    return (x1, y1, x2 - x1, y2 - y1)


def is_background_asset(asset: Dict[str, Any]) -> bool:
    return (
        asset.get("asset_mode") in {"background_decor", "background_clean", "clean_background"}
        or asset.get("background_role") in {"decor", "background", "ornament"}
        or (asset.get("background_cleanup") or {}).get("enabled") is True
    )


def candidate_elements(plan: Dict[str, Any], cleanup: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    ids = set(cleanup.get("erase_elements") or cleanup.get("mask_elements") or [])
    exclude = set(cleanup.get("exclude_elements") or [])
    auto = bool(cleanup.get("auto_mask", True))
    mask_layers = set(cleanup.get("mask_layers") or DEFAULT_MASK_LAYERS)
    for el in plan.get("elements", []):
        eid = el.get("id")
        if eid in exclude:
            continue
        if eid in ids:
            yield el
            continue
        if not auto:
            continue
        if el.get("background_role") in {"decor", "background", "ornament"}:
            continue
        if el.get("mask_as_background") is True:
            continue
        if el.get("mask_as_content") is True or el.get("layer") in mask_layers:
            yield el


def draw_mask(mask: Image.Image, rect: Tuple[float, float, float, float], padding: int) -> None:
    x, y, w, h = rect
    x1 = max(0, int(round(x - padding)))
    y1 = max(0, int(round(y - padding)))
    x2 = min(mask.width, int(round(x + w + padding)))
    y2 = min(mask.height, int(round(y + h + padding)))
    if x2 <= x1 or y2 <= y1:
        return
    ImageDraw.Draw(mask).rectangle((x1, y1, x2, y2), fill=255)


def build_content_mask(plan: Dict[str, Any], asset: Dict[str, Any], cleanup: Dict[str, Any]) -> Image.Image:
    crop = asset.get("crop", {})
    ax = float(crop.get("x", 0) or 0)
    ay = float(crop.get("y", 0) or 0)
    aw = int(round(float(crop.get("w", 0) or 0)))
    ah = int(round(float(crop.get("h", 0) or 0)))
    mask = Image.new("L", (max(1, aw), max(1, ah)), 0)
    asset_box = (ax, ay, float(aw), float(ah))
    padding = int(cleanup.get("padding", 10) or 0)
    for raw in cleanup.get("erase_rects", []) or []:
        rect = (
            float(raw.get("x", 0) or 0) - ax,
            float(raw.get("y", 0) or 0) - ay,
            float(raw.get("w", 0) or 0),
            float(raw.get("h", 0) or 0),
        )
        draw_mask(mask, rect, padding)
    for el in candidate_elements(plan, cleanup):
        b = bbox(el)
        if not b:
            continue
        hit = intersect(asset_box, b)
        if not hit:
            continue
        hx, hy, hw, hh = hit
        draw_mask(mask, (hx - ax, hy - ay, hw, hh), padding)
    blur_radius = float(cleanup.get("mask_blur", 2.0) or 0)
    if blur_radius > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))
    return mask


def inpaint_with_cv2(img: Image.Image, mask: Image.Image, radius: float) -> Image.Image | None:
    try:
        import cv2  # type: ignore
        import numpy as np
    except Exception:
        return None
    rgb = np.array(img.convert("RGB"))
    m = np.array(mask.convert("L"))
    result = cv2.inpaint(rgb, m, float(radius), cv2.INPAINT_TELEA)
    return Image.fromarray(result).convert("RGBA")


def fallback_fill(img: Image.Image, mask: Image.Image, radius: float) -> Image.Image:
    try:
        import numpy as np
    except Exception:
        base = img.convert("RGBA")
        soft_mask = mask.convert("L").filter(ImageFilter.GaussianBlur(max(2, radius)))
        blurred = base.filter(ImageFilter.GaussianBlur(max(8, radius * 5)))
        return Image.composite(blurred, base, soft_mask)

    base = img.convert("RGBA")
    arr = np.array(base).astype(np.float32)
    m = np.array(mask.convert("L")) > 0
    h, w = m.shape
    xgrid = np.arange(w)
    ygrid = np.arange(h)
    horizontal = arr.copy()
    vertical = arr.copy()
    for y in range(h):
        invalid = m[y]
        if not invalid.any():
            continue
        valid = ~invalid
        if valid.sum() < 2:
            continue
        for ch in range(4):
            horizontal[y, invalid, ch] = np.interp(xgrid[invalid], xgrid[valid], arr[y, valid, ch])
    for x in range(w):
        invalid = m[:, x]
        if not invalid.any():
            continue
        valid = ~invalid
        if valid.sum() < 2:
            continue
        for ch in range(4):
            vertical[invalid, x, ch] = np.interp(ygrid[invalid], ygrid[valid], arr[valid, x, ch])
    filled = arr.copy()
    filled[m] = horizontal[m] * 0.65 + vertical[m] * 0.35
    interp = Image.fromarray(np.clip(filled, 0, 255).astype("uint8"), "RGBA")
    soft_mask = mask.convert("L").filter(ImageFilter.GaussianBlur(max(1.5, radius / 2)))
    return Image.composite(interp, base, soft_mask)


def clean_background(asset_file: Path, mask: Image.Image, method: str, radius: float) -> Image.Image:
    img = Image.open(asset_file).convert("RGBA")
    if mask.size != img.size:
        mask = mask.resize(img.size)
    if method in {"auto", "cv2"}:
        out = inpaint_with_cv2(img, mask, radius)
        if out is not None:
            return out
        if method == "cv2":
            raise RuntimeError("cv2 is not available for inpainting")
    return fallback_fill(img, mask, radius)


def overlay_mask_preview(img: Image.Image, mask: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    red = Image.new("RGBA", img.size, (255, 0, 0, 96))
    return Image.alpha_composite(img, Image.composite(red, Image.new("RGBA", img.size, (0, 0, 0, 0)), mask.convert("L")))


def process_slide(root: Path, slide: Dict[str, Any], method: str, force: bool) -> List[Dict[str, Any]]:
    plan_path = root / slide["plan"]
    plan = load_json(plan_path)
    assets_dir = root / slide["assets_dir"]
    qa_dir = assets_dir / "_background_qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    for asset in plan.get("assets", []):
        cleanup = asset.get("background_cleanup") or {}
        if cleanup.get("enabled") is False:
            results.append({"asset_id": asset.get("id"), "status": "skipped_pure_background"})
            continue
        if not force and not is_background_asset(asset):
            continue
        if asset.get("type") != "crop":
            continue
        source_file = assets_dir / (asset.get("file") or f"{asset.get('id', 'asset')}.png")
        if not source_file.exists():
            results.append({"asset_id": asset.get("id"), "status": "missing_file", "file": str(source_file)})
            continue
        mask = build_content_mask(plan, asset, cleanup)
        if not mask.getbbox():
            results.append({"asset_id": asset.get("id"), "status": "no_mask"})
            continue
        clean_name = cleanup.get("file") or f"{asset.get('id', source_file.stem)}_background_clean.png"
        mask_name = f"{asset.get('id', source_file.stem)}_content_mask.png"
        preview_name = f"{asset.get('id', source_file.stem)}_mask_preview.png"
        radius = float(cleanup.get("inpaint_radius", 7.0) or 7.0)
        cleaned = clean_background(source_file, mask, method, radius)
        cleaned.save(assets_dir / clean_name)
        mask.save(qa_dir / mask_name)
        overlay_mask_preview(Image.open(source_file), mask).save(qa_dir / preview_name)
        asset.setdefault("original_file", asset.get("file"))
        asset["file"] = clean_name
        asset.setdefault("background_cleanup", {})
        asset["background_cleanup"].update(
            {
                "status": "cleaned",
                "method": method,
                "mask": str((qa_dir / mask_name).relative_to(plan_path.parent)).replace("\\", "/"),
                "preview": str((qa_dir / preview_name).relative_to(plan_path.parent)).replace("\\", "/"),
            }
        )
        results.append({"asset_id": asset.get("id"), "status": "cleaned", "mask_pixels": sum(1 for value in mask.getdata() if value)})
    save_json(plan_path, plan)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Separate decorative background assets from overlaid editable content by masking and cleaning content areas.")
    parser.add_argument("deck_plan", type=Path)
    parser.add_argument("--method", choices=["auto", "cv2", "blur"], default="auto")
    parser.add_argument("--force", action="store_true", help="Process every crop asset as a background asset. Use only for debugging.")
    args = parser.parse_args()

    root = args.deck_plan.resolve().parent
    deck = load_json(args.deck_plan)
    all_results: List[Dict[str, Any]] = []
    for slide in deck.get("slides", []):
        for result in process_slide(root, slide, args.method, args.force):
            result["slide_id"] = slide.get("id")
            all_results.append(result)
    summary = {
        "method": args.method,
        "cleaned": sum(1 for r in all_results if r.get("status") == "cleaned"),
        "results": all_results,
    }
    (root / "background_separation_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
