# Background And Content Separation

Use this when decorative background imagery is mixed with editable content in a screenshot. The goal is to make background art draggable independently while keeping cards, icons, text, and callouts editable above it.

## Generic Rule

Do not classify by subject matter such as fish, waves, buildings, grids, or particles. Classify by role:

- `background`: decorative art, texture, photo wash, wave, footer, watermark, pattern, ambience.
- `content`: text, callout boxes, badges, cards, legends, icons that communicate a point, charts, tables, data labels.
- `content asset`: a non-editable visual object that should still move with content, such as a product photo or icon.

## Recommended Layer Split

1. `decor`: cleaned background image, named `slideXX.bg.*`.
2. `structure`: editable cards, rounded boxes, borders, dividers, named `slideXX.content.*`.
3. `icon` / `media`: foreground icons or subject PNGs, named `slideXX.content.icon.*` or `slideXX.asset.*`.
4. `text`: editable text, named `slideXX.content.text.*`.

## Asset Fields

Mark a background crop like this:

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
    "exclude_elements": ["bg_fish"],
    "padding": 14,
    "mask_blur": 2,
    "inpaint_radius": 7
  }
}
```

Then place it as an image element:

```json
{
  "id": "slide11.bg.bottom_decor",
  "type": "image",
  "asset_id": "bottom_decor",
  "x": 0,
  "y": 760,
  "w": 1672,
  "h": 181,
  "layer": "decor",
  "z": 1,
  "background_role": "decor"
}
```

## Workflow

1. Crop assets with `scripts/crop_assets.py`.
2. Run `scripts/separate_background_content.py deck_plan.json`.
3. Rebuild cards, labels, icons, and text as separate objects above the cleaned background.
4. Inspect `slides/<id>/assets/_background_qa/*_mask_preview.png`.

## QA

- Moving a `bg.*` object should not move any text, card, badge, or foreground icon.
- The cleaned background should not contain readable ghost text or obvious callout-box remnants.
- If deterministic cleanup is too blurry, save the generated mask and use an image editing/inpainting tool to produce a better `*_background_clean.png`, then keep the same layout plan.
