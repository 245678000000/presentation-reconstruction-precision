# Layering Contract

This skill uses a strict layer contract to keep objects visible and editable.

## Default Order

1. `background`
2. `fallback`
3. `decor`
4. `structure`
5. `underlay_recovered`
6. `media`
7. `chart`
8. `icon`
9. `text`
10. `annotation`
11. `debug`

PowerPoint uses creation order as z-order. Generators must sort by `(layer_index, z)`.

## Clickability Rules

- Editable text must not be covered by an image unless intentionally marked `covered: true`.
- Full-slide fallback must stay under all editable overlays.
- Decorative background crops must stay on `background` or `decor` and should be named `bg.*`.
- Card and panel backgrounds must stay below media crops.
- Recovered lower images must stay under their upper occluding objects.
- Transparent PNG subjects should sit above native card backgrounds and below editable text.
- Debug guides must be removed or placed on `debug`.

## Audit Warnings

Layer audit should warn when:

- An image overlaps editable text and has a higher layer or `z`.
- A fallback image is above non-fallback objects.
- A card-sized image crop replaces readable editable text.
- A cleaned transparent asset still contains visible card borders or dirty crop background.
- A recovered lower object is above its recorded upper object.
- Two image assets overlap without `occlusion_role`.
- An asset has `contains_text: true` without editable text overlays.

## Auto-Fix

`layer_audit.py --fix-order` may:

- Normalize unknown layers to `media`.
- Move `fallback_image` to layer `fallback`, z `0`.
- Move `text` and `rich_text` to layer `text`.
- Move recovered lower images to `underlay_recovered`.

It should not delete elements or invent recovered images.
