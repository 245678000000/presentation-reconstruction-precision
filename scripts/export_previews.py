#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def q(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pptx", type=Path)
    parser.add_argument("--out", type=Path, default=Path("work/presentation_reconstruction_pro/previews"))
    parser.add_argument("--width", type=int, default=1672)
    parser.add_argument("--height", type=int, default=941)
    args = parser.parse_args()

    pptx = args.pptx.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("*.png")) + list(out.glob("*.PNG")):
        try:
            old.unlink()
        except OSError:
            pass
    ps = f"""
$ErrorActionPreference = 'Stop'
$app = $null
$pres = $null
try {{
  $app = New-Object -ComObject PowerPoint.Application
  $pres = $app.Presentations.Open({q(str(pptx))}, $true, $false, $false)
  for ($i = 1; $i -le $pres.Slides.Count; $i++) {{
    $name = Join-Path {q(str(out))} ('slide_' + $i.ToString('00') + '.png')
    $pres.Slides.Item($i).Export($name, 'PNG', {args.width}, {args.height})
  }}
  $pres.Close()
  $app.Quit()
}} catch {{
  if ($pres) {{ $pres.Close() | Out-Null }}
  if ($app) {{ $app.Quit() | Out-Null }}
  Write-Output ('PREVIEW_EXPORT_UNAVAILABLE: ' + $_.Exception.Message)
}}
"""
    result = subprocess.run(["powershell", "-NoProfile", "-Command", ps], text=True, encoding="utf-8", errors="replace", capture_output=True)
    previews = [str(p) for p in sorted(set(out.glob("*.png")) | set(out.glob("*.PNG")))]
    messages = [line for line in (result.stdout or "").splitlines() if line.startswith("PREVIEW_EXPORT_UNAVAILABLE")]
    print(json.dumps({"ok": result.returncode == 0 and bool(previews), "previews": previews, "messages": messages}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
