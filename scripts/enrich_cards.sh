#!/bin/bash
#
# Enrich Cards - Enrich existing card files with Modelbank data
#
# Usage: ./scripts/enrich_cards.sh <retailer_name> [matches_file] [styles_file]
#

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <retailer_name> [matches_file] [styles_file]"
    echo "Example: $0 bassett"
    echo "Example: $0 bassett /path/to/matches.json /path/to/styles.json"
    exit 1
fi

RETAILER="$1"
MATCHES_FILE="$2"
STYLES_FILE="$3"

echo "Enriching cards for $RETAILER..."

CMD="python3 src/cli.py $RETAILER enrich"

if [ -n "$MATCHES_FILE" ]; then
    CMD="$CMD -m $MATCHES_FILE"
fi

if [ -n "$STYLES_FILE" ]; then
    CMD="$CMD -s $STYLES_FILE"
fi

eval $CMD

echo ""
echo "Done! Enriched cards saved to output directory."
echo ""
