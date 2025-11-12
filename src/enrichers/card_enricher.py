#!/usr/bin/env python3
"""
Card Enricher - Enriches product cards with Modelbank and style data
"""

import re
import json
from typing import Dict, List, Optional


class CardEnricher:
    """Enriches product cards with Modelbank metadata and style information"""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize card enricher with configuration

        Args:
            config: Optional dict with:
                - max_related_products: int - Max related products to include (default 5)
                - enrich_all_confidence: bool - Enrich all matches or only high-confidence (default False)
        """
        self.config = config or {}
        self.max_related = self.config.get('max_related_products', 5)
        self.enrich_all = self.config.get('enrich_all_confidence', False)

    def extract_model_base(self, model: str) -> str:
        """
        Extract base model ID for URL (remove _XX suffix)

        Args:
            model: Full model ID (e.g., "xxxx50618d1ed4f46b2fd19c67ec06b3bd00f31b_28")

        Returns:
            Base model ID (e.g., "xxxx50618d1ed4f46b2fd19c67ec06b3bd00f31b")
        """
        if not model:
            return ""
        # Remove _XX suffix (e.g., _00, _01, _28)
        return re.sub(r'_\d{2}$', '', model)

    def generate_modelbank_image_urls(
        self,
        model: str,
        views: Optional[List[str]] = None,
        size: int = 540
    ) -> Dict[str, str]:
        """
        Generate Modelbank CloudFront image URLs for a product

        Args:
            model: Full model ID (e.g., "xxxx50618d1ed4f46b2fd19c67ec06b3bd00f31b_28")
            views: List of view types (default: ['iso', 'front', 'left', 'top'])
            size: Image width in pixels (default: 540)

        Returns:
            Dict of {view_name: image_url}
        """
        if not model:
            return {}

        # Extract base model (remove variant suffix)
        model_base = self.extract_model_base(model)

        # Extract variant number (e.g., "28" from "xxxx...31b_28")
        variant_match = re.search(r'_(\d{2})$', model)
        variant = variant_match.group(1) if variant_match else "00"

        # Default views if not specified
        # Standard Modelbank renders: iso, front, left, top
        if views is None:
            views = ['iso', 'front', 'left', 'top']

        # CloudFront base URL
        base_url = "https://d2bi8gvwsa8xa3.cloudfront.net/cdb/renders"

        # Generate URLs for each view
        image_urls = {}

        for view in views:
            # Get first two characters for directory structure
            prefix = model_base[:2]

            # Build URL: {base}/{prefix}/{model_base}_{variant}.{view}.{size}.png
            url = f"{base_url}/{prefix}/{model_base}_{variant}.{view}.{size}.png"
            image_urls[view] = url

        return image_urls

    def build_enrichment_index(self, matches: Dict) -> Dict[str, Dict]:
        """
        Build index: filename → enrichment data

        Args:
            matches: Dict from matching output with 'matches' list

        Returns:
            Dict of {filename: enrichment_data}
        """
        enrichment = {}

        for match in matches.get('matches', []):
            if not match.get('matched'):
                continue

            # Filter by confidence if configured
            if not self.enrich_all and match.get('confidence') != 'high':
                continue

            cardset = match['cardset']
            filename = cardset.get('file_name')

            if not filename:
                continue

            # Get first matched Modelbank product
            matched_products = match.get('matches', [])
            if not matched_products:
                continue

            product = matched_products[0]

            # Get style information
            styles = match.get('styles', [])

            # Build related products list (from same styles)
            related_skus = self._find_related_products(match, matches, styles)

            # Generate image URLs
            model_id = product.get('model')
            image_urls = self.generate_modelbank_image_urls(model_id) if model_id else {}

            enrichment[filename] = {
                'model': product.get('model'),
                'sku': cardset.get('card_sku'),
                'parent': product.get('parent'),
                'is_private': product.get('is_private', False),
                'fp_url': f"https://modelbank.floorplanner.com/products/{self.extract_model_base(product.get('model', ''))}",
                'modelbank_images': image_urls,
                'styles': styles,
                'related_products': sorted(list(related_skus))[:self.max_related]
            }

        return enrichment

    def _find_related_products(
        self,
        current_match: Dict,
        all_matches: Dict,
        styles: List[Dict]
    ) -> set:
        """
        Find related products that share the same styles

        Args:
            current_match: Current match dict
            all_matches: All matches dict
            styles: List of style dicts for current match

        Returns:
            Set of related product SKUs
        """
        related_skus = set()
        current_sku = current_match['cardset'].get('card_sku')

        for style_info in styles:
            # Get other products from same style
            for other_match in all_matches.get('matches', []):
                if not other_match.get('matched'):
                    continue

                other_styles = other_match.get('styles', [])

                # Check if shares same style
                for other_style in other_styles:
                    if other_style.get('style_id') == style_info.get('style_id'):
                        other_sku = other_match['cardset'].get('card_sku')
                        if other_sku and other_sku != current_sku:
                            related_skus.add(other_sku)

        return related_skus

    def parse_card_file(self, filepath: str) -> List[Dict]:
        """
        Parse card file into individual cards

        Args:
            filepath: Path to card file

        Returns:
            List of card dicts with {type, card_id, meta, content}
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split by card markers
        pattern = r'<!--\s*CARD:([^\s]+)\s*-->'
        parts = re.split(pattern, content)

        cards = []

        # First part is header
        if parts[0].strip():
            cards.append({
                'type': 'header',
                'content': parts[0]
            })

        # Process card pairs (card_id, content)
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                card_id = parts[i]
                card_content = parts[i + 1]

                # Extract META block
                meta_match = re.search(
                    r'<!--\s*META:\s*(\{[^}]+\})\s*-->',
                    card_content,
                    re.DOTALL
                )
                meta = {}
                if meta_match:
                    try:
                        meta = json.loads(meta_match.group(1))
                    except json.JSONDecodeError:
                        pass

                cards.append({
                    'type': 'card',
                    'card_id': card_id,
                    'meta': meta,
                    'content': card_content
                })

        return cards

    def enrich_card_meta(
        self,
        card: Dict,
        enrichment: Dict,
        card_sku: Optional[str] = None
    ) -> Dict:
        """
        Enrich a single card's META block

        Args:
            card: Card dict from parse_card_file()
            enrichment: Enrichment data for this cardset
            card_sku: Optional SKU to include

        Returns:
            Updated META dict
        """
        meta = card.get('meta', {}).copy()
        card_role = meta.get('card_role', '')

        # All cards get model and sku
        if enrichment.get('model'):
            meta['model'] = enrichment['model']

        if card_sku or enrichment.get('sku'):
            meta['sku'] = card_sku or enrichment.get('sku')

        # Meta card gets full enrichment
        if card_role == 'meta':
            if enrichment.get('parent'):
                meta['parent'] = enrichment['parent']

            if enrichment.get('is_private') is not None:
                meta['is_private'] = enrichment['is_private']

            if enrichment.get('fp_url'):
                meta['fp_url'] = enrichment['fp_url']

            if enrichment.get('modelbank_images'):
                meta['modelbank_images'] = enrichment['modelbank_images']

            if enrichment.get('styles'):
                meta['style'] = enrichment['styles']

            if enrichment.get('related_products'):
                meta['related_products'] = enrichment['related_products']

        return meta

    def rebuild_card_content(self, card: Dict, new_meta: Optional[Dict] = None) -> str:
        """
        Rebuild card content with updated META

        Args:
            card: Card dict from parse_card_file()
            new_meta: Optional new META dict to replace existing

        Returns:
            Rebuilt card content string
        """
        if card['type'] == 'header':
            return card['content']

        content = card['content']
        card_id = card['card_id']

        if new_meta is None:
            return f"<!-- CARD:{card_id} -->{content}"

        # Remove old META block
        content_without_meta = re.sub(
            r'<!--\s*META:\s*\{[^}]+\}\s*-->\s*',
            '',
            content,
            flags=re.DOTALL
        )

        # Build new META block
        meta_json = json.dumps(new_meta, indent=2)
        meta_block = f"<!-- META: {meta_json} -->"

        # Reconstruct: CARD marker + META + content
        return f"<!-- CARD:{card_id} -->\n{meta_block}{content_without_meta}"

    def enrich_card_file(
        self,
        input_file: str,
        output_file: str,
        enrichment: Dict
    ):
        """
        Enrich a single card file with Modelbank data

        Args:
            input_file: Path to input card file
            output_file: Path to output enriched card file
            enrichment: Enrichment data for this file
        """
        # Parse cards
        cards = self.parse_card_file(input_file)

        # Get card SKU (from first card or meta card)
        card_sku = None
        for card in cards:
            if card['type'] == 'card':
                sku = card.get('meta', {}).get('sku')
                if sku:
                    card_sku = sku
                    break

        # Enrich each card
        enriched_content = []
        for card in cards:
            if card['type'] == 'header':
                enriched_content.append(card['content'])
            else:
                new_meta = self.enrich_card_meta(card, enrichment, card_sku)
                enriched_card = self.rebuild_card_content(card, new_meta)
                enriched_content.append(enriched_card)

        # Write output
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(enriched_content))

    def enrich_card_directory(
        self,
        input_dir: str,
        output_dir: str,
        enrichment_index: Dict[str, Dict],
        input_suffix: str = '_cards_v6.md',
        output_suffix: str = '_cards_v7.md'
    ) -> Dict[str, int]:
        """
        Enrich all card files in a directory

        Args:
            input_dir: Input directory path
            output_dir: Output directory path
            enrichment_index: Dict of {filename: enrichment_data}
            input_suffix: Input file suffix to match
            output_suffix: Output file suffix

        Returns:
            Dict with 'enriched' and 'copied' counts
        """
        import os

        os.makedirs(output_dir, exist_ok=True)

        enriched_count = 0
        copied_count = 0

        for filename in sorted(os.listdir(input_dir)):
            if not filename.endswith(input_suffix):
                continue

            input_file = os.path.join(input_dir, filename)
            output_filename = filename.replace(input_suffix, output_suffix)
            output_file = os.path.join(output_dir, output_filename)

            # Check if we have enrichment data
            if filename in enrichment_index:
                enrichment = enrichment_index[filename]
                self.enrich_card_file(input_file, output_file, enrichment)
                enriched_count += 1
            else:
                # Copy unchanged (no enrichment)
                with open(input_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Update suffix in content
                content = content.replace(input_suffix, output_suffix)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                copied_count += 1

        return {
            'enriched': enriched_count,
            'copied': copied_count,
            'total': enriched_count + copied_count
        }
