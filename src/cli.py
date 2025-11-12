#!/usr/bin/env python3
"""
Modelbank Card Matching - Command Line Interface
"""

import os
import sys
import json
import yaml
import argparse
from pathlib import Path
from typing import Dict, Optional

from api.modelbank_client import ModelbankClient
from matchers.product_matcher import ProductMatcher
from matchers.style_matcher import StyleMatcher
from enrichers.card_enricher import CardEnricher
from analyzers.report_generator import ReportGenerator
from uploaders.gemini_uploader import GeminiUploader


class CLI:
    """Command-line interface for modelbank matching"""

    def __init__(self):
        """Initialize CLI"""
        self.config = {}
        self.credentials = {}

    def load_config(self, retailer: str):
        """Load configuration files"""
        # Load credentials
        creds_file = Path("config/api_credentials.yaml")
        if not creds_file.exists():
            print(f"Error: {creds_file} not found. Copy api_credentials.example.yaml and fill in your credentials.")
            sys.exit(1)

        with open(creds_file) as f:
            self.credentials = yaml.safe_load(f)

        # Load retailers config
        retailers_file = Path("config/retailers.yaml")
        if not retailers_file.exists():
            print(f"Error: {retailers_file} not found. Copy retailers.example.yaml and configure your retailer.")
            sys.exit(1)

        with open(retailers_file) as f:
            retailers_config = yaml.safe_load(f)

        if retailer not in retailers_config:
            print(f"Error: Retailer '{retailer}' not found in config/retailers.yaml")
            print(f"Available retailers: {', '.join(retailers_config.keys())}")
            sys.exit(1)

        self.config = retailers_config[retailer]
        self.config['name'] = retailer
        self.config['display_name'] = self.config.get('name', retailer)

    def cmd_match(self, args):
        """Run product matching"""
        print(f"Matching products for {self.config['display_name']}...")
        print()

        # Initialize API client
        mb_config = self.credentials.get('modelbank', {})
        client = ModelbankClient(
            api_url=mb_config['api_url'],
            auth_token=mb_config['auth_token']
        )

        # Fetch products from Modelbank
        print(f"Fetching products for supplier_id={self.config['supplier_id']}...")
        products = client.fetch_products_by_supplier(
            supplier_id=self.config['supplier_id']
        )
        print(f"Fetched {len(products)} products from Modelbank")
        print()

        # Load product cards
        print(f"Loading product cards from {self.config['card_path']}...")
        style_matcher = StyleMatcher()
        card_suffix = args.card_suffix or '_cards_v6.md'
        cards = style_matcher.load_product_cards(
            self.config['card_path'],
            card_suffix=card_suffix
        )
        print(f"Loaded {len(cards)} product cards")
        print()

        # Initialize matcher
        matching_config = self.config.get('matching', {})
        matcher = ProductMatcher(matching_config)

        # Build SKU variant index
        print("Building SKU variant index...")
        sku_index = matcher.build_sku_variant_index(products)
        print()

        # Match products
        print("Matching products...")
        matches_output = {
            'retailer': self.config['display_name'],
            'supplier_id': self.config['supplier_id'],
            'total_cards': len(cards),
            'total_modelbank_products': len(products),
            'matches': []
        }

        match_count = 0
        for card_file, card_data in cards.items():
            card_url = card_data.get('url', '')
            card_sku = card_data.get('sku', '')
            card_name = card_data.get('name', '')

            # Try matching methods in priority order
            matched_products = []
            match_method = None
            confidence = None

            # 1. URL matching
            if card_url:
                matched_products = matcher.match_by_url(card_url, products)
                if matched_products:
                    match_method = 'url'
                    confidence = 'high'

            # 2. Exact SKU matching
            if not matched_products and card_sku:
                matched_products = matcher.match_by_sku_exact(card_sku, products)
                if matched_products:
                    match_method = 'sku'
                    confidence = 'high'

            # 3. Fuzzy SKU matching
            if not matched_products and card_sku:
                matched_products = matcher.match_by_sku_fuzzy(card_sku, sku_index)
                if matched_products:
                    match_method = 'sku_fuzzy'
                    confidence = matcher.assign_confidence(match_method, len(matched_products))

            # 4. Name matching
            if not matched_products and card_name:
                name_matches = matcher.match_by_name(card_name, products)
                if name_matches:
                    matched_products = [m[0] for m in name_matches[:5]]  # Top 5
                    similarity = name_matches[0][1]
                    match_method = 'name'
                    confidence = matcher.assign_confidence(match_method, len(matched_products), similarity)

            # Record result
            match_result = {
                'cardset': {
                    'file_name': card_file,
                    'card_sku': card_sku,
                    'card_name': card_name,
                    'card_url': card_url
                },
                'matched': len(matched_products) > 0,
                'match_method': match_method,
                'confidence': confidence,
                'matches': matched_products
            }

            matches_output['matches'].append(match_result)

            if matched_products:
                match_count += 1

        print(f"Matched {match_count}/{len(cards)} products ({match_count/len(cards)*100:.1f}%)")
        print()

        # Save results
        output_file = args.output or f"{self.config['output_path']}/matches.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(matches_output, f, indent=2)

        print(f"Results saved to: {output_file}")

        # Quick summary
        report_gen = ReportGenerator()
        report_gen.print_quick_summary(matches_output)

    def cmd_match_styles(self, args):
        """Run style matching"""
        print(f"Matching styles for {self.config['display_name']}...")
        print()

        # Check if style images path exists
        style_path = self.config.get('style_images_path')
        if not style_path or not os.path.exists(style_path):
            print(f"Error: style_images_path not configured or not found")
            sys.exit(1)

        # Initialize API client
        mb_config = self.credentials.get('modelbank', {})
        client = ModelbankClient(
            api_url=mb_config['api_url'],
            auth_token=mb_config['auth_token']
        )

        # Fetch styles from Modelbank
        branding_id = self.config.get('branding_id')
        if not branding_id:
            print("Warning: branding_id not configured, fetching all styles")

        print(f"Fetching styles (branding_id={branding_id})...")
        styles_list = client.fetch_styles(branding_id=branding_id)
        print(f"Fetched {len(styles_list)} styles from Modelbank")
        print()

        # Build style name → ID mapping
        style_map = {s['name']: s['id'] for s in styles_list}

        # Initialize style matcher
        style_matcher = StyleMatcher()

        # Get style folders
        print(f"Scanning style folders in {style_path}...")
        style_folders = style_matcher.get_style_folders(style_path)
        print(f"Found {len(style_folders)} style folders with ORIGINAL images")
        print()

        # Load product cards
        print(f"Loading product cards from {self.config['card_path']}...")
        card_suffix = args.card_suffix or '_cards_v6.md'
        products = style_matcher.load_product_cards(
            self.config['card_path'],
            card_suffix=card_suffix
        )
        print(f"Loaded {len(products)} product cards")
        print()

        # Build style-product mapping
        print("Mapping styles to products...")
        style_mappings = style_matcher.build_style_product_mapping(
            style_folders,
            products,
            style_map
        )

        # Calculate statistics
        total_matches = sum(s['matched_products_count'] for s in style_mappings)
        styles_with_matches = sum(1 for s in style_mappings if s['matched_products_count'] > 0)

        print(f"Mapped {total_matches} products across {styles_with_matches}/{len(style_mappings)} styles")
        print()

        # Save results
        output_file = args.output or f"{self.config['output_path']}/style_mappings.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        output_data = {
            'retailer': self.config['display_name'],
            'branding_id': branding_id,
            'summary': {
                'total_styles': len(style_mappings),
                'styles_with_matches': styles_with_matches,
                'total_product_matches': total_matches
            },
            'styles': style_mappings
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"Results saved to: {output_file}")

    def cmd_enrich(self, args):
        """Enrich cards with Modelbank data"""
        print(f"Enriching cards for {self.config['display_name']}...")
        print()

        # Load match results
        matches_file = args.matches or f"{self.config['output_path']}/matches.json"
        if not os.path.exists(matches_file):
            print(f"Error: Match results not found: {matches_file}")
            print("Run 'match' command first")
            sys.exit(1)

        with open(matches_file) as f:
            matches = json.load(f)

        # Load style mappings (optional)
        style_file = args.styles or f"{self.config['output_path']}/style_mappings.json"
        style_mappings = None
        if os.path.exists(style_file):
            with open(style_file) as f:
                style_mappings = json.load(f)

            # Enrich matches with style information
            print("Enriching matches with style information...")
            style_matcher = StyleMatcher()
            product_to_style = style_matcher.build_product_to_style_index(
                style_mappings.get('styles', [])
            )

            for match in matches['matches']:
                if not match.get('matched'):
                    continue
                filename = match['cardset'].get('file_name')
                if filename in product_to_style:
                    match['styles'] = product_to_style[filename]

        # Initialize enricher
        enricher_config = self.config.get('enrichment', {})
        enricher = CardEnricher(enricher_config)

        # Build enrichment index
        print("Building enrichment index...")
        enrichment_index = enricher.build_enrichment_index(matches)
        print(f"Built enrichment for {len(enrichment_index)} products")
        print()

        # Enrich cards
        input_dir = self.config['card_path']
        output_dir = args.output or f"{self.config['output_path']}/enriched_cards"
        input_suffix = args.input_suffix or '_cards_v6.md'
        output_suffix = args.output_suffix or '_cards_v7.md'

        print(f"Enriching cards from {input_dir}...")
        print(f"Output directory: {output_dir}")
        print()

        results = enricher.enrich_card_directory(
            input_dir,
            output_dir,
            enrichment_index,
            input_suffix,
            output_suffix
        )

        print(f"Enriched: {results['enriched']} files")
        print(f"Copied unchanged: {results['copied']} files")
        print(f"Total: {results['total']} files")

    def cmd_analyze(self, args):
        """Analyze matching results"""
        print(f"Analyzing results for {self.config['display_name']}...")
        print()

        # Load match results
        matches_file = args.matches or f"{self.config['output_path']}/matches.json"
        if not os.path.exists(matches_file):
            print(f"Error: Match results not found: {matches_file}")
            sys.exit(1)

        with open(matches_file) as f:
            matches = json.load(f)

        # Load style mappings (optional)
        style_file = args.styles or f"{self.config['output_path']}/style_mappings.json"
        style_mappings = None
        if os.path.exists(style_file):
            with open(style_file) as f:
                style_mappings = json.load(f)

        # Generate report
        report_gen = ReportGenerator()
        output_base = args.output or f"{self.config['output_path']}/report"
        format = args.format or 'both'

        report_gen.save_report(
            matches,
            output_base,
            style_mappings,
            self.config['display_name'],
            format
        )

    def cmd_upload(self, args):
        """Upload enriched cards to Gemini"""
        print(f"Uploading cards for {self.config['display_name']} to Gemini...")
        print()

        # Check Gemini config
        gemini_config = self.credentials.get('gemini')
        if not gemini_config:
            print("Error: Gemini configuration not found in config/api_credentials.yaml")
            print("Add a 'gemini:' section with api_key, project_id, and optionally corpus_id")
            sys.exit(1)

        api_key = gemini_config.get('api_key')
        project_id = gemini_config.get('project_id')
        corpus_id = gemini_config.get('corpus_id')

        if not api_key:
            print("Error: gemini.api_key not configured")
            sys.exit(1)

        if not project_id:
            print("Error: gemini.project_id not configured")
            sys.exit(1)

        # Initialize uploader
        try:
            uploader = GeminiUploader(
                api_key=api_key,
                project_id=project_id,
                corpus_id=corpus_id
            )
        except ImportError as e:
            print(f"Error: {e}")
            print("Install with: pip install google-generativeai")
            sys.exit(1)

        # Create corpus if needed
        if not corpus_id and not args.corpus_id:
            corpus_name = args.corpus_name or f"{self.config['display_name']} Product Cards"
            corpus_id = uploader.create_corpus(
                display_name=corpus_name,
                description=f"Enriched product cards for {self.config['display_name']}"
            )
            print(f"Created new corpus: {corpus_id}")
            print(f"Add this to config/api_credentials.yaml under gemini.corpus_id to reuse")
            print()
        elif args.corpus_id:
            uploader.corpus_id = args.corpus_id
            print(f"Using specified corpus: {args.corpus_id}")

        # Get cards directory
        cards_dir = args.directory or f"{self.config['output_path']}/enriched_cards"
        if not os.path.exists(cards_dir):
            print(f"Error: Cards directory not found: {cards_dir}")
            print("Run 'enrich' command first")
            sys.exit(1)

        # Process cards
        card_suffix = args.card_suffix or '_cards_v7.md'
        print(f"Processing cards from {cards_dir}...")
        cards = uploader.process_card_directory(cards_dir, card_suffix=card_suffix)

        if not cards:
            print("No cards found to upload")
            sys.exit(0)

        # Upload
        batch_size = args.batch_size or 100
        rate_limit = args.rate_limit or 1.0

        results = uploader.upload_cards(
            cards,
            batch_size=batch_size,
            rate_limit_delay=rate_limit
        )

        print()
        print(f"Upload complete!")
        print(f"Corpus ID: {uploader.corpus_id}")

    def run(self):
        """Run CLI"""
        parser = argparse.ArgumentParser(
            description="Modelbank Card Matching - Match retailer product cards to Modelbank"
        )

        parser.add_argument(
            'retailer',
            help="Retailer name (must be configured in config/retailers.yaml)"
        )

        subparsers = parser.add_subparsers(dest='command', help='Command to run')

        # Match command
        match_parser = subparsers.add_parser('match', help='Match products to Modelbank')
        match_parser.add_argument('-o', '--output', help='Output file path')
        match_parser.add_argument('--card-suffix', help='Card file suffix (default: _cards_v6.md)')

        # Match styles command
        styles_parser = subparsers.add_parser('match-styles', help='Match styles to products')
        styles_parser.add_argument('-o', '--output', help='Output file path')
        styles_parser.add_argument('--card-suffix', help='Card file suffix (default: _cards_v6.md)')

        # Enrich command
        enrich_parser = subparsers.add_parser('enrich', help='Enrich cards with Modelbank data')
        enrich_parser.add_argument('-m', '--matches', help='Path to matches.json')
        enrich_parser.add_argument('-s', '--styles', help='Path to style_mappings.json')
        enrich_parser.add_argument('-o', '--output', help='Output directory')
        enrich_parser.add_argument('--input-suffix', help='Input card suffix (default: _cards_v6.md)')
        enrich_parser.add_argument('--output-suffix', help='Output card suffix (default: _cards_v7.md)')

        # Analyze command
        analyze_parser = subparsers.add_parser('analyze', help='Analyze matching results')
        analyze_parser.add_argument('-m', '--matches', help='Path to matches.json')
        analyze_parser.add_argument('-s', '--styles', help='Path to style_mappings.json')
        analyze_parser.add_argument('-o', '--output', help='Output file base path')
        analyze_parser.add_argument('-f', '--format', choices=['text', 'json', 'both'],
                                   help='Report format (default: both)')

        # Upload command
        upload_parser = subparsers.add_parser('upload', help='Upload enriched cards to Gemini')
        upload_parser.add_argument('-d', '--directory', help='Cards directory (default: output/enriched_cards)')
        upload_parser.add_argument('--corpus-id', help='Existing corpus ID to upload to')
        upload_parser.add_argument('--corpus-name', help='Corpus name (if creating new)')
        upload_parser.add_argument('--card-suffix', help='Card file suffix (default: _cards_v7.md)')
        upload_parser.add_argument('--batch-size', type=int, help='Upload batch size (default: 100)')
        upload_parser.add_argument('--rate-limit', type=float, help='Rate limit delay in seconds (default: 1.0)')

        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            sys.exit(1)

        # Load config
        self.load_config(args.retailer)

        # Run command
        if args.command == 'match':
            self.cmd_match(args)
        elif args.command == 'match-styles':
            self.cmd_match_styles(args)
        elif args.command == 'enrich':
            self.cmd_enrich(args)
        elif args.command == 'analyze':
            self.cmd_analyze(args)
        elif args.command == 'upload':
            self.cmd_upload(args)


def main():
    """Main entry point"""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
