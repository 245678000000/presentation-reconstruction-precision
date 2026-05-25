# Occlusion Recovery

Occlusion recovery handles cases where two visual objects overlap, and the lower object must be editable/movable as an independent layer.

## Problem

If a slide screenshot shows object B on top of object A, the visible pixels of A are incomplete. Cropping A from the screenshot produces a damaged asset. Moving B later reveals a hole.

## Strategy

1. Identify lower and upper objects.
2. Crop the lower object's full bounding box from the source screenshot.
3. Create a mask for the hidden area where upper object overlaps lower object.
4. Create a recovery task describing what must be restored.
5. Use an image-edit/inpaint tool with the lower crop and mask.
6. Save the recovered asset to the path in the task.
7. Replace the lower asset with the recovered file.
8. Layer recovered lower object below the foreground upper object in PPT.

## Recovery Task

`occlusion_recovery.py` writes tasks like:

```json
{
  "id": "slide_01__lower_photo__covered_by_upper_badge",
  "slide_id": "slide_01",
  "lower_element_id": "lower_photo",
  "upper_element_id": "upper_badge",
  "input_image": "slides/slide_01/recovery/lower_photo_partial.png",
  "mask_image": "slides/slide_01/recovery/lower_photo_mask.png",
  "output_image": "slides/slide_01/recovery/lower_photo_recovered.png",
  "prompt": "Restore the masked hidden part of the lower image so it continues naturally behind the foreground object. Preserve lighting, perspective, texture, and slide style."
}
```

## Important Rules

- Do not claim hidden content is recovered until `output_image` exists.
- Keep the original partial crop as an audit artifact.
- Put recovered lower assets on `underlay_recovered` or `media`.
- After recovery and crop extraction, run `transparent_assets.py` when the recovered lower object should be a standalone transparent PNG. Do not transparentize recovered factual charts or maps.
- Keep the upper object on a later/higher layer.
- If lower content is semantic text, reconstruct it as editable text instead of inpainting a bitmap.

## When Not To Recover

Do not run image restoration for:

- Logos where the original logo file is available.
- Simple shapes that can be redrawn.
- Hidden text that should be reconstructed as editable text.
- Dense charts where the hidden data would be fabricated.

In those cases, rebuild the object or mark the limitation.
