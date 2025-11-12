#!/usr/bin/env python3
"""
Reverse Matcher - Find ModelBank items without cards
Analyzes orphaned products and materials in ModelBank
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict


class ReverseMatcher:
    """Reverse matcher to find ModelBank items without cards"""

    def __init__(self, retailer_config: Dict):
        """
        Initialize reverse matcher

        Args:
            retailer_config: Retailer configuration dict
        """
        self.retailer_config = retailer_config
        self.retailer_name = retailer_config['name']

    def load_all_cards(self) -> Dict[str, List[Dict]]:
        """
        Load all cards from all directories

        Returns:
            Dict mapping card type to list of card info
        """
        cards_path = self.retailer_config.get('card_path')
        if not cards_path:
            raise ValueError("No card_path in retailer config")

        # Get parent directory if card_path points to product directory
        cards_dir = Path(cards_path).parent if Path(cards_path).name == 'product' else Path(cards_path)

        all_cards = {}

        # Load from each subdirectory
        for subdir in ['product', 'material', 'collection', 'style', 'content']:
            card_dir = cards_dir / subdir
            if not card_dir.exists():
                continue

            cards = []
            for card_file in card_dir.glob('*.md'):
                try:
                    with open(card_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Extract SKUs from filename and content
                    filename_skus = set(re.findall(r'-(\d{5,7})-', card_file.stem))
                    content_skus = set(re.findall(r'(?:SKU|Item)[:\s]+(\d{5,7})', content, re.IGNORECASE))
                    all_skus = filename_skus | content_skus

                    # Extract name from first bold text
                    name_match = re.search(r'\*\*(.+?)\*\*', content)
                    name = name_match.group(1) if name_match else ""

                    # Extract URL
                    url_match = re.search(r'source_url:\s*(.+)', content)
                    url = url_match.group(1).strip() if url_match else None

                    cards.append({
                        'filename': card_file.name,
                        'name': name,
                        'skus': list(all_skus),
                        'url': url,
                        'content_preview': content[:200]
                    })

                except Exception as e:
                    print(f"Error loading {card_file}: {e}")
                    continue

            all_cards[subdir] = cards
            print(f"Loaded {len(cards)} cards from {subdir}/")

        return all_cards

    def build_card_indices(self, all_cards: Dict[str, List[Dict]]) -> Tuple[Dict, Dict]:
        """
        Build indices for fast card lookup

        Args:
            all_cards: Cards organized by type

        Returns:
            Tuple of (sku_index, name_index)
        """
        sku_index = {}  # SKU -> list of cards
        name_index = {}  # normalized name -> list of cards

        for card_type, cards in all_cards.items():
            for card in cards:
                # Index by SKU
                for sku in card['skus']:
                    if sku not in sku_index:
                        sku_index[sku] = []
                    sku_index[sku].append({**card, 'card_type': card_type})

                # Index by name
                if card['name']:
                    name_key = self._normalize_name(card['name'])
                    if name_key not in name_index:
                        name_index[name_key] = []
                    name_index[name_key].append({**card, 'card_type': card_type})

        return sku_index, name_index

    def _normalize_name(self, name: str) -> str:
        """Normalize name for matching"""
        if not name:
            return ""
        # Remove common suffixes and normalize
        name = name.lower()
        name = re.sub(r'\s+(fabric|leather|finish|material|pillow|mirror)$', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def reverse_match_products(
        self,
        mb_products: List[Dict],
        matched_product_ids: Set[str],
        sku_index: Dict,
        name_index: Dict
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Reverse match orphaned products to cards

        Args:
            mb_products: All ModelBank products
            matched_product_ids: Set of already matched model IDs
            sku_index: SKU to cards index
            name_index: Name to cards index

        Returns:
            Tuple of (reverse_matches, truly_orphaned)
        """
        reverse_matches = []
        truly_orphaned = []

        for product in mb_products:
            model_id = product.get('model')
            if model_id in matched_product_ids:
                continue  # Already matched in forward pass

            sku = str(product.get('sku', '')).strip()
            name = product.get('name', '')

            # Try multiple matching strategies
            match_info = self._try_match_product(product, sku, name, sku_index, name_index)

            if match_info:
                reverse_matches.append({
                    'mb_product': {
                        'model_id': model_id,
                        'name': name,
                        'sku': sku,
                        'url': product.get('url'),
                        'status': product.get('status'),
                        'created_at': product.get('created_at')
                    },
                    'card': match_info['card'],
                    'match_method': match_info['method'],
                    'confidence': match_info['confidence']
                })
            else:
                truly_orphaned.append({
                    'model_id': model_id,
                    'name': name,
                    'sku': sku,
                    'url': product.get('url'),
                    'status': product.get('status'),
                    'category': self._categorize_orphaned_product(product)
                })

        return reverse_matches, truly_orphaned

    def _try_match_product(self, product: Dict, sku: str, name: str, sku_index: Dict, name_index: Dict) -> Dict:
        """Try to match a product using multiple strategies"""

        # Strategy 1: Exact SKU match
        if sku and sku in sku_index:
            return {
                'card': sku_index[sku][0],
                'method': 'exact_sku',
                'confidence': 'high'
            }

        # Strategy 2: SKU without suffix (e.g., "074138 BRS" -> "074138")
        sku_base = re.match(r'^(\d{5,7})', sku)
        if sku_base and sku_base.group(1) in sku_index:
            return {
                'card': sku_index[sku_base.group(1)][0],
                'method': 'sku_base',
                'confidence': 'medium'
            }

        # Strategy 3: Exact name match
        name_key = self._normalize_name(name)
        if name_key and name_key in name_index:
            return {
                'card': name_index[name_key][0],
                'method': 'exact_name',
                'confidence': 'high'
            }

        # Strategy 4: Fuzzy name match (word overlap)
        if name:
            name_words = set(name.lower().split())
            for card_name_key, cards in name_index.items():
                card_words = set(card_name_key.split())
                overlap = name_words & card_words
                if len(overlap) >= min(3, len(name_words) * 0.7):
                    return {
                        'card': cards[0],
                        'method': 'fuzzy_name',
                        'confidence': 'low'
                    }

        return None

    def _categorize_orphaned_product(self, product: Dict) -> str:
        """Categorize orphaned product by type"""
        name = product.get('name', '').lower()
        sku = product.get('sku') or ''

        # Check for sectional components
        if any(word in name for word in ['laf', 'raf', 'armless', 'corner', 'wedge', 'cst']):
            return 'sectional_component'

        # Check for accessories
        if any(word in name for word in ['mirror', 'pillow', 'pendant', 'sculpture', 'art', 'decor']):
            return 'accessory'

        # Check for color/finish variants (SKU has suffix)
        if sku and re.search(r'[A-Z]{3}$', str(sku)):  # Ends with 3 letter code
            return 'finish_variant'

        # Check for size variants
        if re.search(r'\d+["\']', name):  # Has dimension in name
            return 'size_variant'

        return 'unknown'

    def reverse_match_materials(
        self,
        mb_materials: List[Dict],
        matched_material_ids: Set[int],
        sku_index: Dict,
        name_index: Dict
    ) -> Tuple[List[Dict], List[Dict]]:
        """Reverse match orphaned materials to cards"""
        reverse_matches = []
        truly_orphaned = []

        for material in mb_materials:
            mat_id = material.get('id')
            if mat_id in matched_material_ids:
                continue

            sku = str(material.get('sku', '')).strip()
            name = material.get('name', '')

            match_info = self._try_match_product(material, sku, name, sku_index, name_index)

            if match_info:
                reverse_matches.append({
                    'mb_material': {
                        'id': mat_id,
                        'name': name,
                        'sku': sku,
                        'kind': material.get('kind')
                    },
                    'card': match_info['card'],
                    'match_method': match_info['method']
                })
            else:
                truly_orphaned.append({
                    'id': mat_id,
                    'name': name,
                    'sku': sku,
                    'kind': material.get('kind')
                })

        return reverse_matches, truly_orphaned

    def generate_report(
        self,
        product_reverse: Tuple[List, List],
        material_reverse: Tuple[List, List],
        output_path: str
    ):
        """Generate reverse matching report"""
        import json

        prod_matches, prod_orphaned = product_reverse
        mat_matches, mat_orphaned = material_reverse

        # Categorize orphaned products
        orphaned_by_category = defaultdict(list)
        for orphan in prod_orphaned:
            orphaned_by_category[orphan['category']].append(orphan)

        # Text report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Reverse Matching Report for {self.retailer_name}\n")
            f.write("=" * 80 + "\n\n")

            f.write("PRODUCTS\n")
            f.write("-" * 80 + "\n\n")
            f.write(f"Reverse matches found: {len(prod_matches)}\n")
            f.write(f"Truly orphaned: {len(prod_orphaned)}\n\n")

            if prod_matches:
                f.write("Sample reverse matches:\n")
                for match in prod_matches[:20]:
                    f.write(f"  {match['mb_product']['name'][:45]:45} SKU: {match['mb_product']['sku']}\n")
                    f.write(f"    -> Card: {match['card']['filename']} ({match['match_method']})\n\n")

            f.write("\nOrphaned Products by Category:\n")
            for category, items in sorted(orphaned_by_category.items(), key=lambda x: len(x[1]), reverse=True):
                f.write(f"\n  {category}: {len(items)} items\n")
                for item in items[:10]:
                    f.write(f"    {item['name'][:50]:50} SKU: {item['sku']}\n")

            f.write("\n\nMATERIALS\n")
            f.write("-" * 80 + "\n\n")
            f.write(f"Reverse matches found: {len(mat_matches)}\n")
            f.write(f"Truly orphaned: {len(mat_orphaned)}\n\n")

            if mat_orphaned:
                f.write("Sample orphaned materials:\n")
                for mat in mat_orphaned[:30]:
                    f.write(f"  {mat['name'][:40]:40} SKU: {mat['sku']:15} Kind: {mat['kind']}\n")

        print(f"\nReverse matching report saved to: {output_path}")

        # JSON report
        json_path = output_path.replace('.txt', '.json')
        json_data = {
            'retailer': self.retailer_name,
            'products': {
                'reverse_matches': prod_matches,
                'orphaned': prod_orphaned,
                'orphaned_by_category': {k: len(v) for k, v in orphaned_by_category.items()}
            },
            'materials': {
                'reverse_matches': mat_matches,
                'orphaned': mat_orphaned
            },
            'summary': {
                'product_reverse_matches': len(prod_matches),
                'product_orphaned': len(prod_orphaned),
                'material_reverse_matches': len(mat_matches),
                'material_orphaned': len(mat_orphaned)
            }
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)

        print(f"Reverse matching JSON saved to: {json_path}")
