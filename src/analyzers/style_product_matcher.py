#!/usr/bin/env python3
"""
Style Product Matcher - Extract and match products mentioned in style/room cards
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict


class StyleProductMatcher:
    """Matcher for products mentioned in style/room pages"""

    def __init__(self, retailer_config: Dict):
        """
        Initialize style product matcher

        Args:
            retailer_config: Retailer configuration dict
        """
        self.retailer_config = retailer_config
        self.retailer_name = retailer_config['name']

    def load_style_sources(self, source_dir: str) -> List[Dict]:
        """
        Load style JSON source files

        Args:
            source_dir: Directory containing style JSON files

        Returns:
            List of style data dicts
        """
        source_path = Path(source_dir)
        if not source_path.exists():
            raise ValueError(f"Style source directory not found: {source_dir}")

        styles = []
        for json_file in source_path.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    styles.append({
                        'filename': json_file.name,
                        'title': data.get('title', ''),
                        'url': data.get('url', ''),
                        'card_type': data.get('card_type', 'style'),
                        'data': data
                    })
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
                continue

        print(f"Loaded {len(styles)} style source files")
        return styles

    def extract_product_ids(self, style_data: Dict) -> List[str]:
        """
        Extract ProductID values from style JSON

        Args:
            style_data: Style data dict

        Returns:
            List of product IDs
        """
        text_content = style_data['data'].get('html_extracted', {}).get('text_content', '')

        # Extract ProductID values from JSON-like structures
        product_ids = re.findall(r'\{ "name": "ProductID", "value": "([^"]+)" \}', text_content)

        return product_ids

    def build_product_indices(
        self,
        product_cards: List[Dict],
        mb_products: List[Dict]
    ) -> Tuple[Dict, Dict]:
        """
        Build indices for product lookup

        Args:
            product_cards: List of product card dicts
            mb_products: List of ModelBank product dicts

        Returns:
            Tuple of (card_index, mb_index)
        """
        card_index = defaultdict(list)
        mb_index = defaultdict(list)

        # Index product cards by SKU and normalized name
        for card in product_cards:
            # Extract SKUs from card
            skus = card.get('skus', [])
            for sku in skus:
                if sku:
                    # Add multiple variants for matching
                    for variant in self._sku_variants(sku):
                        card_index[variant].append(card)

            # Index by name
            name = card.get('name', '')
            if name:
                name_key = self._normalize_for_lookup(name)
                card_index[name_key].append(card)

        # Index ModelBank products by SKU and name
        for product in mb_products:
            sku = str(product.get('sku', '')).strip()
            if sku:
                for variant in self._sku_variants(sku):
                    mb_index[variant].append(product)

            name = product.get('name', '')
            if name:
                name_key = self._normalize_for_lookup(name)
                mb_index[name_key].append(product)

        print(f"Built indices: {len(card_index)} card entries, {len(mb_index)} ModelBank entries")
        return dict(card_index), dict(mb_index)

    def _sku_variants(self, sku: str) -> List[str]:
        """Generate SKU variants for matching"""
        variants = [sku, sku.lower(), sku.upper()]

        # Remove leading zeros
        variants.append(sku.lstrip('0'))

        # Extract base SKU (digits only)
        base = re.match(r'^(\d+)', sku)
        if base:
            variants.append(base.group(1))

        # Remove common separators
        clean = re.sub(r'[+\s-]+', '', sku)
        variants.append(clean)
        variants.append(clean.lower())

        return list(set(variants))

    def _normalize_for_lookup(self, text: str) -> str:
        """Normalize text for lookup"""
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove special chars, keep alphanumeric and spaces
        text = re.sub(r'[^a-z0-9\s]', '', text)

        # Normalize whitespace
        text = re.sub(r'\s+', '', text)

        return text

    def match_style_products(
        self,
        styles: List[Dict],
        card_index: Dict,
        mb_index: Dict
    ) -> Dict:
        """
        Match products referenced in styles to cards and ModelBank

        Args:
            styles: List of style data dicts
            card_index: Product card index
            mb_index: ModelBank product index

        Returns:
            Dict with matching results
        """
        results = {
            'total_styles': len(styles),
            'total_product_refs': 0,
            'matched_to_cards': 0,
            'matched_to_mb': 0,
            'unmatched': 0,
            'styles': []
        }

        for style in styles:
            product_ids = self.extract_product_ids(style)

            style_result = {
                'title': style['title'],
                'url': style['url'],
                'filename': style['filename'],
                'product_count': len(product_ids),
                'products': []
            }

            results['total_product_refs'] += len(product_ids)

            for pid in product_ids:
                match_result = self._match_product_id(pid, card_index, mb_index)
                style_result['products'].append(match_result)

                if match_result['card_match']:
                    results['matched_to_cards'] += 1
                if match_result['mb_match']:
                    results['matched_to_mb'] += 1
                if not match_result['card_match'] and not match_result['mb_match']:
                    results['unmatched'] += 1

            results['styles'].append(style_result)

        return results

    def _match_product_id(
        self,
        product_id: str,
        card_index: Dict,
        mb_index: Dict
    ) -> Dict:
        """
        Try to match a product ID to cards and ModelBank

        Args:
            product_id: Product ID to match
            card_index: Card lookup index
            mb_index: ModelBank lookup index

        Returns:
            Dict with match results
        """
        result = {
            'product_id': product_id,
            'card_match': None,
            'mb_match': None,
            'match_method': None
        }

        # Try exact match first
        if product_id in card_index:
            result['card_match'] = card_index[product_id][0]
            result['match_method'] = 'exact'
        elif product_id in mb_index:
            result['mb_match'] = mb_index[product_id][0]
            result['match_method'] = 'exact'
        else:
            # Try variants
            for variant in self._sku_variants(product_id):
                if variant in card_index:
                    result['card_match'] = card_index[variant][0]
                    result['match_method'] = 'variant'
                    break
                elif variant in mb_index:
                    result['mb_match'] = mb_index[variant][0]
                    result['match_method'] = 'variant'
                    break

            # Try normalized name matching
            if not result['card_match'] and not result['mb_match']:
                normalized = self._normalize_for_lookup(product_id)
                if normalized in card_index:
                    result['card_match'] = card_index[normalized][0]
                    result['match_method'] = 'name'
                elif normalized in mb_index:
                    result['mb_match'] = mb_index[normalized][0]
                    result['match_method'] = 'name'

        return result

    def generate_report(
        self,
        results: Dict,
        output_path: str
    ):
        """
        Generate style product matching report

        Args:
            results: Matching results dict
            output_path: Path to output report file
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Text report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Style Product Matching Report for {self.retailer_name}\n")
            f.write("=" * 80 + "\n\n")

            f.write("SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total style pages: {results['total_styles']}\n")
            f.write(f"Total product references: {results['total_product_refs']}\n")
            f.write(f"Matched to cards: {results['matched_to_cards']} ({results['matched_to_cards']/results['total_product_refs']*100:.1f}%)\n")
            f.write(f"Matched to ModelBank: {results['matched_to_mb']} ({results['matched_to_mb']/results['total_product_refs']*100:.1f}%)\n")
            f.write(f"Unmatched: {results['unmatched']} ({results['unmatched']/results['total_product_refs']*100:.1f}%)\n\n")

            f.write("STYLES WITH PRODUCTS\n")
            f.write("-" * 80 + "\n\n")

            for style in results['styles'][:30]:
                f.write(f"\n{style['title']}\n")
                f.write(f"  URL: {style['url']}\n")
                f.write(f"  Products: {style['product_count']}\n")

                # Show first few products
                for product in style['products'][:5]:
                    f.write(f"    - {product['product_id']}")
                    if product['card_match']:
                        card_name = product['card_match'].get('name', 'Unknown')
                        f.write(f" -> Card: {card_name}")
                    elif product['mb_match']:
                        mb_name = product['mb_match'].get('name', 'Unknown')
                        mb_sku = product['mb_match'].get('sku', '')
                        f.write(f" -> MB: {mb_name} (SKU: {mb_sku})")
                    else:
                        f.write(" -> NO MATCH")
                    f.write(f" ({product['match_method']})\n")

                if style['product_count'] > 5:
                    f.write(f"    ... and {style['product_count'] - 5} more\n")

        print(f"\nStyle product matching report saved to: {output_path}")

        # JSON report
        json_path = output_path.replace('.txt', '.json')

        # Prepare JSON-serializable version (remove full object references)
        json_results = {
            'retailer': self.retailer_name,
            'summary': {
                'total_styles': results['total_styles'],
                'total_product_refs': results['total_product_refs'],
                'matched_to_cards': results['matched_to_cards'],
                'matched_to_mb': results['matched_to_mb'],
                'unmatched': results['unmatched']
            },
            'styles': []
        }

        for style in results['styles']:
            style_data = {
                'title': style['title'],
                'url': style['url'],
                'filename': style['filename'],
                'product_count': style['product_count'],
                'products': []
            }

            for product in style['products']:
                product_data = {
                    'product_id': product['product_id'],
                    'match_method': product['match_method'],
                    'card_match': None,
                    'mb_match': None
                }

                if product['card_match']:
                    product_data['card_match'] = {
                        'filename': product['card_match'].get('filename'),
                        'name': product['card_match'].get('name'),
                        'skus': product['card_match'].get('skus', [])
                    }

                if product['mb_match']:
                    product_data['mb_match'] = {
                        'model_id': product['mb_match'].get('model'),
                        'name': product['mb_match'].get('name'),
                        'sku': product['mb_match'].get('sku')
                    }

                style_data['products'].append(product_data)

            json_results['styles'].append(style_data)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_results, f, indent=2)

        print(f"Style product matching JSON saved to: {json_path}")
