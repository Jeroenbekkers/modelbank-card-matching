#!/bin/bash
#
# Full Pipeline - Run complete matching, enrichment, and analysis
#
# Usage: ./scripts/run_full_pipeline.sh <retailer_name>
#

set -e  # Exit on error

if [ -z "$1" ]; then
    echo "Usage: $0 <retailer_name>"
    echo "Example: $0 bassett"
    exit 1
fi

RETAILER="$1"

echo "========================================="
echo "FULL PIPELINE: $RETAILER"
echo "========================================="
echo ""

# 1. Match products
echo "Step 1/4: Matching products..."
python3 src/cli.py "$RETAILER" match
echo ""

# 2. Match styles
echo "Step 2/4: Matching styles..."
python3 src/cli.py "$RETAILER" match-styles || echo "Note: Style matching skipped (optional)"
echo ""

# 3. Enrich cards
echo "Step 3/4: Enriching cards..."
python3 src/cli.py "$RETAILER" enrich
echo ""

# 4. Generate reports
echo "Step 4/4: Generating analysis reports..."
python3 src/cli.py "$RETAILER" analyze
echo ""

echo "========================================="
echo "PIPELINE COMPLETE"
echo "========================================="
echo ""
echo "Results saved to output directory (check config/retailers.yaml)"
echo ""
