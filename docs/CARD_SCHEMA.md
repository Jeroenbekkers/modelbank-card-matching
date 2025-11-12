# Card Enrichment Schema

This document describes the card enrichment schema used when adding Modelbank data to product cards.

## Overview

The enrichment process adds Modelbank metadata to product card META blocks. The system uses a **hybrid approach**:

- **All cards**: Get minimal identifiers (`model`, `sku`)
- **Meta card only**: Gets full enrichment (`fp_url`, `style`, `related_products`, etc.)

This avoids bloat while ensuring any retrieved card can link back to Modelbank.

## Card Structure

### Before Enrichment (v6)

```markdown
<!-- CARDSET_ID:GB00095D775ZXGADN7YELEOUL3ISOPMA3SJCD6RQ -->

<!-- CARD:definition -->
<!-- META: {
  "card_type": "product",
  "card_role": "definition",
  "sku": "1342-3"
} -->
## **Emma Tufted Sofa**

A classic tufted sofa with elegant rolled arms...

**SKU:** 1342-3
**Price:** $1,999
**URL:** https://www.bassettfurniture.com/p/1342-3/emma-sofa

<!-- CARD:context -->
<!-- META: {
  "card_role": "context"
} -->
Usage context...

<!-- CARD:meta -->
<!-- META: {
  "card_role": "meta"
} -->
Product specifications...
```

### After Enrichment (v7)

```markdown
<!-- CARDSET_ID:GB00095D775ZXGADN7YELEOUL3ISOPMA3SJCD6RQ -->

<!-- CARD:definition -->
<!-- META: {
  "card_type": "product",
  "card_role": "definition",
  "model": "xxxx50618d1ed4f46b2fd19c67ec06b3bd00f31b_28",
  "sku": "1342-3"
} -->
## **Emma Tufted Sofa**

A classic tufted sofa with elegant rolled arms...

**SKU:** 1342-3
**Price:** $1,999
**URL:** https://www.bassettfurniture.com/p/1342-3/emma-sofa

<!-- CARD:context -->
<!-- META: {
  "card_role": "context",
  "model": "xxxx50618d1ed4f46b2fd19c67ec06b3bd00f31b_28",
  "sku": "1342-3"
} -->
Usage context...

<!-- CARD:meta -->
<!-- META: {
  "card_role": "meta",
  "model": "xxxx50618d1ed4f46b2fd19c67ec06b3bd00f31b_28",
  "sku": "1342-3",
  "parent": "GB00095D775ZXGADN7YELEOUL3ISOPMA3SJCD6RQ",
  "is_private": true,
  "fp_url": "https://modelbank.floorplanner.com/products/xxxx50618d1ed4f46b2fd19c67ec06b3bd00f31b",
  "style": [
    {
      "style_id": 6892,
      "style_name": "Blue Swedish Transitional"
    }
  ],
  "related_products": [
    "1342-3-22",
    "1342-3-53",
    "1342-3L-53"
  ]
} -->
Product specifications...
```

## Field Definitions

### Added to All Cards

#### `model` (string, required for enriched cards)
The Modelbank product model ID.

**Format:** `xxxx50618d1ed4f46b2fd19c67ec06b3bd00f31b_28`

**Components:**
- `xxxx` prefix = Private product (visible only to retailer)
- Main ID = Unique product identifier
- `_28` suffix = Variant number

**Absence:** If `model` field is missing, product has no Modelbank match

**Example:**
```json
{
  "model": "xxxx50618d1ed4f46b2fd19c67ec06b3bd00f31b_28"
}
```

#### `sku` (string, required)
The retailer's product SKU. Usually already present in v6, preserved in v7.

**Example:**
```json
{
  "sku": "1342-3"
}
```

### Added to Meta Card Only

#### `parent` (string, optional)
The cardset ID (parent document identifier).

**Example:**
```json
{
  "parent": "GB00095D775ZXGADN7YELEOUL3ISOPMA3SJCD6RQ"
}
```

#### `is_private` (boolean, optional)
Whether this is a private product (retailer-exclusive).

**Private products:**
- Model ID starts with `xxxx`
- Only visible to the retailer
- Not shown in public Modelbank catalog

**Example:**
```json
{
  "is_private": true
}
```

#### `fp_url` (string, optional)
Direct URL to product in Modelbank/Floorplanner.

**Format:** `https://modelbank.floorplanner.com/products/{model_base}`

**Note:** URL uses base model ID (without `_XX` variant suffix)

