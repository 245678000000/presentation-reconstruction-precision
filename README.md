# Presentation Reconstruction Precision

Presentation Reconstruction Precision is a Codex skill and Python utility set for rebuilding image-based presentation pages into clean, editable PowerPoint decks.

It is designed for cases where a prior image-to-PPT conversion left clipped assets, missing icons, dirty shadows, fused backgrounds, or partially hidden visual objects. The workflow favors editable native PowerPoint shapes where possible, keeps background art separate from foreground content, and runs strict checks before delivery.

## Features

- Reconstruct slide screenshots and exported deck images into editable PPTX files.
- Separate decorative backgrounds from cards, text, icons, photos, charts, and callouts.
- Preserve factual or dense media as rectangular images instead of unsafe transparent cutouts.
- Generate transparent foreground assets with padding and edge-touch integrity checks.
- Audit required component recall so small visible labels and icons are not silently omitted.
- Flag recoverable hidden regions while preventing invented chart data, text, values, or logos.

## Repository Layout

```text
.
├── SKILL.md                  # Codex skill instructions
├── agents/openai.yaml        # Skill display metadata
├── references/               # Reconstruction contracts and schemas
├── scripts/                  # Pipeline and QA utilities
└── requirements.txt          # Python runtime dependencies
```

## Installation

Install the Python dependencies in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

To use it as a Codex skill, place this repository under your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R presentation-reconstruction-precision ~/.codex/skills/
```

Restart Codex after adding the skill so it can be discovered.

## Basic Usage

Create or bootstrap a semantic deck plan, then run the pipeline:

```bash
python scripts/run_pipeline.py work/deck_plan.json \
  --skip-auto-plan \
  --transparent-mode marked \
  --strict-integrity \
  --out work/reconstructed.pptx
```

The expected planning format is documented in `references/deck_schema.md`. The stricter visual QA expectations are documented in `references/precision_qa_contract.md`.

## Typical Workflow

1. Build `deck_plan.json` and per-slide `layout_plan.json`.
2. Populate `required_components` for every visible text, icon, chart, callout, and important visual block.
3. Mark background art as `background_decor`.
4. Mark foreground assets by role, such as `opaque_icon`, `translucent_subject`, `photo_rect`, or `native_rebuild`.
5. Run the reconstruction pipeline.
6. Inspect previews, checkerboards, mask outputs, recall reports, and integrity reports.
7. Regenerate until strict QA passes or the remaining limitation is explicitly documented.

## License

This project is released under the MIT License. See `LICENSE` for details.
