# Adding a New Retailer

This guide walks you through adding a new retailer to the Modelbank card matching system.

## Prerequisites

Before you begin, you'll need:

1. **Product cards** from the retailer's website (Linda cards in markdown format)
2. **Modelbank supplier_id** for this retailer
3. **Floorplanner branding_id** (optional, for styles)
4. **API credentials** for Modelbank/Floorplanner
5. **Style images** (optional, room photos with product SKUs in filenames)

## Step-by-Step Guide

### 1. Get Retailer IDs

#### Find Supplier ID

The supplier_id identifies the retailer in Modelbank.

```bash
# Method 1: Check Modelbank dashboard
# Visit: https://mb.floorplanner.com/suppliers
# Find your retailer and note the ID

# Method 2: Search via API
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://mb.floorplanner.com/api/v1/suppliers/search.json?name=RetailerName"
```

#### Find Branding ID (Optional)

The branding_id is used to fetch retailer-specific styles.

```bash
# Check Floorplanner API
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://floorplanner.com/api/v2/brandings.json" | jq '.[] | select(.name | contains("Retailer"))'
```

### 2. Prepare Product Cards

Ensure your product cards follow the Linda card format:

```markdown
<!-- CARDSET_ID:GB00095... -->

<!-- CARD:definition -->
<!-- META: {"card_type": "product", "card_role": "definition", "sku": "3991-K4808"} -->
## **Product Name**

Description...

**SKU:** 3991-K4808
**Price:** $1,299
**URL:** https://www.retailer.com/products/...

<!-- CARD:context -->
<!-- META: {"card_role": "context"} -->
...
```

**Requirements:**
- Cards must be in `.md` format
- Must include `SKU:` field (case-insensitive)
- Must include product URL (if available)
- Cards should follow `*_cards_v6.md` naming pattern (configurable)

### 3. Prepare Style Images (Optional)

If you want style assignments:

1. **Organize style folders:**
   ```
   retailer_styles/
   ├── Blue Swedish Transitional - 1342-3-6442-2/
   │   └── ORIGINAL_image.jpg
   ├── Modern Farmhouse - 2571-C000-72/
   │   └── ORIGINAL_photo.jpg
   └── ...
   ```

2. **Name requirements:**
   - Folder name: `Style Name - SKU1-SKU2-...` (SKUs optional in folder name)
   - Image name: Must start with `ORIGINAL_` and contain SKUs
   - Image format: `.jpg` or `.png`

3. **SKU in filenames:**
   The system extracts SKUs from image filenames using patterns like:
   - Standard: `1342-3`, `2571-K173CB`
   - Custom: `C000-72SFA1`
   - Numeric: `0270`

### 4. Configure Retailer

Edit `config/retailers.yaml` and add your retailer:

```yaml
your_retailer:
  # Modelbank configuration
  supplier_id: 1234                                    # Required: Modelbank supplier ID
  branding_id: 56789                                   # Optional: Floorplanner branding ID for styles

  # Retailer information
  name: "Your Retailer Name"                           # Display name
  base_url: "https://www.yourretailer.com"             # Retailer website

  # File paths
  card_path: "/path/to/retailer/linda-cards/product"  # Required: Product cards directory
  style_images_path: "/path/to/retailer/styles"       # Optional: Style images directory
  output_path: "/path/to/retailer/output"             # Output directory for results

  # Matching configuration (optional overrides)
  matching:
    name_similarity_threshold: 0.6                     # 0.0-1.0, default 0.6
    fuzzy_sku_enabled: true                            # Enable fuzzy SKU matching
    max_fuzzy_matches_high: 1                          # 1 match = high confidence
    max_fuzzy_matches_medium: 3                        # 2-3 matches = medium confidence
```

### 5. Configure API Credentials

Edit `config/api_credentials.yaml`:

```yaml
modelbank:
  api_url: "https://mb.floorplanner.com/api/v1"
  auth_token: "your-jwt-token-here"

floorplanner:
  api_url: "https://floorplanner.com/api/v2"
  auth_token: "your-jwt-token-here"  # Usually same as Modelbank
```

**Security:** These files are in `.gitignore` - never commit credentials!

### 6. Test Matching

Run the matching pipeline:

```bash
# Full pipeline
./scripts/run_full_pipeline.sh your_retailer

# Or step by step:

# Step 1: Match products
python3 src/cli.py your_retailer match

# Step 2: Match styles (optional)
python3 src/cli.py your_retailer match-styles

# Step 3: Enrich cards
python3 src/cli.py your_retailer enrich

# Step 4: Generate reports
python3 src/cli.py your_retailer analyze
```

### 7. Review Results

Check the output directory (specified in `output_path`):

```
output/
├── matches.json              # Product matching results
├── style_mappings.json       # Style-product mappings (if styles enabled)
├── enriched_cards/           # Enriched card files (v7)
├── report.txt                # Human-readable analysis report
└── report.json               # Structured analysis data
```