**Example:**
```json
{
  "fp_url": "https://modelbank.floorplanner.com/products/xxxx50618d1ed4f46b2fd19c67ec06b3bd00f31b"
}
```

#### `modelbank_images` (object, optional)
CloudFront URLs for automatically generated product render images.

**Format:** Object with view names as keys and image URLs as values

**Available views:**
- `iso` - Isometric view (default primary view)
- `front` - Front view
- `left` - Left side view
- `top` - Top/overhead view

**URL pattern:** `https://d2bi8gvwsa8xa3.cloudfront.net/cdb/renders/{prefix}/{model_base}_{variant}.{view}.540.png`

Where:
- `prefix` = First 2 characters of model ID
- `model_base` = Model ID without variant suffix
- `variant` = Variant number (e.g., "00", "28")
- `view` = Camera angle (iso, front, left, top)
- `540` = Image width in pixels

**Example:**
```json
{
  "modelbank_images": {
    "iso": "https://d2bi8gvwsa8xa3.cloudfront.net/cdb/renders/ad/ad50ae3e51b0b9a35e3213ec0d4d2af1cdfe61c9_00.iso.540.png",
    "front": "https://d2bi8gvwsa8xa3.cloudfront.net/cdb/renders/ad/ad50ae3e51b0b9a35e3213ec0d4d2af1cdfe61c9_00.front.540.png",
    "left": "https://d2bi8gvwsa8xa3.cloudfront.net/cdb/renders/ad/ad50ae3e51b0b9a35e3213ec0d4d2af1cdfe61c9_00.left.540.png",
    "top": "https://d2bi8gvwsa8xa3.cloudfront.net/cdb/renders/ad/ad50ae3e51b0b9a35e3213ec0d4d2af1cdfe61c9_00.top.540.png"
  }
}
```

#### `style` (array of objects, optional)
Design styles this product appears in.

**Each style object contains:**
- `style_id` (integer): Floorplanner style ID
- `style_name` (string): Human-readable style name

**How determined:**
1. Product SKU found in style room image filenames
2. Matched to Modelbank styles via branding_id
3. Multiple styles possible if product appears in multiple rooms

**Example:**
```json
{
  "style": [
    {
      "style_id": 6892,
      "style_name": "Blue Swedish Transitional"
    },
    {
      "style_id": 6901,
      "style_name": "Modern Farmhouse Living"
    }
  ]
}
```

#### `related_products` (array of strings, optional)
SKUs of related products that appear in the same styles.

**How determined:**
1. Find all products in the same styles as current product
2. Sort and limit to top 5 most related
3. Excludes current product's own SKU

**Use cases:**
- Suggest coordinating products
- "Complete the look" recommendations
- Products that work well together

**Example:**
```json
{
  "related_products": [
    "6442-2",
    "2571-K173CB",
    "C000-72SFA1"
  ]
}
```

## Complete Meta Card Example

Full META block for a matched product with style assignments:

```json
{
  "card_role": "meta",
  "model": "ad50ae3e51b0b9a35e3213ec0d4d2af1cdfe61c9_00",
  "sku": "1342-3",
  "parent": "GB00095D775ZXGADN7YELEOUL3ISOPMA3SJCD6RQ",
  "is_private": false,
  "fp_url": "https://modelbank.floorplanner.com/products/ad50ae3e51b0b9a35e3213ec0d4d2af1cdfe61c9",
  "modelbank_images": {
    "iso": "https://d2bi8gvwsa8xa3.cloudfront.net/cdb/renders/ad/ad50ae3e51b0b9a35e3213ec0d4d2af1cdfe61c9_00.iso.540.png",
    "front": "https://d2bi8gvwsa8xa3.cloudfront.net/cdb/renders/ad/ad50ae3e51b0b9a35e3213ec0d4d2af1cdfe61c9_00.front.540.png",
    "left": "https://d2bi8gvwsa8xa3.cloudfront.net/cdb/renders/ad/ad50ae3e51b0b9a35e3213ec0d4d2af1cdfe61c9_00.left.540.png",
    "top": "https://d2bi8gvwsa8xa3.cloudfront.net/cdb/renders/ad/ad50ae3e51b0b9a35e3213ec0d4d2af1cdfe61c9_00.top.540.png"
  },
  "style": [
    {
      "style_id": 6892,
      "style_name": "Blue Swedish Transitional"
    }
  ],
  "related_products": [
    "1342-3-22",
    "1342-3-53",
    "1342-3L-53",
    "6442-2"
  ]
}
```

## Unmatched Products

