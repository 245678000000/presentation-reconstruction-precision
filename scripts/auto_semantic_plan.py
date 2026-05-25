#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_tesseract(image: Path) -> List[Dict[str, Any]]:
    exe = shutil.which("tesseract")
    if not exe:
        return []
    with tempfile.TemporaryDirectory() as td:
        out_base = Path(td) / "ocr"
        cmd = [exe, str(image), str(out_base), "-l", "chi_sim+eng", "--psm", "6", "tsv"]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            return []
        tsv = out_base.with_suffix(".tsv")
        if not tsv.exists():
            return []
        rows = list(csv.DictReader(tsv.read_text(encoding="utf-8", errors="replace").splitlines(), delimiter="\t"))
    lines: Dict[tuple, List[Dict[str, Any]]] = {}
    for row in rows:
        text = (row.get("text") or "").strip()
        if not text:
            continue
        try:
            conf = float(row.get("conf", -1))
        except ValueError:
            conf = -1
        if conf >= 0 and conf < 35:
            continue
        key = (row.get("block_num"), row.get("par_num"), row.get("line_num"))
        lines.setdefault(key, []).append(row)
    observations = []
    for idx, words in enumerate(lines.values(), start=1):
        xs = [int(w["left"]) for w in words]
        ys = [int(w["top"]) for w in words]
        x2 = [int(w["left"]) + int(w["width"]) for w in words]
        y2 = [int(w["top"]) + int(w["height"]) for w in words]
        body = " ".join((w.get("text") or "").strip() for w in words).strip()
        if not body:
            continue
        observations.append(
            {
                "id": f"ocr_text_{idx:03d}",
                "kind": "text",
                "text": body,
                "bbox": {"x": min(xs), "y": min(ys), "w": max(x2) - min(xs), "h": max(y2) - min(ys)},
                "style": {"font_size": max(12, round((max(y2) - min(ys)) * 0.85)), "font_weight": 400, "color": "#111111"},
                "layer": "text",
                "confidence": 0.72,
                "needs_review": True,
                "source": "tesseract",
            }
        )
    return observations


def visual_regions(image: Path, max_regions: int = 24) -> List[Dict[str, Any]]:
    try:
        import numpy as np
    except Exception:
        return []
    img = Image.open(image).convert("RGB")
    scale = 0.25
    small = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
    arr = np.asarray(small).astype("int16")
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    saturation = mx - mn
    dark = mx < 180
    colored = saturation > 38
    nonwhite = mx < 242
    mask = (nonwhite & (dark | colored))
    h, w = mask.shape
    seen = np.zeros(mask.shape, dtype=bool)
    regions = []
    for y in range(h):
        for x in range(w):
            if seen[y, x] or not mask[y, x]:
                continue
            q = deque([(x, y)])
            seen[y, x] = True
            xs, ys = [], []
            while q:
                cx, cy = q.popleft()
                xs.append(cx)
                ys.append(cy)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny, nx] and mask[ny, nx]:
                        seen[ny, nx] = True
                        q.append((nx, ny))
            rx, ry, rx2, ry2 = min(xs), min(ys), max(xs) + 1, max(ys) + 1
            rw, rh = rx2 - rx, ry2 - ry
            area = rw * rh
            if area < 40 or rw < 4 or rh < 4:
                continue
            regions.append((area, rx, ry, rw, rh))
    regions = sorted(regions, reverse=True)[:max_regions]
    obs = []
    for idx, (_, x, y, w, h) in enumerate(regions, start=1):
        bbox = {"x": round(x / scale), "y": round(y / scale), "w": round(w / scale), "h": round(h / scale)}
        obs.append(
            {
                "id": f"visual_region_{idx:03d}",
                "kind": "image",
                "bbox": bbox,
                "layer": "media",
                "confidence": 0.55,
                "needs_review": True,
                "source": "heuristic_region",
            }
        )
    return obs


def main() -> None:
    parser = argparse.ArgumentParser(description="Create OCR/vision semantic annotation seeds for a deck.")
    parser.add_argument("deck_plan", type=Path)
    parser.add_argument("--no-merge", action="store_true")
    args = parser.parse_args()

    root = args.deck_plan.resolve().parent
    deck = load_json(args.deck_plan)
    for slide in deck.get("slides", []):
        normalized = root / slide["normalized"]
        slide_dir = (root / slide["plan"]).parent
        annotations = {
            "slide_id": slide["id"],
            "canvas": deck.get("canvas", {}),
            "observations": run_tesseract(normalized) + visual_regions(normalized),
        }
        save_json(slide_dir / "vision_annotations.auto.json", annotations)
    if not args.no_merge:
        merge = Path(__file__).resolve().parent / "merge_vision_annotations.py"
        subprocess.check_call([sys.executable, str(merge), str(args.deck_plan), "--auto-only"])
    print(args.deck_plan)


if __name__ == "__main__":
    main()
