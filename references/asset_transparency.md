# Asset Transparency

Use transparent PNG cleanup when a cropped visual object should move independently on top of editable PowerPoint structure.

## Process As Transparent PNG

- Bottles, vials, syringes, needles, trucks, freezers, dryers, fish, shields, targets, snowflakes, arrows, simple icons, and logos.
- Recovered lower visual objects after occlusion repair when they are standalone illustrations or product-like objects.
- Crops with `asset_mode: "transparent_subject"`, `transparent: true`, or `background_removal: true`.

## Keep As Rectangular Assets

- Dense charts, maps, screenshots, tables, microscopic panels with labels, full-slide fallbacks, waves, decorative bands, and information panels.
- Any crop whose text cannot be reliably overlaid as editable text.
- Assets marked `contains_text: true`, unless the agent intentionally sets `transparent: true` and also creates editable text overlays.

## Asset Fields

```json
{
  "id": "vaccine_bottle",
  "type": "crop",
  "source": "normalized.png",
  "crop": {"x": 920, "y": 210, "w": 120, "h": 180},
  "file": "vaccine_bottle.png",
  "reason": "standalone bottle",
  "contains_text": false,
  "asset_mode": "transparent_subject",
  "remove_border": true,
  "transparent_threshold": 42,
  "transparent_feather": 0.65,
  "edge_clear_px": 6
}
```

After running `scripts/transparent_assets.py`, the script updates `file` to `*_transparent.png`, preserves `original_file`, and writes `transparent_assets_report.json`.

## QA Rules

- Inspect `slides/<id>/assets/_transparent_qa/*_preview.png` on a checkerboard background.
- Reject obvious white, blue, or card-border halos around the subject.
- Keep the transparent canvas dimensions stable unless the layout plan is also updated.
- Do not remove factual chart/map/table pixels to make a prettier object.
