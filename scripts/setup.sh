#!/bin/bash
#
# Setup Script - Initialize the project
#

set -e

echo "========================================="
echo "MODELBANK CARD MATCHING - SETUP"
echo "========================================="
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $PYTHON_VERSION"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt
echo ""

# Create config files if they don't exist
echo "Setting up configuration files..."

if [ ! -f config/api_credentials.yaml ]; then
    echo "  Creating config/api_credentials.yaml from example..."
    cp config/api_credentials.example.yaml config/api_credentials.yaml
    echo "  ⚠️  IMPORTANT: Edit config/api_credentials.yaml and add your API credentials"
else
    echo "  ✓ config/api_credentials.yaml already exists"
fi

if [ ! -f config/retailers.yaml ]; then
    echo "  Creating config/retailers.yaml from example..."
    cp config/retailers.example.yaml config/retailers.yaml
    echo "  ⚠️  IMPORTANT: Edit config/retailers.yaml and configure your retailer(s)"
else
    echo "  ✓ config/retailers.yaml already exists"
fi

echo ""
echo "========================================="
echo "SETUP COMPLETE"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Edit config/api_credentials.yaml - Add your Modelbank/Floorplanner API credentials"
echo "  2. Edit config/retailers.yaml - Configure your retailer details"
echo "  3. Run a test: python3 src/cli.py <retailer_name> match"
echo ""
echo "For more information, see README.md"
echo ""