Products without Modelbank matches are **not enriched** but are still copied to v7.

**Indicators of unmatched product:**
- No `model` field in META blocks
- No `fp_url`, `style`, or `related_products`
- Only `sku` remains from v6

**Example (unmatched product):**
```json
{
  "card_role": "definition",
  "card_type": "product",
  "sku": "9999-NOTFOUND"
}
```

## Field Presence Rules

| Field | All Cards | Meta Card | When Present |
|-------|-----------|-----------|--------------|
| `model` | ✅ Yes | ✅ Yes | Product matched to Modelbank |
| `sku` | ✅ Yes | ✅ Yes | Always (from original card) |
| `parent` | ❌ No | ✅ Yes | Product matched to Modelbank |
| `is_private` | ❌ No | ✅ Yes | Product matched AND is private |
| `fp_url` | ❌ No | ✅ Yes | Product matched to Modelbank |
| `modelbank_images` | ❌ No | ✅ Yes | Product matched to Modelbank |
| `style` | ❌ No | ✅ Yes | Product matched AND has style assignments |
| `related_products` | ❌ No | ✅ Yes | Product matched AND has related products |

## Usage in AI Systems

### Linking to Modelbank

When Linda retrieves a card with `model` field:

```python
# Extract model from any card in cardset
model_id = card_meta.get('model')

if model_id:
    # Strip variant suffix for URL
    model_base = model_id.rsplit('_', 1)[0]
    url = f"https://modelbank.floorplanner.com/products/{model_base}"
    # Fetch full 3D model, images, specifications
```

### Displaying Product Images

When showing products to users, use the Modelbank render images:

```python
# From meta card
images = meta.get('modelbank_images', {})

# Show isometric view as main image
main_image = images.get('iso')
if main_image:
    display_image(main_image)

# Provide additional views
for view_name, image_url in images.items():
    add_gallery_image(view_name, image_url)
```

**Example response:**
```
Emma Tufted Sofa
[Display: https://d2bi8gvwsa8xa3.cloudfront.net/cdb/renders/ad/...iso.540.png]

Additional views:
- Front view: [front.540.png]
- Left view: [left.540.png]
- Top view: [top.540.png]

Price: $1,999
SKU: 1342-3
View in 3D: https://modelbank.floorplanner.com/products/...
```

### Style-Based Recommendations

When user asks "What goes with this sofa?":

```python
# From meta card
styles = meta.get('style', [])
related_skus = meta.get('related_products', [])

# Retrieve related product cards
for sku in related_skus:
    related_card = retrieve_card_by_sku(sku)
    suggest_to_user(related_card)

# Or find more products in same styles
for style in styles:
    style_products = find_products_by_style(style['style_id'])
    suggest_to_user(style_products)
```

### Determining Product Availability

```python
is_private = meta.get('is_private', False)

if is_private:
    # Product exclusive to this retailer
    show_availability = "Available only at [Retailer Name]"
else:
    # Public Modelbank product, may be available from multiple retailers
    show_availability = "Also available from other retailers"
```

## Versioning

- **v6 cards**: Original cards from scraping/content2card
- **v7 cards**: Enriched cards with Modelbank metadata

**File naming:**
- Input: `12345_cards_v6.md`
- Output: `12345_cards_v7.md`

**Version in META:** Not stored in META, inferred from filename

## Schema Validation

To validate enriched cards:

```python
def validate_enriched_card(meta: dict) -> bool:
    """Validate enriched card META block"""

    # If model present, should have sku
    if 'model' in meta:
        assert 'sku' in meta, "model requires sku"

    # If meta card with model, should have fp_url
    if meta.get('card_role') == 'meta' and 'model' in meta:
        assert 'fp_url' in meta, "meta card with model requires fp_url"

    # Validate style format
    if 'style' in meta:
        assert isinstance(meta['style'], list), "style must be array"
        for style in meta['style']:
            assert 'style_id' in style, "style needs style_id"
            assert 'style_name' in style, "style needs style_name"

    # Validate related_products format
    if 'related_products' in meta:
        assert isinstance(meta['related_products'], list), "related_products must be array"
        assert len(meta['related_products']) <= 5, "max 5 related products"

    return True
```

## Future Enhancements

Potential future additions to schema:

- `product_family`: Group related variants
- `dimensions`: Width, depth, height from Modelbank
- `materials`: Material information
- `tags`: Searchable tags (color, style, room)
- `price_range`: Modelbank MSRP if available
- `last_updated`: Timestamp of last enrichment

These would go in meta card only, following same pattern.
