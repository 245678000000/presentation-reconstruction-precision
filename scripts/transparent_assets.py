#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


POSITIVE_HINTS = {
    "arrow",
    "bacteria",
    "bottle",
    "device",
    "dryer",
    "fish",
    "freezer",
    "icon",
    "injection",
    "logo",
    "needle",
    "shield",
    "snow",
    "target",
    "thermometer",
    "truck",
    "vehicle",
    "vial",
}
NEGATIVE_HINTS = {
    "background",
    "card",
    "chart",
    "cluster_text",
    "full_slide",
    "map",
    "panel",
    "plot",
    "screenshot",
    "table",
    "wave",
}
PROTECTED_SUBJECT_MODES = {
    "light_subject",
    "preserve_tile",
    "translucent_subject",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def norm_text(asset: Dict[str, Any]) -> str:
    return " ".join(str(asset.get(k, "")).lower() for k in ("id", "reason", "role", "subject", "asset_mode"))


def should_process(asset: Dict[str, Any], mode: str) -> Tuple[bool, str]:
    if mode == "off":
        return False, "mode_off"
    if asset.get("subject_mode") in PROTECTED_SUBJECT_MODES and not asset.get("approved_transparency"):
        return False, "protected_light_or_translucent_subject"
    if asset.get("transparent") is False or asset.get("background_removal") is False:
        return False, "disabled"
    explicit = asset.get("transparent") is True or asset.get("background_removal") is True or asset.get("asset_mode") in {
        "transparent",
        "transparent_subject",
    }
    if explicit:
        return True, "explicit"
    if mode == "marked":
        return False, "not_marked"
    if asset.get("contains_text"):
        return False, "contains_text"
    text = norm_text(asset)
    if any(h in text for h in NEGATIVE_HINTS):
        return False, "negative_hint"
    if any(h in text for h in POSITIVE_HINTS):
        return True, "positive_hint"
    return False, "no_hint"


def border_background(arr: np.ndarray, edge: int) -> np.ndarray:
    h, w, _ = arr.shape
    edge = max(1, min(edge, h // 2 or 1, w // 2 or 1))
    samples = np.concatenate(
        [
            arr[:edge, :, :3].reshape(-1, 3),
            arr[h - edge :, :, :3].reshape(-1, 3),
            arr[:, :edge, :3].reshape(-1, 3),
            arr[:, w - edge :, :3].reshape(-1, 3),
        ],
        axis=0,
    )
    return np.median(samples, axis=0)


def connected_background(bg_candidate: np.ndarray) -> np.ndarray:
    h, w = bg_candidate.shape
    visited = np.zeros((h, w), dtype=bool)
    q: deque[Tuple[int, int]] = deque()
    for x in range(w):
        if bg_candidate[0, x]:
            visited[0, x] = True
            q.append((0, x))
        if bg_candidate[h - 1, x] and not visited[h - 1, x]:
            visited[h - 1, x] = True
            q.append((h - 1, x))
    for y in range(h):
        if bg_candidate[y, 0] and not visited[y, 0]:
            visited[y, 0] = True
            q.append((y, 0))
        if bg_candidate[y, w - 1] and not visited[y, w - 1]:
            visited[y, w - 1] = True
            q.append((y, w - 1))
    while q:
        y, x = q.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and bg_candidate[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))
    return visited


def remove_edge_lines(mask: np.ndarray, edge_band: int, min_ratio: float) -> np.ndarray:
    if edge_band <= 0:
        return mask
    h, w = mask.shape
    out = mask.copy()
    band = min(edge_band, h // 4 or 1, w // 4 or 1)
    for y in list(range(band)) + list(range(max(0, h - band), h)):
        if out[y, :].mean() > min_ratio:
            out[y, :] = False
    for x in list(range(band)) + list(range(max(0, w - band), w)):
        if out[:, x].mean() > min_ratio:
            out[:, x] = False
    return out


def open_edge_line_barriers(bg_candidate: np.ndarray, edge_band: int, min_ratio: float) -> np.ndarray:
    if edge_band <= 0:
        return bg_candidate
    h, w = bg_candidate.shape
    out = bg_candidate.copy()
    band = min(edge_band, h // 4 or 1, w // 4 or 1)
    for y in list(range(band)) + list(range(max(0, h - band), h)):
        if (~out[y, :]).mean() > min_ratio:
            out[y, :] = True
    for x in list(range(band)) + list(range(max(0, w - band), w)):
        if (~out[:, x]).mean() > min_ratio:
            out[:, x] = True
    return out


def checkerboard(size: Tuple[int, int], cell: int = 16) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, "#FFFFFF")
    draw = ImageDraw.Draw(img)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            fill = "#D9E3F2" if ((x // cell) + (y // cell)) % 2 else "#FFFFFF"
            draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=fill)
    return img


def add_safe_canvas_padding(img: Image.Image, padding: int) -> Image.Image:
    if padding <= 0:
        return img
    padded = Image.new("RGBA", (img.width + 2 * padding, img.height + 2 * padding), (0, 0, 0, 0))
    padded.paste(img, (padding, padding), img)
    return padded


def expand_image_placements(plan: Dict[str, Any], asset_id: str, original_size: Tuple[int, int], padding: int) -> None:
    if padding <= 0:
        return
    original_w, original_h = original_size
    if original_w <= 0 or original_h <= 0:
        return
    for element in plan.get("elements", []):
        if element.get("asset_id") != asset_id:
            continue
        if not all(key in element for key in ("x", "y", "w", "h")):
            continue
        dx = float(element["w"]) * padding / original_w
        dy = float(element["h"]) * padding / original_h
        element["x"] = float(element["x"]) - dx
        element["y"] = float(element["y"]) - dy
        element["w"] = float(element["w"]) + 2 * dx
        element["h"] = float(element["h"]) + 2 * dy


def transparentize(path: Path, threshold: float, feather: float, edge_clear: int, remove_border_lines: bool) -> Tuple[Image.Image, Dict[str, Any]]:
    img = Image.open(path).convert("RGBA")
    arr = np.array(img).astype(np.float32)
    h, w, _ = arr.shape
    bg = border_background(arr, edge=max(2, min(14, min(h, w) // 12 or 2)))
    dist = np.linalg.norm(arr[:, :, :3] - bg.reshape(1, 1, 3), axis=2)
    alpha = arr[:, :, 3]
    bg_candidate = (dist <= threshold) | (alpha <= 4)
    if remove_border_lines:
        bg_candidate = open_edge_line_barriers(bg_candidate, edge_clear, 0.55)
    bg_connected = connected_background(bg_candidate)
    foreground = (~bg_connected) & (alpha > 4)
    if remove_border_lines:
        foreground = remove_edge_lines(foreground, edge_clear, 0.55)

    mask = Image.fromarray((foreground.astype(np.uint8) * 255), mode="L")
    if feather > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=feather))
    out = img.copy()
    out.putalpha(mask)
    removed_ratio = float(bg_connected.sum()) / float(max(1, h * w))
    kept_ratio = float(foreground.sum()) / float(max(1, h * w))
    return out, {
        "background_rgb": [int(round(v)) for v in bg.tolist()],
        "removed_ratio": round(removed_ratio, 4),
        "kept_ratio": round(kept_ratio, 4),
        "threshold": threshold,
        "feather": feather,
    }


def process_slide(root: Path, slide: Dict[str, Any], mode: str, threshold: float, feather: float, edge_clear: int, force: bool) -> List[Dict[str, Any]]:
    plan_path = root / slide["plan"]
    plan = load_json(plan_path)
    assets_dir = root / slide["assets_dir"]
    qa_dir = assets_dir / "_transparent_qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    for asset in plan.get("assets", []):
        if asset.get("type") != "crop":
            continue
        ok, reason = should_process(asset, mode)
        if force and asset.get("type") == "crop":
            ok, reason = True, "force"
        if not ok:
            results.append({"asset_id": asset.get("id"), "status": "skipped", "reason": reason})
            continue
        source_file = assets_dir / (asset.get("file") or f"{asset.get('id', 'asset')}.png")
        if not source_file.exists():
            results.append({"asset_id": asset.get("id"), "status": "missing_file", "file": str(source_file)})
            continue
        remove_border = bool(asset.get("remove_border", True))
        try:
            out_img, stats = transparentize(
                source_file,
                threshold=float(asset.get("transparent_threshold", threshold)),
                feather=float(asset.get("transparent_feather", feather)),
                edge_clear=int(asset.get("edge_clear_px", edge_clear)),
                remove_border_lines=remove_border,
            )
        except Exception as exc:
            results.append({"asset_id": asset.get("id"), "status": "failed", "error": str(exc)})
            continue
        integrity = asset.get("integrity") or {}
        padding = int(asset.get("transparent_padding_px", integrity.get("min_clear_margin_px", 8)) or 0)
        original_size = out_img.size
        if padding > 0:
            out_img = add_safe_canvas_padding(out_img, padding)
            expand_image_placements(plan, str(asset.get("id")), original_size, padding)
            stats["transparent_padding_px"] = padding
        clean_name = f"{asset.get('id', source_file.stem)}_transparent.png"
        clean_file = assets_dir / clean_name
        out_img.save(clean_file)
        preview = checkerboard(out_img.size)
        preview.paste(out_img, (0, 0), out_img)
        preview_file = qa_dir / f"{asset.get('id', source_file.stem)}_preview.png"
        preview.save(preview_file)
        asset.setdefault("transparency", {})
        asset["transparency"].update({"status": "cleaned", "reason": reason, **stats, "preview": str(preview_file.relative_to(plan_path.parent)).replace("\\", "/")})
        asset.setdefault("original_file", asset.get("file"))
        asset["file"] = clean_name
        asset["transparent_file"] = clean_name
        results.append({"asset_id": asset.get("id"), "status": "cleaned", "reason": reason, **stats})
    save_json(plan_path, plan)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Create transparent PNG assets by removing border-connected background pixels.")
    parser.add_argument("deck_plan", type=Path)
    parser.add_argument("--mode", choices=["off", "marked", "auto"], default="auto", help="marked only processes assets explicitly tagged for transparency; auto also uses asset id/reason hints.")
    parser.add_argument("--threshold", type=float, default=42.0, help="RGB distance threshold for border-connected background removal.")
    parser.add_argument("--feather", type=float, default=0.65, help="Alpha edge blur radius.")
    parser.add_argument("--edge-clear", type=int, default=6, help="Band size for edge-line removal when remove_border is true.")
    parser.add_argument("--force", action="store_true", help="Process every crop asset regardless of hints. Use only for debugging.")
    args = parser.parse_args()

    root = args.deck_plan.resolve().parent
    deck = load_json(args.deck_plan)
    all_results: List[Dict[str, Any]] = []
    for slide in deck.get("slides", []):
        for result in process_slide(root, slide, args.mode, args.threshold, args.feather, args.edge_clear, args.force):
            result["slide_id"] = slide.get("id")
            all_results.append(result)
    summary = {
        "mode": args.mode,
        "processed": sum(1 for r in all_results if r.get("status") == "cleaned"),
        "skipped": sum(1 for r in all_results if r.get("status") == "skipped"),
        "results": all_results,
    }
    (root / "transparent_assets_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
