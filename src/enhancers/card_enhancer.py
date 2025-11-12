#!/usr/bin/env python3
"""
Card Enhancer - Add ModelBank metadata to cards
Enhances v6 cards with Floorplanner/ModelBank integration data
"""

import os
import re
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class CardEnhancer:
    """Enhancer to add ModelBank metadata to cards"""

    def __init__(self, retailer_config: Dict):
        """
        Initialize card enhancer

        Args:
            retailer_config: Retailer configuration dict
        """
        self.retailer_config = retailer_config
        self.retailer_name = retailer_config['name']

    def load_matching_data(
        self,
        product_matches_path: str,
        material_matches_path: str,
        style_products_path: str
    ) -> Tuple[Dict, Dict, Dict]:
        """
        Load all matching data

        Args:
            product_matches_path: Path to product matches JSON
            material_matches_path: Path to material matches JSON
            style_products_path: Path to style products JSON

        Returns:
            Tuple of (product_lookup, material_lookup, style_lookup)
        """
        # Load product matches
        with open(product_matches_path, 'r') as f:
            product_data = json.load(f)

        # Build product lookup by card filename
        product_lookup = {}
        for match in product_data['matches']:
            if match['matched'] and match['matches']:
                card_file = match['cardset']['file_name']
                mb_product = match['matches'][0]
                product_lookup[card_file] = {
                    'mb_product': mb_product,
                    'confidence': match['confidence'],
                    'match_method': match['match_method']
                }

        print(f"Loaded {len(product_lookup)} product matches")

        # Load material matches
        with open(material_matches_path, 'r') as f:
            material_data = json.load(f)

        material_lookup = {}
        for match in material_data['matches']:
            card_file = match['card_filename']
            material_lookup[card_file] = {
                'mb_id': match['mb_id'],
                'mb_sku': match['mb_sku'],
                'mb_name': match['mb_name'],
                'mb_kind': match['mb_kind'],
                'match_type': match['match_type']
            }

        print(f"Loaded {len(material_lookup)} material matches")

        # Load style products
        with open(style_products_path, 'r') as f:
            style_data = json.load(f)

        # Build lookup for products featured in styles
        product_to_styles = defaultdict(list)
        style_lookup = {}

        for style in style_data['styles']:
            style_info = {
                'title': style['title'],
                'url': style['url'],
                'filename': style['filename']
            }

            style_products = []
            for product in style['products']:
                product_info = {
                    'product_id': product['product_id'],
                    'match_method': product['match_method']
                }

                if product['card_match']:
                    card_file = product['card_match']['filename']
                    product_info['card_file'] = card_file
                    product_to_styles[card_file].append({
                        'title': style['title'],
                        'url': style['url']
                    })

                if product['mb_match']:
                    product_info['model_id'] = product['mb_match']['model_id']
                    product_info['mb_name'] = product['mb_match']['name']

                style_products.append(product_info)

            style_lookup[style['filename']] = {
                'style_info': style_info,
                'products': style_products,
                'total_products': style['product_count']
            }

        print(f"Loaded {len(style_lookup)} styles")
        print(f"Found {len(product_to_styles)} products featured in styles")

        return product_lookup, material_lookup, (style_lookup, product_to_styles)

    def enhance_card(
        self,
        card_content: str,
        card_type: str,
        card_filename: str,
        product_lookup: Dict,
        material_lookup: Dict,
        style_data: Tuple[Dict, Dict]
    ) -> Tuple[str, bool]:
        """
        Enhance a single card with ModelBank metadata

        Args:
            card_content: Original card content
            card_type: Type of card (product/material/style)
            card_filename: Card filename
            product_lookup: Product matching data
            material_lookup: Material matching data
            style_data: Style matching data

        Returns:
            Tuple of (enhanced_content, was_modified)
        """
        style_lookup, product_to_styles = style_data

        # Parse all cards in the file
        cards = self._parse_cards(card_content)
        modified = False

        for i, card in enumerate(cards):
            if card['role'] == 'meta':
                # This is the meta card - enhance it
                enhanced_meta = self._enhance_meta_card(
                    card,
                    card_type,
                    card_filename,
                    product_lookup,
                    material_lookup,
                    style_data
                )
                if enhanced_meta != card['meta']:
                    cards[i]['meta'] = enhanced_meta
                    modified = True
            elif card['role'] in ['definition', 'context', 'data', 'procedure', 'exception', 'decision', 'example']:
                # Add model ID to regular cards if available
                if card_type == 'product' and card_filename in product_lookup:
                    model_id = product_lookup[card_filename]['mb_product'].get('model')
                    if model_id and 'model' not in card['meta']:
                        card['meta']['model'] = model_id
                        modified = True

        if modified:
            # Rebuild card content
            new_content = self._rebuild_card_content(cards)
            return new_content, True

        return card_content, False

    def _parse_cards(self, content: str) -> List[Dict]:
        """Parse all cards from a card file"""
        cards = []

        # Split by card markers
        card_pattern = r'<!-- CARD:([^>]+) -->\s*<!-- META: ({[^}]+}) -->(.*?)<!-- END_CARD -->'

        for match in re.finditer(card_pattern, content, re.DOTALL):
            card_id = match.group(1)
            meta_json = match.group(2)
            card_body = match.group(3)

            # Parse card role - handle both naming patterns:
            # Product cards: product-{role}-{name} (e.g., product-meta-chair)
            # Material/other cards: {name}-{role} (e.g., camby-fabric-meta)

            # Try product pattern first
            role_match = re.search(r'product-(\w+)-', card_id)
            if role_match:
                role = role_match.group(1)
            else:
                # Try extracting role from end (for material cards)
                # Common roles: meta, definition, context, data, composition, colors, care, etc.
                role_from_end = re.search(r'-(\w+)$', card_id)
                if role_from_end:
                    potential_role = role_from_end.group(1)
                    # Validate it's a known role
                    known_roles = {'meta', 'definition', 'context', 'data', 'procedure', 'exception',
                                   'decision', 'example', 'composition', 'colors', 'care', 'restrictions',
                                   'ordering', 'warranty', 'swatch', 'info', 'overview', 'palette', 'implementation'}
                    role = potential_role if potential_role in known_roles else 'unknown'
                else:
                    role = 'unknown'

            try:
                meta = json.loads(meta_json)
            except json.JSONDecodeError:
                meta = {}

            cards.append({
                'id': card_id,
                'role': role,
                'meta': meta,
                'body': card_body,
                'original_meta_str': meta_json
            })

        return cards

    def _enhance_meta_card(
        self,
        card: Dict,
        card_type: str,
        card_filename: str,
        product_lookup: Dict,
        material_lookup: Dict,
        style_data: Tuple[Dict, Dict]
    ) -> Dict:
        """Enhance meta card with ModelBank data"""
        style_lookup, product_to_styles = style_data
        meta = card['meta'].copy()

        if card_type == 'product' and card_filename in product_lookup:
            match_data = product_lookup[card_filename]
            mb_product = match_data['mb_product']

            # Add Floorplanner/ModelBank integration
            meta['model'] = mb_product.get('model')
            meta['fp_url'] = f"https://modelbank.floorplanner.com/products/{mb_product.get('model', '').split('_')[0]}"

            if mb_product.get('parent'):
                meta['parent_model'] = mb_product['parent']

            # ModelBank status & metadata
            meta['mb_status'] = mb_product.get('status')
            meta['mb_created_at'] = mb_product.get('created_at')
            meta['mb_sku'] = str(mb_product.get('sku', ''))
            meta['mb_name'] = mb_product.get('name')

            # Visual & 3D data
            if mb_product.get('color'):
                meta['mb_color_hex'] = mb_product['color']
            if mb_product.get('palette_color'):
                meta['mb_palette_colors'] = mb_product['palette_color']
            meta['mb_has_3d_model'] = True
            meta['mb_is_glb'] = mb_product.get('is_glb', False)

            # Dimensions
            meta['mb_dimensions_cm'] = {
                'width': mb_product.get('width'),
                'depth': mb_product.get('depth'),
                'height': mb_product.get('height')
            }
            if mb_product.get('surface_height'):
                meta['mb_dimensions_cm']['surface_height'] = mb_product['surface_height']

            # Materials
            if mb_product.get('materials'):
                meta['mb_materials'] = mb_product['materials']

            # Product relationships - featured in styles
            if card_filename in product_to_styles:
                meta['featured_in_styles'] = product_to_styles[card_filename]

            # Match quality
            meta['match_confidence'] = match_data['confidence']
            meta['match_method'] = match_data['match_method']

        elif card_type == 'material' and card_filename in material_lookup:
            match_data = material_lookup[card_filename]

            # ModelBank material integration
            meta['mb_material_id'] = match_data['mb_id']
            meta['mb_material_sku'] = match_data['mb_sku']
            meta['mb_material_name'] = match_data['mb_name']
            meta['mb_material_kind'] = match_data['mb_kind']

            # Match quality
            meta['match_type'] = match_data['match_type']
            meta['match_confidence'] = 'high' if match_data['match_type'] == 'exact_item' else 'medium'

        elif card_type == 'style':
            # Get style filename (convert from cards filename to source filename)
            style_source_file = card_filename.replace('_cards_v6.md', '.json')

            if style_source_file in style_lookup:
                style_data = style_lookup[style_source_file]

                meta['style_url'] = style_data['style_info']['url']
                meta['style_title'] = style_data['style_info']['title']

                # Products shown in this style
                products_shown = []
                for product in style_data['products']:
                    prod_info = {
                        'product_id': product['product_id'],
                        'match_method': product['match_method']
                    }
                    if product.get('model_id'):
                        prod_info['model_id'] = product['model_id']
                        prod_info['fp_url'] = f"https://modelbank.floorplanner.com/products/{product['model_id'].split('_')[0]}"
                    if product.get('mb_name'):
                        prod_info['name'] = product['mb_name']

                    products_shown.append(prod_info)

                if products_shown:
                    meta['products_shown'] = products_shown
                    meta['total_products'] = style_data['total_products']
                    meta['matched_products'] = len([p for p in products_shown if p.get('model_id')])
                    meta['unmatched_products'] = style_data['total_products'] - meta['matched_products']

        return meta

    def _rebuild_card_content(self, cards: List[Dict]) -> str:
        """Rebuild card file content from parsed cards"""
        content_parts = []

        for card in cards:
            # Format META as pretty JSON
            meta_json = json.dumps(card['meta'], indent=2, ensure_ascii=False)

            card_text = f"<!-- CARD:{card['id']} -->\n"
            card_text += f"<!-- META: {meta_json} -->\n"
            card_text += card['body']
            card_text += "<!-- END_CARD -->\n"

            content_parts.append(card_text)

        return '\n\n'.join(content_parts)

    def enhance_cards_directory(
        self,
        source_dir: str,
        output_dir: str,
        product_matches_path: str,
        material_matches_path: str,
        style_products_path: str
    ) -> Dict:
        """
        Enhance all cards in a directory

        Args:
            source_dir: Source cards directory
            output_dir: Output enhanced cards directory
            product_matches_path: Path to product matches JSON
            material_matches_path: Path to material matches JSON
            style_products_path: Path to style products JSON

        Returns:
            Dict with enhancement statistics
        """
        # Load matching data
        print("Loading matching data...")
        product_lookup, material_lookup, style_data = self.load_matching_data(
            product_matches_path,
            material_matches_path,
            style_products_path
        )

        # Create output directory structure
        source_path = Path(source_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        stats = {
            'total_cards': 0,
            'enhanced_cards': 0,
            'unchanged_cards': 0,
            'by_type': defaultdict(lambda: {'total': 0, 'enhanced': 0})
        }

        # Card types that can be enhanced with ModelBank data
        enhanceable_types = ['product', 'material', 'style', 'collection', 'content']

        # Process all subdirectories in source
        for subdir in sorted(source_path.iterdir()):
            if not subdir.is_dir():
                continue

            card_type_dir = subdir.name
            type_source = subdir
            type_output = output_path / card_type_dir
            type_output.mkdir(exist_ok=True)

            # Determine if this card type can be enhanced
            can_enhance = card_type_dir in enhanceable_types

            if can_enhance:
                print(f"\nProcessing {card_type_dir} cards...")
            else:
                print(f"\nCopying {card_type_dir} cards (no enhancement)...")

            for card_file in type_source.glob('*.md'):
                stats['total_cards'] += 1
                stats['by_type'][card_type_dir]['total'] += 1

                # Read card
                with open(card_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if can_enhance:
                    # Try to enhance card
                    enhanced_content, was_modified = self.enhance_card(
                        content,
                        card_type_dir,
                        card_file.name,
                        product_lookup,
                        material_lookup,
                        style_data
                    )
                else:
                    # Just copy as-is
                    enhanced_content = content
                    was_modified = False

                # Write to output
                output_file = type_output / card_file.name
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(enhanced_content)

                if was_modified:
                    stats['enhanced_cards'] += 1
                    stats['by_type'][card_type_dir]['enhanced'] += 1
                else:
                    stats['unchanged_cards'] += 1

            print(f"  {stats['by_type'][card_type_dir]['enhanced']}/{stats['by_type'][card_type_dir]['total']} enhanced")

        return dict(stats)

    def generate_report(self, stats: Dict, output_path: str):
        """Generate enhancement report"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Card Enhancement Report for {self.retailer_name}\n")
            f.write("=" * 80 + "\n\n")

            f.write("SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total cards processed: {stats['total_cards']}\n")
            f.write(f"Enhanced with ModelBank data: {stats['enhanced_cards']} ({stats['enhanced_cards']/stats['total_cards']*100:.1f}%)\n")
            f.write(f"Unchanged (copied as-is): {stats['unchanged_cards']} ({stats['unchanged_cards']/stats['total_cards']*100:.1f}%)\n\n")

            f.write("BY CARD TYPE\n")
            f.write("-" * 80 + "\n")
            for card_type, type_stats in sorted(stats['by_type'].items()):
                f.write(f"\n{card_type.upper()}:\n")
                f.write(f"  Total: {type_stats['total']}\n")
                f.write(f"  Enhanced: {type_stats['enhanced']} ({type_stats['enhanced']/type_stats['total']*100:.1f}%)\n")
                f.write(f"  Unchanged: {type_stats['total'] - type_stats['enhanced']}\n")

        print(f"\nEnhancement report saved to: {output_path}")
