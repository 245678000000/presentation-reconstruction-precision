---
name: presentation-reconstruction-precision
description: Reconstruct slide screenshots, exported PPT images, academic presentation pages, and layered visual mockups into clean editable PowerPoint decks with strict foreground completeness, shadow/halo removal, required-component recall checks, separated draggable backgrounds, and controlled hidden-region image recovery. Use when prior image-to-PPT output has clipped assets, missing icons, dirty shadows, fused backgrounds, or partially visible overlapping images that must become independently movable.
---

# Presentation Reconstruction Precision

Rebuild image-based slides as editable PowerPoint objects while refusing common visual shortcuts that produce clipped, dirty, or incomplete assets.

## Non-Negotiable Rules

- Separate decorative background art from cards, text, icons, photos, and charts.
- Create titles, labels, callouts, lines, bars, circles, and simple indicator icons as native PPT objects.
- Preserve rectangular photos/charts as media when transparency would damage meaningful content.
- Give all important elements stable shape names.
- Remove unrequested shadows, glow, and soft-edge effects from native shapes.
- Do not deliver a transparent foreground asset whose subject touches a crop edge unless it is explicitly approved.
- Do not omit a visible icon or label simply because it is small.
- Restore hidden pixels only for non-factual visuals; never invent chart data, text, values, or logos.

## Workflow

1. Bootstrap or create a semantic `deck_plan.json` and per-slide `layout_plan.json`.
2. Build a component inventory from OCR/vision inspection. For every key content block, populate `required_components`.
3. Define backgrounds as `background_decor`; prefer crops that contain only background. Use content masks only when unavoidable.
4. Define foreground visual assets with a role:
   - `opaque_icon`: vehicle, fish, shield, target, snowflake.
   - `translucent_subject`: glass bottle, white pellet, liquid, pale instrument.
   - `light_subject` or `preserve_tile`: pale subjects or compound visual tiles that must stay intact.
   - `photo_rect`: photo, dense map, chart, text-bearing scene.
   - `native_rebuild`: arrows, mini charts, badges, indicator icons.
5. Capture subjects with padding. Use `integrity.min_clear_margin_px` and inspect crop context before generating transparent PNGs.
6. Do not automatically remove the background for `light_subject`, `preserve_tile`, or `translucent_subject`; the transparency stage skips these unless `approved_transparency: true` was set after visual validation.
7. Add transparent safe-canvas padding around extracted PNG subjects while expanding their PPT placement bounds, so the visible subject stays in the same position and no draggable image has its contour flush against the PNG edge. Padding prevents new clipping; it does not restore pixels already missing in the source crop.
6. For overlapping lower media, declare `occlusion.status: "needs_recovery"` and `content_safety: "non_factual_visual"` only when image restoration is permitted. Run `scripts/occlusion_recovery.py`; if tasks remain, use an image-editing model to create the specified recovered output before generation.
7. Run the full pipeline:

```bash
python scripts/run_pipeline.py work/deck_plan.json --skip-auto-plan --transparent-mode marked --strict-integrity --out work/reconstructed.pptx
```

8. Inspect previews, foreground checkerboards, background mask previews, component recall report, and integrity report. Correct and regenerate until strict QA passes or limitations are explicitly reported.

## Asset Contract

Use padded crops for foreground assets:

```json
{
  "id": "truck",
  "type": "crop",
  "crop": {"x": 40, "y": 300, "w": 220, "h": 130},
  "asset_mode": "transparent_subject",
  "subject_mode": "opaque_icon",
  "integrity": {"required": true, "min_clear_margin_px": 8, "allow_edge_touch": []}
}
```

For pale or translucent subjects, do not trust ordinary color-threshold removal:

```json
{
  "id": "glass_vial",
  "asset_mode": "transparent_subject",
  "subject_mode": "translucent_subject",
  "requires_model_cutout": true,
  "integrity": {"required": true, "min_clear_margin_px": 8}
}
```

Provide a prepared cutout file or keep the object as `photo_rect` until a validated model cutout is available.

For semantic recall, list required elements:

```json
{
  "required_components": [
    {"id": "metric_y1_icon", "element_id": "metric_y1_icon", "required": true},
    {"id": "metric_y1_text", "element_id": "metric_y1_text", "required": true}
  ]
}
```

## Scripts

- `scripts/run_pipeline.py`: full reconstruction and strict QA orchestration.
- `scripts/deck_to_pptx.py`: PowerPoint output with default effect removal.
- `scripts/asset_integrity_audit.py`: rejects clipped/edge-touching foreground assets.
- `scripts/component_recall_audit.py`: verifies visible required components were built.
- `scripts/transparent_assets.py`: creates transparent PNG assets; avoid for translucent objects unless validated.
- `scripts/occlusion_recovery.py`: emits/apply hidden-region recovery tasks.

## References

- Read `references/precision_qa_contract.md` for edge, shadow, component-recall, and restoration requirements.
- Read `references/background_content_separation.md` when content overlays decorative backgrounds.
- Read `references/occlusion_recovery.md` before using image restoration.
- Read `references/deck_schema.md` for plan fields.
