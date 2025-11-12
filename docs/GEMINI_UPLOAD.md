# Gemini Upload Guide

This guide explains how to upload your enriched product cards to Google's Gemini semantic retrieval API for use with AI assistants like Linda.

## Overview

After enriching your product cards with Modelbank metadata, you can upload them to Gemini's semantic search corpus. This enables:

- **Semantic search** across all product cards
- **Context retrieval** for AI assistants
- **Multi-retailer knowledge base** with consistent metadata
- **Fast, relevant results** for product queries

## Prerequisites

1. **Google Cloud account** with API access
2. **Gemini API key** - Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
3. **Enriched cards** - Run the enrichment pipeline first
4. **Python package** - Install `google-generativeai`

## Setup

### 1. Install Dependencies

```bash
pip install google-generativeai
```

### 2. Configure API Credentials

Edit `config/api_credentials.yaml` and add your Gemini credentials:

```yaml
gemini:
  api_key: "AIzaSy..."                    # Your Gemini API key
  project_id: "my-project-123"            # Your Google Cloud project ID
  corpus_id: ""                           # Leave empty for first upload
```

**Get your API key:**
1. Visit https://aistudio.google.com/app/apikey
2. Create new API key or use existing
3. Copy and paste into config file

**Project ID:**
- Use any identifier for your project (e.g., "modelbank-cards", "retailer-products")
- This groups your corpora together

**Corpus ID:**
- Leave empty on first upload (will be created automatically)
- After first upload, add the corpus ID here to reuse the same corpus

## Usage

### Quick Upload

```bash
# Upload enriched cards for a retailer
./scripts/upload_to_gemini.sh bassett

# Or use CLI directly
python3 src/cli.py bassett upload
```

### Custom Upload

```bash
# Upload from specific directory
python3 src/cli.py bassett upload -d /path/to/enriched_cards

# Use existing corpus
python3 src/cli.py bassett upload --corpus-id "corpora/my-corpus-123"

# Create new corpus with custom name
python3 src/cli.py bassett upload --corpus-name "Bassett Products 2024"

# Control upload rate
python3 src/cli.py bassett upload --batch-size 50 --rate-limit 2.0
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `-d, --directory` | Cards directory to upload | `{output_path}/enriched_cards` |
| `--corpus-id` | Existing corpus to upload to | From config or create new |
| `--corpus-name` | Name for new corpus | `{Retailer} Product Cards` |
| `--card-suffix` | Card file suffix | `_cards_v7.md` |
| `--batch-size` | Cards per batch | 100 |
| `--rate-limit` | Delay between batches (seconds) | 1.0 |

## What Gets Uploaded

Each card in your cardset is uploaded as a separate document with:

### Document Content
The full card content (markdown text) without META blocks

### Document Metadata
All metadata from the card's META block, including:
- `source_file` - Original filename
- `card_name` - Card identifier (e.g., "definition", "context")
- `card_type` - "product", "style", etc.
- `card_role` - "definition", "context", "meta", etc.
- `sku` - Product SKU
- `model` - Modelbank model ID (if enriched)
- `fp_url` - Modelbank URL (meta card only)
- `style` - Style assignments (meta card only)
- `related_products` - Related SKUs (meta card only)

### Example Document

```
Title: product:definition:1342-3

Content:
## **Emma Tufted Sofa**
A classic tufted sofa with elegant rolled arms...
**SKU:** 1342-3
**Price:** $1,999
...

Metadata:
{
  "source_file": "70254_cards_v7.md",
  "card_name": "definition",
  "card_type": "product",
  "card_role": "definition",
  "model": "xxxx50618d1ed4f46b2fd19c67ec06b3bd00f31b_28",
  "sku": "1342-3"
}
```

## First Upload

When uploading for the first time:

1. **Corpus is created automatically:**
   ```
   Creating Gemini corpus: Bassett Furniture Product Cards
   Created corpus: corpora/my-project-123/corpora/abc123xyz
   Add this to config/api_credentials.yaml under gemini.corpus_id to reuse
   ```

2. **Save the corpus ID:**
   Copy the corpus ID and add to `config/api_credentials.yaml`:
   ```yaml
   gemini:
     api_key: "AIzaSy..."
     project_id: "my-project-123"
     corpus_id: "corpora/my-project-123/corpora/abc123xyz"  # Add this
   ```

3. **Future uploads use the same corpus:**
   This updates your existing corpus instead of creating duplicates

## Upload Progress

The upload shows progress in real-time:

```
Uploading enriched cards for Bassett Furniture to Gemini...

Processing cards from /home/jeroen/clients/bassett/output/enriched_cards...
Found 324 files to process...
Processing: 70254_cards_v7.md
Processing: 70255_cards_v7.md
...
Extracted 1,620 total cards from 324 files

Uploading 1,620 cards to corpus corpora/my-project-123/corpora/abc123xyz
Batch size: 100, Rate limit delay: 1.0s

