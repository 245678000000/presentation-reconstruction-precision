# Precision QA Contract

## Foreground Completeness

- Capture foreground subjects with at least 8 px clearance where source context permits.
- Treat alpha-subject contact within `min_clear_margin_px` as a failed integrity check unless the side is named in `allow_edge_touch`.
- Add transparent safe-canvas padding after a validated cutout and expand its PPT placement bounds so the visible object does not shift; this removes edge-contact hazards but is not hidden-region restoration.
- Split combined visual objects when one would be harmed by transparency processing.
- Use `subject_mode: "translucent_subject"` for glass, liquid, white powder, and low-contrast pale objects; require a validated cutout or retain a rectangular asset.

## Effects And Halos

- Native shapes default to no shadow, no glow, and no soft edge.
- Keep a shadow only when `effects.shadow` is explicitly set to a design requirement.
- Check transparent assets on a checkerboard; reject dirty gray haze, white fringe, original card borders, or diffuse cast shadows unless required.

## Component Recall

- Record visible key icons and labels as `required_components` in each slide plan.
- Fail strict QA when a required component has neither a matching element nor an approved omission note.
- Prefer native reconstruction for small bars, trend arrows, mini graphs, bullets, badges, and thermometer lines.

## Controlled Recovery

- Use image restoration only for non-factual photo texture, product imagery, equipment, fish, vehicles, vials, or background artwork.
- Require tasks to name the lower object, upper object, mask, output file, and `content_safety: "non_factual_visual"`.
- Do not proceed as independently editable when an occluded asset remains `needs_recovery`.
- Never model-fill text, numeric data, chart marks, logos, or scientific measurements.
