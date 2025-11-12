# Modelbank Card Matching

A comprehensive system for matching retailer product cards with Modelbank products and style data. Designed to work across 40+ furniture retailers with consistent methodology and quality tracking.

## Overview

This tool automatically matches:
- **Product cards** (from retailer websites) → **Modelbank products** (3D models, images)
- **Style images** (room photos) → **Products shown** in those images
- **Products** → **Design styles** (e.g., "Blue Swedish Transitional")

The output enriches product cards with Modelbank IDs, URLs, style assignments, and related products for AI assistants like Linda.

## Features

- 🎯 **Multi-method matching**: URL, SKU (exact + fuzzy), name similarity
- 📊 **Confidence scoring**: High/medium/low based on match quality
- 🎨 **Style extraction**: Extract SKUs from room images, map to products
- 📝 **Card enrichment**: Add Modelbank data to card META blocks
- 📈 **Deep analysis**: Gap detection, pattern analysis, quality metrics
- ☁️ **Gemini upload**: Upload enriched cards to Google's semantic search
- 🔧 **Configurable**: Easy to add new retailers via YAML config
- 🧪 **Tested**: Proven on Bassett (2,103 products, 75 styles)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure your retailer (copy from template)
cp config/retailers.example.yaml config/retailers.yaml
# Edit with your retailer's details

# Run matching pipeline
./scripts/run_full_pipeline.sh bassett

# Upload enriched cards to Gemini (optional)
./scripts/upload_to_gemini.sh bassett

# View results
cat output/report.txt
```

## Results

Example from Bassett Furniture:
- **2,103 product cards** processed
- **1,207 matches** (57.4% match rate)
  - 324 high confidence (URL/exact SKU matches)
  - 155 medium confidence
  - 742 low confidence (product families)
- **75 styles** with product assignments
- **324 cards enriched** with Modelbank data

## Workflow

```
┌─────────────────┐
│ Retailer Cards  │  Product cards from website scraping
└────────┬────────┘
         │
         ├──────────────┐
         │              │
    ┌────▼─────┐   ┌───▼───────┐
    │ Products │   │  Styles   │  Style images with room photos
    └────┬─────┘   └───┬───────┘
         │             │
         │             ├─────────> Extract SKUs from filenames
         │             │
         ├──────┐      │
         │      │      │
    ┌────▼──────▼──────▼────┐
    │   Modelbank API       │  Fetch products by supplier_id
    │   supplier_id: 2397   │  Fetch styles by branding_id
    └────────┬──────────────┘
             │
    ┌────────▼────────────┐
    │  Matching Engine    │  • URL matching
    │                     │  • SKU exact/fuzzy
    │                     │  • Name similarity
    │                     │  • Confidence scoring
    └────────┬────────────┘
             │
    ┌────────▼────────────┐
    │   Style Mapping     │  • Style → Products
    │                     │  • Products → Styles
    │                     │  • Related products
    └────────┬────────────┘
             │
    ┌────────▼────────────┐
    │  Card Enrichment    │  Add to META blocks:
    │  v6 → v7           │  • model, fp_url
    │                     │  • style assignments
    │                     │  • related_products
    └────────┬────────────┘
             │
    ┌────────▼────────────┐
    │  Analysis Reports   │  • Match statistics
    │                     │  • Confidence breakdown
    │                     │  • Gap analysis
    │                     │  • Quality metrics
    └────────┬────────────┘
             │
    ┌────────▼────────────┐
    │  Gemini Upload      │  • Upload to semantic search
    │  (Optional)         │  • Enable AI retrieval
    │                     │  • Multi-retailer queries
    └─────────────────────┘
