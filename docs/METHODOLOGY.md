### Matching Methodology

This document explains the matching algorithms and confidence scoring used in the Modelbank card matching system.

## Overview

The system uses a **waterfall matching strategy** with four progressively broader methods:

1. **URL Matching** (highest confidence)
2. **Exact SKU Matching** (high confidence)
3. **Fuzzy SKU Matching** (variable confidence)
4. **Name Similarity** (variable confidence)

Each method is tried in order, and the first successful match is used. This ensures we get the most reliable match available.

## 1. URL Matching

**Confidence:** High
**When used:** If both card and product have URLs

Compares normalized URLs to find exact matches. This is the most reliable method because product URLs are unique identifiers.

### Normalization Process

```python
# Original URLs
card_url = "https://www.bassettfurniture.com/p/3991-PLSECTL/owens-leather-sectional"
product_url = "https://www.bassettfurniture.com/p/3991-PLSECTL/owens-leather-sectional?color=navy"

# Normalized URLs (both become identical)
"bassettfurniture.com/p/3991-PLSECTL/owens-leather-sectional"
```

**Normalization steps:**
- Remove protocol (`https://`, `http://`)
- Remove `www.` prefix
- Remove trailing slashes
- Remove query parameters (`?...`)
- Remove fragments (`#...`)
- Convert to lowercase

## 2. Exact SKU Matching

**Confidence:** High
**When used:** If card has a SKU and URL matching failed

Compares normalized SKUs to find exact matches.

### Normalization Process

```python
# Original SKUs
card_sku = "BAS-3991-K4808"      # Retailer SKU with prefix
product_sku = "3991-K4808"        # Modelbank SKU

# Normalized SKUs (both become identical)
"3991K4808"
```

**Normalization steps:**
- Convert to uppercase
- Remove retailer prefixes (e.g., `BAS-`, `CB-`)
- Remove separators (`-`, `_`, spaces)

## 3. Fuzzy SKU Matching

**Confidence:** Variable (high/medium/low based on result count)
**When used:** If exact SKU matching failed

Generates multiple SKU variants and matches against an index of product SKU variants. This handles cases where:
- Card SKU includes color/configuration codes
- Modelbank SKU is the base product SKU
- SKU formats differ between systems

### Variant Generation

Given card SKU: `2676-WLSECTL-KIT53`

Generated variants:
```python
[
  "2676-WLSECTL-KIT53",     # Original
  "2676WLSECTLKIT53",       # No separators
  "2676",                   # Base (before first dash)
  "2676-WLSECTL",           # First two parts
  "2676WLSECTL",            # First two parts, no separator
  "2676WLSECTL"             # Numeric base (trailing letters removed)
]
```

Product SKU: `2676-LSECT`
Will match via base variant `"2676"` or partial match `"2676LSECTL"` ≈ `"2676WLSECTL"`

### Confidence Assignment

Fuzzy matching confidence depends on **how many products matched**:

- **1 match = HIGH confidence** - Unique product family
- **2-3 matches = MEDIUM confidence** - Small product family (likely variants)
- **4+ matches = LOW confidence** - Large product family or ambiguous match

Example:
```
Card SKU: "1342-3"
Matches: [1342-3-22, 1342-3-53, 1342-3L-53]
Count: 3 matches
Confidence: MEDIUM (likely different configurations of same product)
```

## 4. Name Similarity

**Confidence:** Variable (based on similarity score)
**When used:** If all SKU methods failed

Compares product names using word overlap (Jaccard similarity).

### Similarity Calculation

```python
card_name = "Owens Modern Leather Dining Chair with Arms"
product_name = "Owens Leather Arm Chair"

# Extract words (remove stop words)
card_words = {"owens", "modern", "leather", "dining", "chair", "arms"}
product_words = {"owens", "leather", "arm", "chair"}

# Calculate Jaccard similarity
intersection = {"owens", "leather", "chair"}  # 3 words
union = {"owens", "modern", "leather", "dining", "chair", "arms", "arm"}  # 7 words
similarity = 3 / 7 = 0.43
```

### Stop Words Removed

`the`, `a`, `an`, `and`, `or`, `but`, `in`, `with`, `of`, `for`, `to`, `from`, `by`

### Confidence Thresholds