Processing batch 1/17 (100 cards)...
Processing batch 2/17 (100 cards)...
...

--- Upload Complete ---
Successfully uploaded: 1620
Failed: 0
Skipped: 0

Upload complete!
Corpus ID: corpora/my-project-123/corpora/abc123xyz
```

## Querying Your Corpus

Once uploaded, you can query your corpus:

```python
from uploaders.gemini_uploader import GeminiUploader

# Initialize
uploader = GeminiUploader(
    api_key="your-key",
    project_id="your-project",
    corpus_id="corpora/..."
)

# Query
results = uploader.query("modern leather sofa", top_k=5)

# Results include matching cards with relevance scores
for result in results:
    print(f"Score: {result.score}")
    print(f"Content: {result.text}")
    print(f"Metadata: {result.metadata}")
```

## Integration with Linda AI

Linda can now retrieve enriched product cards with Modelbank metadata:

**User Query:**
> "Show me modern leather sofas with the Emma style"

**Linda retrieves:**
- Cards matching "modern leather sofa"
- Filters by style assignment = "Emma"
- Returns product with Modelbank link, price, description
- Suggests related products from `related_products` field

**Example response:**
```
I found the Emma Tufted Sofa that matches perfectly:

- SKU: 1342-3
- Price: $1,999
- Style: Blue Swedish Transitional
- Modelbank 3D model: [View in Floorplanner](https://modelbank.floorplanner.com/...)

This sofa pairs well with:
- Langford Coffee Table (SKU: 6442-2)
- Winston Side Chair (SKU: 2571-K173CB)
```

## Multiple Retailers

You can create separate corpora for each retailer or combine them:

### Separate Corpora (Recommended)

```bash
# Upload each retailer to its own corpus
python3 src/cli.py bassett upload
python3 src/cli.py arhaus upload
python3 src/cli.py cb2 upload
```

Benefits:
- Easier to manage and update per retailer
- Can delete one retailer without affecting others
- Simpler access control

### Combined Corpus

```bash
# Upload all to same corpus
python3 src/cli.py bassett upload --corpus-id "corpora/all-retailers/abc123"
python3 src/cli.py arhaus upload --corpus-id "corpora/all-retailers/abc123"
python3 src/cli.py cb2 upload --corpus-id "corpora/all-retailers/abc123"
```

Benefits:
- Single search across all retailers
- Easier cross-retailer queries
- One API endpoint

Use metadata filters to query specific retailers:
```python
results = uploader.query(
    "modern sofa",
    metadata_filter={"source_file": "*bassett*"}
)
```

## Rate Limits

Google Gemini has API rate limits. Adjust upload settings if you hit limits:

```bash
# Slower, more conservative upload
python3 src/cli.py bassett upload --batch-size 50 --rate-limit 2.0
```

## Updating Cards

To update cards after re-enrichment:

**Option 1: Replace entire corpus**
```bash
# Delete old corpus via Gemini console
# Upload new cards (will create new corpus)
python3 src/cli.py bassett upload
```

**Option 2: Incremental updates**
Gemini automatically handles duplicates - uploading the same card twice updates it.

```bash
# Re-upload - updates existing cards
python3 src/cli.py bassett upload
```

## Troubleshooting

### "ImportError: No module named google.generativeai"
```bash
pip install google-generativeai
```

### "Error: gemini.api_key not configured"
Add your Gemini API key to `config/api_credentials.yaml`

### "Error: Cards directory not found"
Run enrichment first:
```bash
python3 src/cli.py bassett enrich
```

### "Failed to upload card: Rate limit exceeded"
Increase rate limit delay:
```bash
python3 src/cli.py bassett upload --rate-limit 5.0
```

### "Authentication failed"
- Verify API key is correct
- Check key has Generative AI API access enabled
- Visit [Google Cloud Console](https://console.cloud.google.com/apis/) to enable API

## Cost Considerations

Gemini pricing (as of 2024):
- **Semantic retrieval:** First 1M queries/month free
- **Storage:** Free for reasonable corpus sizes
- **Updates:** Free (included in query quota)

For 40 retailers × 2,000 products × 5 cards = **400,000 cards**, costs are minimal.

## Best Practices

1. **Upload v7 (enriched) cards** - Include Modelbank metadata for best results
2. **Use one corpus per retailer** - Easier management and updates
3. **Save corpus IDs** - Reuse existing corpora instead of creating duplicates
4. **Monitor upload failures** - Review failed cards and retry
5. **Test queries** - Verify semantic search works as expected
6. **Update regularly** - Re-upload after catalog changes or enrichment improvements

## Next Steps

After uploading:

1. **Test semantic search** - Query your corpus to verify it works
2. **Integrate with Linda** - Connect Linda AI to your Gemini corpus
3. **Monitor usage** - Track query volume and relevance
4. **Iterate on enrichment** - Improve metadata and re-upload
5. **Scale to all retailers** - Upload all 40 retailers' cards

Happy searching! 🚀
