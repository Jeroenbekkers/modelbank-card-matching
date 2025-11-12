#!/bin/bash
#
# Upload Cards to Gemini - Upload enriched cards to Gemini semantic retrieval
#
# Usage: ./scripts/upload_to_gemini.sh <retailer_name> [cards_directory]
#

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <retailer_name> [cards_directory]"
    echo "Example: $0 bassett"
    echo "Example: $0 bassett /path/to/enriched_cards"
    exit 1
fi

RETAILER="$1"
CARDS_DIR="$2"

echo "Uploading enriched cards for $RETAILER to Gemini..."

CMD="python3 src/cli.py $RETAILER upload"

if [ -n "$CARDS_DIR" ]; then
    CMD="$CMD -d $CARDS_DIR"
fi

eval $CMD

echo ""
echo "Done! Cards are now searchable in Gemini."
echo ""
