# QA Checklist

## Before Generation

- `deck_plan.json` validates.
- Every slide has a plan and normalized source.
- OCR/vision annotations have been merged or explicitly skipped.
- Occlusion tasks are generated for overlapping lower images that need restoration.
- Recovered output files exist for tasks marked recovered.
- Decorative background crops are marked with `asset_mode: "background_decor"` and content masks when content is baked into the crop.
- Transparent-subject assets are marked with `asset_mode: "transparent_subject"` or are safe for auto cleanup.

## Visual Fidelity

- Generated previews are nonblank.
- Source and preview dimensions match.
- Main layout, margins, and titles align.
- Overlapped objects appear in the intended order.
- Recovered lower images do not show hard seams or obvious hallucinated text.
- Cleaned background assets do not contain readable ghost text, callout boxes, badges, or foreground icons.
- Transparent PNG assets do not show card borders, white/blue halos, or dirty crop backgrounds.

## Editability

- Main titles, bullets, callouts, cards, tables, and section headers are editable.
- Dense photos/logos/charts are assets.
- Shape names are useful in the PowerPoint selection pane.
- Assets containing text are reported unless editable overlays exist.
- Background decoration can be selected/moved independently from content objects.
- Standalone visual objects use transparent PNGs over native PPT cards when practical.

## Occlusion QA

- Lower object can be moved independently without exposing the original hidden hole.
- Upper object remains separately movable.
- Recovery mask corresponds only to the hidden region.
- If restoration would fabricate factual content, the task is flagged instead of completed.

## Correction Loop

1. Export previews.
2. Run `layer_audit.py`.
3. Inspect `_background_qa` mask previews.
4. Inspect `_transparent_qa` checkerboard previews.
5. Read `qa_report.md`.
6. Correct `layout_plan.json`, `vision_annotations.json`, background masks, transparent asset flags, or recovered assets.
7. Regenerate.
