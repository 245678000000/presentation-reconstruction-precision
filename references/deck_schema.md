# Deck Schema

`deck_plan.json` is the root manifest.

```json
{
  "version": "2.0",
  "canvas": {"width": 1672, "height": 941, "aspect": "16:9"},
  "quality_mode": "balanced",
  "theme": {"font_family": "Microsoft YaHei", "colors": {"primary": "#003B91"}},
  "layer_policy": ["background", "fallback", "decor", "structure", "underlay_recovered", "media", "chart", "icon", "text", "annotation", "debug"],
  "slides": [
    {
      "id": "slide_01",
      "source": "slides/slide_01/source.png",
      "normalized": "slides/slide_01/normalized.png",
      "plan": "slides/slide_01/layout_plan.json",
      "assets_dir": "slides/slide_01/assets",
      "recovery_dir": "slides/slide_01/recovery"
    }
  ]
}
```

## Slide Plan

```json
{
  "version": "2.0",
  "slide_id": "slide_01",
  "canvas": {"width": 1672, "height": 941, "background": "#FFFFFF"},
  "assets": [],
  "elements": []
}
```

## Asset

```json
{
  "id": "image_lower_partial",
  "type": "crop",
  "source": "normalized.png",
  "crop": {"x": 200, "y": 160, "w": 520, "h": 360},
  "file": "image_lower_partial.png",
  "contains_text": false,
  "asset_mode": "transparent_subject",
  "transparent": true,
  "remove_border": true,
  "occlusion": {
    "status": "partial",
    "hidden_by": ["image_upper"],
    "recovered_file": "image_lower_recovered.png"
  },
  "transparency": {
    "status": "cleaned",
    "preview": "assets/_transparent_qa/image_lower_partial_preview.png"
  }
}
```

Use `occlusion.status` values:

- `none`: asset is fully visible or not relevant.
- `partial`: asset is visible but hidden by another object in the source screenshot.
- `needs_recovery`: hidden pixels need image restoration.
- `recovered`: `recovered_file` is available and should be used.

Use `asset_mode: "transparent_subject"` or `transparent: true` for standalone visual objects whose crop background should be removed. Do not use this for charts, maps, screenshots, tables, or text-heavy panels.

For decorative backgrounds that must move independently from content, use `asset_mode: "background_decor"` or `background_role: "decor"`:

```json
{
  "id": "bottom_decor",
  "type": "crop",
  "source": "normalized.png",
  "crop": {"x": 0, "y": 760, "w": 1672, "h": 181},
  "file": "bottom_decor.png",
  "contains_text": false,
  "asset_mode": "background_decor",
  "background_role": "decor",
  "background_cleanup": {
    "enabled": true,
    "auto_mask": true,
    "mask_layers": ["structure", "text", "icon", "annotation"],
    "erase_elements": ["bottom_callout_box", "bottom_callout_text"],
    "erase_rects": [{"x": 210, "y": 815, "w": 1210, "h": 65}],
    "exclude_elements": [],
    "padding": 14,
    "mask_blur": 2,
    "inpaint_radius": 7
  }
}
```

## Element Common Fields

```json
{
  "id": "slide01.image.lower",
  "type": "image",
  "layer": "underlay_recovered",
  "z": 10,
  "shape_name": "slide01.image.lower",
  "editability": "asset"
}
```

## Supported Elements

- `fallback_image`
- `image`
- `rect`
- `round_rect`
- `circle`
- `line`
- `arrow`
- `text`
- `rich_text`
- `table`
- `group`

For image elements:

```json
{
  "id": "lower_photo",
  "type": "image",
  "asset_id": "lower_photo",
  "x": 200,
  "y": 160,
  "w": 520,
  "h": 360,
  "fit": "stretch",
  "layer": "underlay_recovered",
  "z": 10,
  "occlusion_role": "lower"
}
```

Use `occlusion_role` values `lower`, `upper`, or `none`.

Transparent assets keep the same element geometry unless the plan is intentionally revised. The PNG canvas may contain transparent margins so the object remains aligned with the source crop.

Background image elements should use `layer: "decor"` or `layer: "background"` and `background_role: "decor"`. Content objects above them should be separate native shapes, images, and text.
