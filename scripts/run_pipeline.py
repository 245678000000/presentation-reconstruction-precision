#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd):
    print("+", " ".join(map(str, cmd)))
    subprocess.check_call([sys.executable, *map(str, cmd)])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("deck_plan", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--skip-auto-plan", action="store_true")
    parser.add_argument("--skip-background-separation", action="store_true")
    parser.add_argument("--background-method", choices=["auto", "cv2", "blur"], default="auto")
    parser.add_argument("--skip-transparent-assets", action="store_true")
    parser.add_argument("--transparent-mode", choices=["off", "marked", "auto"], default="auto")
    parser.add_argument("--strict-integrity", action="store_true", help="Fail when required components are missing or required foreground assets touch crop edges.")
    parser.add_argument("--skip-preview", action="store_true")
    args = parser.parse_args()

    scripts = Path(__file__).resolve().parent
    root = args.deck_plan.resolve().parent
    out = args.out or (root / "reconstructed.pptx")
    if not args.skip_auto_plan:
        run([scripts / "auto_semantic_plan.py", args.deck_plan])
    component_cmd = [scripts / "component_recall_audit.py", args.deck_plan]
    if args.strict_integrity:
        component_cmd.append("--strict")
    run(component_cmd)
    run([scripts / "occlusion_recovery.py", args.deck_plan])
    recovery_cmd = [scripts / "recovery_readiness_audit.py", args.deck_plan]
    if args.strict_integrity:
        recovery_cmd.append("--strict")
    run(recovery_cmd)
    run([scripts / "layer_audit.py", args.deck_plan, "--fix-order"])
    run([scripts / "crop_assets.py", args.deck_plan])
    if not args.skip_background_separation:
        run([scripts / "separate_background_content.py", args.deck_plan, "--method", args.background_method])
        run([scripts / "layer_audit.py", args.deck_plan, "--fix-order"])
    if not args.skip_transparent_assets and args.transparent_mode != "off":
        run([scripts / "transparent_assets.py", args.deck_plan, "--mode", args.transparent_mode])
        run([scripts / "layer_audit.py", args.deck_plan, "--fix-order"])
    integrity_cmd = [scripts / "asset_integrity_audit.py", args.deck_plan]
    if args.strict_integrity:
        integrity_cmd.append("--strict")
    run(integrity_cmd)
    run([scripts / "deck_to_pptx.py", args.deck_plan, "--out", out])
    if not args.skip_preview:
        run([scripts / "export_previews.py", out, "--out", root / "previews"])
    run([scripts / "qa_report.py", args.deck_plan, "--pptx", out, "--previews", root / "previews", "--out", root / "qa_report.md"])
    print(out)


if __name__ == "__main__":
    main()
