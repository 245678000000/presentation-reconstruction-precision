# Vision Annotation Schema

Use this file when manual or model-assisted visual reasoning can identify objects better than deterministic image heuristics.

Write `slides/<slide_id>/vision_annotations.json`:

```json
{
  "slide_id": "slide_01",
  "canvas": {"width": 1672, "height": 941},
  "observations": [
    {
      "id": "title_main",
      "kind": "text",
      "text": "研究背景：运输冷链限制是活菌疫苗推广的关键瓶颈",
      "bbox": {"x": 145, "y": 45, "w": 960, "h": 45},
      "style": {"font_size": 35, "font_weight": 700, "color": "#FFFFFF"},
      "layer": "text",
      "confidence": 0.95
    },
    {
      "id": "header_bar",
      "kind": "shape",
      "shape": "round_rect",
      "bbox": {"x": 116, "y": 25, "w": 1033, "h": 78},
      "style": {"fill": "#003B91", "rx": 10},
      "layer": "structure",
      "confidence": 0.9
    },
    {
      "id": "lower_image",
      "kind": "image",
      "bbox": {"x": 260, "y": 180, "w": 520, "h": 360},
      "layer": "underlay_recovered",
      "occlusion_role": "lower",
      "hidden_by": ["upper_badge"],
      "needs_recovery": true,
      "asset_mode": "transparent_subject",
      "transparent": true,
      "remove_border": true
    }
  ]
}
```

## Observation Kinds

- `text`: editable text or rich text candidate.
- `shape`: rectangle, rounded rectangle, circle, line, arrow, panel, divider.
- `image`: photo, logo, chart, screenshot, illustration, map, microscopic image.
- `table`: editable table candidate.
- `chart`: simple editable chart candidate or dense chart asset.
- `overlap`: explicit relationship between two observations.

## Merge Rules

- `kind=text` becomes `text` unless `runs` are provided, then use `rich_text`.
- `kind=shape` becomes native PowerPoint shape when possible.
- `kind=image` becomes a crop asset plus image element.
- `needs_recovery=true` creates an occlusion recovery task.
- `asset_mode`, `transparent`, `background_removal`, and `remove_border` are copied onto image assets for transparent PNG cleanup.
- `confidence < 0.75` should set `needs_review: true`.

Do not invent unreadable text. Use `needs_review: true` or image assets.
