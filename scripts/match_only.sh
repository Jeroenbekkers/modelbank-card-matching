#!/bin/bash
#
# Match Only - Run product matching without enrichment
#
# Usage: ./scripts/match_only.sh <retailer_name>
#

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <retailer_name>"
    echo "Example: $0 bassett"
    exit 1
fi

RETAILER="$1"

echo "Matching products for $RETAILER..."
python3 src/cli.py "$RETAILER" match

echo ""
echo "Done! Run analyze to see detailed results:"
echo "  python3 src/cli.py $RETAILER analyze"
echo ""