```

## Matching Methods

### 1. URL Matching (Highest Confidence)
Exact URL comparison after normalization.
```python
# Card URL:     https://www.bassettfurniture.com/pdp/sofas/emma-sofa/12345.html
# Modelbank URL: https://www.bassettfurniture.com/pdp/sofas/emma-sofa/12345.html
# → MATCH (high confidence)
```

### 2. SKU Exact Matching (High Confidence)
Direct SKU comparison after normalization.
```python
# Card SKU:      "BAS-1234-56"
# Modelbank SKU: "BAS-1234-56"
# → MATCH (high confidence)
```

### 3. SKU Fuzzy Matching (Variable Confidence)
Generates SKU variants to handle color codes, configurations.
```python
# Card SKU:      "2676-LSECTL-KIT53"  (with color/config)
# Modelbank SKU: "2676-LSECT"         (base SKU)
# Variants: ["2676", "2676LSECTL", "LSECTL", ...]
# → MATCH via "2676" (confidence depends on # of matches)
```

**Confidence rules:**
- 1 match = High (unambiguous)
- 2-3 matches = Medium (small family)
- 4+ matches = Low (large family)

### 4. Name Matching (Variable Confidence)
Word overlap similarity between product names.
```python
# Card name:     "Emma Leather Sofa"
# Modelbank name: "Emma Sofa"
# Word overlap: 66% (2/3 words)
# → MATCH (confidence by threshold)
```

## Project Structure

```
modelbank-card-matching/
├── config/                    # Configuration files
│   ├── retailers.yaml         # Retailer definitions
│   ├── matching_config.yaml   # Matching thresholds
│   └── api_credentials.yaml   # API keys (gitignored)
├── src/                       # Source code
│   ├── matchers/              # Matching algorithms
│   ├── enrichers/             # Card enrichment
│   ├── analyzers/             # Analysis & reports
│   ├── api/                   # API clients
│   └── cli.py                 # Command-line interface
├── scripts/                   # Shell scripts
├── tests/                     # Unit tests
├── docs/                      # Documentation
├── examples/                  # Example data
│   ├── bassett/               # Bassett case study
│   └── template/              # New retailer template
└── output_schemas/            # JSON schemas
```

## Configuration

### Add a New Retailer

1. Copy template configuration:
```bash
cp examples/template/config.yaml config/retailers/your-retailer.yaml
```

2. Edit with retailer details:
```yaml
your_retailer:
  supplier_id: 1234              # Modelbank supplier ID
  branding_id: 567890            # Floorplanner branding ID
  base_url: "https://..."        # Retailer website
  card_path: "/path/to/cards"    # Product cards location
  style_images_path: "/path/..."  # Style images (optional)
```

3. Run matching:
```bash
./scripts/run_matching.sh your_retailer
```

## Output Files

### 1. Matching Index (`*_matching_index.json`)
```json
{
  "summary": {
    "total_cardsets": 2103,
    "matched_total": 1207,
    "match_rate": 57.4
  },
  "matches": {
    "72445_cards_v6.md": {
      "model": "xxxx50618d..._28",
      "confidence": "high",
      "match_method": "url"
    }
  }
}
```

### 2. Style Mapping (`*_style_mapping.json`)
```json
{
  "styles": [
    {
      "style_name": "Blue Swedish Transitional",
      "modelbank_style_id": 6892,
      "products": [
        {"sku": "1342-3", "name": "Emmett Recliner"}
      ]
    }
  ]
}
```

### 3. Enriched Cards (v7)
```markdown
<!-- CARD:product-meta-emma-sofa -->
<!-- META: {
  "type": "product",
  "card_role": "meta",
  "model": "xxxx50618d..._28",
  "fp_url": "https://modelbank.floorplanner.com/products/xxxx50618d...",
  "is_private": true,
  "style": [
    {"style_id": 6892, "style_name": "Blue Swedish Transitional"}
  ],
  "related_products": ["1342-3-22", "1342-3L-53"]
} -->
```

## API Requirements

- **Modelbank API**: Product data, 3D models
  - Endpoint: `https://mb.floorplanner.com/api/v1/products/search.json`
  - Auth: Bearer token

- **Floorplanner Styles API**: Design styles taxonomy
  - Endpoint: `https://floorplanner.com/api/v2/styles.json`
  - Auth: Bearer token

See `config/api_credentials.example.yaml` for setup.

## Documentation

- [Methodology](docs/METHODOLOGY.md) - Matching algorithms in detail
- [Adding a Retailer](docs/ADDING_RETAILER.md) - Step-by-step guide
- [Card Schema](docs/CARD_SCHEMA.md) - Card v7 META structure
- [API Reference](docs/API_REFERENCE.md) - Function documentation

## Development

```bash
# Run tests
pytest tests/

# Run specific matcher tests
pytest tests/test_matchers.py

# Analyze existing results
python -m src.analyzers.confidence_breakdown results/bassett_matches.json
```

## Case Study: Bassett Furniture

Full example in `examples/bassett/`:
- 2,103 product cards
- 1,515 Modelbank products
- 75 design styles
- 57.4% match rate
- 15.4% high-confidence matches enriched

See [examples/bassett/README.md](examples/bassett/README.md) for details.

## License

[Your License Here]

## Contributing

Contributions welcome! Please read CONTRIBUTING.md first.

## Contact

[Your Contact Info]