### 8. Validate Results

#### Check Match Rate
```bash
# Quick summary
python3 src/cli.py your_retailer analyze

# Expected: 50-70% match rate for most retailers
# High confidence: 15-30%
# Medium confidence: 10-20%
# Low confidence: remaining matches
```

#### Verify Enriched Cards

Check a few enriched cards to ensure META blocks look correct:

```markdown
<!-- CARD:meta -->
<!-- META: {
  "card_role": "meta",
  "model": "xxxx50618d1ed4f46b2fd19c67ec06b3bd00f31b_28",
  "sku": "3991-K4808",
  "parent": "GB00095D775ZXGADN7YELEOUL3ISOPMA3SJCD6RQ",
  "is_private": true,
  "fp_url": "https://modelbank.floorplanner.com/products/xxxx50618...",
  "style": [{"style_id": 6892, "style_name": "Blue Swedish Transitional"}],
  "related_products": ["3991-K4809", "3991-K4810"]
} -->
```

#### Review Problematic Matches

Check the report for issues:
- **Low confidence matches** - May need manual review
- **Products with 4+ matches** - Ambiguous matches
- **Unmatched products** - Missing from Modelbank or scraping issues

### 9. Tune Configuration

If results aren't satisfactory, adjust matching configuration:

#### Low Match Rate?

```yaml
matching:
  # Enable fuzzy matching if not already enabled
  fuzzy_sku_enabled: true

  # Lower name similarity threshold to be more permissive
  name_similarity_threshold: 0.5  # Default: 0.6
```

#### Too Many Low-Confidence Matches?

```yaml
matching:
  # Raise thresholds for fuzzy matching
  max_fuzzy_matches_high: 1
  max_fuzzy_matches_medium: 2    # Stricter: 2 instead of 3

  # Raise name similarity threshold
  name_similarity_threshold: 0.7  # Default: 0.6
```

#### Custom SKU Patterns?

If your retailer uses unusual SKU formats, customize the StyleMatcher:

```python
# In your custom script
from matchers.style_matcher import StyleMatcher

custom_patterns = [
    ('retailer_format', r'RET-\d{4}-[A-Z]{2}'),  # Custom pattern
]

matcher = StyleMatcher(config={'sku_patterns': custom_patterns})
```

### 10. Automate Updates

Set up regular re-matching as your product catalog grows:

```bash
# Add to cron or automation system
# Run weekly to pick up new products
./scripts/run_full_pipeline.sh your_retailer
```

## Common Issues

### Issue: "Retailer not found in config"
**Solution:** Check spelling in `config/retailers.yaml` and CLI command

### Issue: "No products fetched from Modelbank"
**Solution:**
- Verify `supplier_id` is correct
- Check API credentials
- Confirm products exist in Modelbank for this supplier

### Issue: "No card files found"
**Solution:**
- Verify `card_path` points to directory with `product/` subdirectory
- Check card files end with correct suffix (default: `_cards_v6.md`)
- Ensure cards are in markdown format

### Issue: "Style matching found 0 styles"
**Solution:**
- Verify `style_images_path` is configured
- Check folders contain `ORIGINAL_*` image files
- Verify SKUs are in image filenames
- Try customizing SKU patterns if format is unusual

### Issue: "All matches are low confidence"
**Solution:**
- Review SKU formats - may need normalization adjustments
- Check if Modelbank has base SKUs vs. retailer has variant SKUs
- Consider if name matching threshold is too low
- Verify products in Modelbank match those on retailer site

## Example: Real Bassett Configuration

Here's the actual Bassett configuration as a reference:

```yaml
bassett:
  supplier_id: 2397
  branding_id: 334116
  name: "Bassett Furniture"
  base_url: "https://www.bassettfurniture.com"
  card_path: "/home/jeroen/clients/bassett/linda-cards/product"
  style_images_path: "/home/jeroen/clients/bassett/roomprompt examples"
  output_path: "/home/jeroen/clients/bassett/output"
  matching:
    name_similarity_threshold: 0.6
    fuzzy_sku_enabled: true
    max_fuzzy_matches_high: 1
    max_fuzzy_matches_medium: 3
```

**Results:**
- 2,103 products
- 57.4% match rate
- 324 high-confidence matches (15.4%)
- 75 styles with product assignments

## Next Steps

Once your retailer is configured and matching well:

1. **Document SKU patterns** - Note any retailer-specific patterns for future reference
2. **Share results** - Export quality scores and match statistics
3. **Integrate with Linda** - Use enriched cards in your AI assistant
4. **Monitor quality** - Re-run matching periodically and track quality scores
5. **Add more retailers** - Repeat this process for your other 39 retailers!

## Getting Help

- Check `docs/METHODOLOGY.md` for matching algorithm details
- Review `docs/CARD_SCHEMA.md` for enrichment schema
- See `examples/bassett/` for real-world example
- Open an issue on GitHub for specific problems