- **Similarity > 0.8 = HIGH confidence** - Very similar names
- **Similarity > 0.6 = MEDIUM confidence** - Moderately similar
- **Similarity ≤ 0.6 = LOW confidence** - Weak similarity

Default threshold to return any match: **0.6**

## Style Matching

Style matching extracts SKUs from room image filenames and matches them to products.

### SKU Extraction Patterns

Given filename: `ORIGINAL_Blue-Swedish-Transitional-1342-3-6442-2-Emmett-A-WI25.jpg`

Extraction patterns:
```python
1. Standard: \d{3,4}-[A-Z0-9]+     → Matches: "1342-3", "6442-2"
2. Custom:   [A-Z]\d{3}-[A-Z0-9]+  → Matches: "C000-72SFA1"
3. Underscore: \d{3,4}-\d+__       → Matches: "1215-05"
4. Numeric:  0\d{3}                → Matches: "0270", "0237"
```

Extracted SKUs: `["1342-3", "6442-2"]`

### Product-Style Mapping

The system builds bidirectional mappings:

**Style → Products**
```json
{
  "Blue Swedish Transitional": [
    {"sku": "1342-3", "name": "Emma Sofa"},
    {"sku": "6442-2", "name": "Langford Coffee Table"}
  ]
}
```

**Product → Styles**
```json
{
  "1342-3": [
    {"style_id": 6892, "style_name": "Blue Swedish Transitional"},
    {"style_id": 6901, "style_name": "Modern Farmhouse Living"}
  ]
}
```

## Confidence System Summary

| Method | Match Count | Similarity | Confidence |
|--------|-------------|------------|------------|
| URL | 1+ | - | **HIGH** |
| Exact SKU | 1+ | - | **HIGH** |
| Fuzzy SKU | 1 | - | **HIGH** |
| Fuzzy SKU | 2-3 | - | **MEDIUM** |
| Fuzzy SKU | 4+ | - | **LOW** |
| Name | 1+ | > 0.8 | **HIGH** |
| Name | 1+ | > 0.6 | **MEDIUM** |
| Name | 1+ | ≤ 0.6 | **LOW** |

## Quality Metrics

The system calculates an overall quality score (0-100) based on:

### Match Rate Score (0-40 points)
```
score = match_rate * 0.4
Example: 57.4% match rate = 22.9 points
```

### Confidence Score (0-40 points)
```
weighted_score = (high_count * 1.0 + medium_count * 0.5 + low_count * 0.2) / total_matched
score = weighted_score * 40
Example: 324 high, 155 med, 728 low = 20.7 points
```

### Style Coverage Score (0-20 points)
```
score = min(20, style_coverage_percent * 0.2)
Example: 50% with styles = 10 points
```

**Total Quality Score = Match Rate + Confidence + Style**

Example: 22.9 + 20.7 + 10.0 = **53.6 / 100**

## Configuration

Matching behavior can be tuned per retailer in `config/retailers.yaml`:

```yaml
matching:
  name_similarity_threshold: 0.6          # Min similarity for name matching
  fuzzy_sku_enabled: true                 # Enable fuzzy SKU matching
  max_fuzzy_matches_high: 1               # 1 match = high confidence
  max_fuzzy_matches_medium: 3             # 2-3 matches = medium
```

## Best Practices

1. **Prefer URL matching** - Most reliable, unique identifiers
2. **Use exact SKU when possible** - Second most reliable
3. **Be cautious with fuzzy matching** - Verify low-confidence matches
4. **Review unmatched products** - May indicate missing Modelbank data or scraping issues
5. **Validate style assignments** - Check if product SKUs extracted from images make sense
6. **Monitor quality score** - Track improvements over time

## Common Issues

### High Match Rate but Low Confidence
- Many fuzzy/name matches with 4+ products
- **Solution:** Improve SKU normalization or add more products to Modelbank

### Low Match Rate
- Products missing from Modelbank
- Incorrect supplier_id
- SKU format mismatch
- **Solution:** Verify Modelbank data, check supplier_id, adjust SKU patterns

### Missing Style Assignments
- Style image filenames don't contain SKUs
- SKU patterns not matching filename format
- **Solution:** Customize `sku_patterns` in StyleMatcher config

### False Positives
- Name matching too aggressive
- **Solution:** Increase `name_similarity_threshold` (e.g., 0.7 instead of 0.6)
