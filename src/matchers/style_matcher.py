#!/usr/bin/env python3
"""
Style Matcher - Maps style images to products by extracting SKUs from filenames
"""

import os
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional


class StyleMatcher:
    """Matches style images to products by extracting SKUs from image filenames"""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize style matcher with configuration

        Args:
            config: Optional dict with:
                - sku_patterns: List[str] - Custom regex patterns for SKU extraction
                - style_folder_pattern: str - Regex to extract style name from folder
        """
        self.config = config or {}
        self.sku_patterns = self.config.get('sku_patterns', self._default_sku_patterns())

    def _default_sku_patterns(self) -> List[Tuple[str, str]]:
        """
        Default SKU extraction patterns

        Returns:
            List of (pattern_name, regex) tuples
        """
        return [
            # Pattern 1: Standard SKU format (e.g., 1342-3, 2571-K173CB, 6442-2)
            ('standard', r'\b(\d{3,4}-[A-Z0-9]+)\b'),

            # Pattern 2: Custom SKU format (e.g., C000-72SFA1, C300-L4161SF)
            ('custom', r'\b([A-Z]\d{3}-[A-Z0-9]+)\b'),

            # Pattern 3: SKU with underscores (e.g., 1215-05__6S24-0610)
            ('underscore', r'(\d{3,4}-\d+)__'),

            # Pattern 4: Simple numeric SKU (e.g., 0270, 0237)
            ('numeric', r'\b(0\d{3})\b'),
        ]

    def extract_skus_from_filename(self, filename: str) -> List[str]:
        """
        Extract potential SKUs from an image filename

        Args:
            filename: Image filename (e.g., "ORIGINAL_1342-3-6442-2.jpg")

        Returns:
            List of extracted SKUs
        """
        # Remove common prefixes and extensions
        name = filename.replace('ORIGINAL_', '').replace('.jpg', '').replace('.png', '')

        skus = []

        # Apply all patterns
        for pattern_name, pattern in self.sku_patterns:
            matches = re.findall(pattern, name, re.IGNORECASE)
            skus.extend(matches)

        # Normalize and deduplicate SKUs
        normalized = []
        for sku in skus:
            sku_clean = sku.upper().strip()
            if sku_clean and sku_clean not in normalized:
                normalized.append(sku_clean)

        return normalized

    def normalize_sku_for_matching(self, sku: str) -> Set[str]:
        """
        Generate SKU variants for matching against product cards

        Args:
            sku: SKU string

        Returns:
            Set of SKU variants
        """
        variants = set()
        sku_upper = sku.upper()
        variants.add(sku_upper)

        # Remove dashes
        variants.add(sku_upper.replace('-', ''))

        # Extract base (before first dash)
        if '-' in sku_upper:
            base = sku_upper.split('-')[0]
            variants.add(base)

        return variants

    def get_style_folders(self, roomprompt_dir: str) -> Dict[str, Dict]:
        """
        Get mapping of style name → folder info with ORIGINAL image

        Args:
            roomprompt_dir: Path to directory containing style folders

        Returns:
            Dict of {style_name: {folder_path, original_file, full_folder_name}}
        """
        style_folders = {}

        if not os.path.exists(roomprompt_dir):
            return style_folders

        for folder in os.listdir(roomprompt_dir):
            folder_path = os.path.join(roomprompt_dir, folder)
            if not os.path.isdir(folder_path):
                continue

            # Look for ORIGINAL image
            original_files = [f for f in os.listdir(folder_path)
                            if f.startswith('ORIGINAL_') and
                            (f.endswith('.jpg') or f.endswith('.png'))]

            if not original_files:
                continue

            original_file = original_files[0]

            # Extract style name from folder name
            # Default: Extract before first dash separator
            style_name = self._extract_style_name(folder)

            if not style_name:
                continue

            style_folders[style_name] = {
                'folder_path': folder_path,
                'original_file': original_file,
                'full_folder_name': folder
            }

        return style_folders

    def _extract_style_name(self, folder_name: str) -> Optional[str]:
        """
        Extract style name from folder name

        Args:
            folder_name: Full folder name

        Returns:
            Style name or None
        """
        # Check for custom pattern in config
        custom_pattern = self.config.get('style_folder_pattern')
        if custom_pattern:
            match = re.match(custom_pattern, folder_name)
            if match:
                return match.group(1)

        # Default: Extract before " - " separator
        if ' - ' in folder_name:
            return folder_name.split(' - ')[0]

        # Skip analysis/temp folders
        if any(skip in folder_name.lower() for skip in ['analysis', 'temp', 'test']):
            return None

        # Otherwise use full folder name
        return folder_name

    def load_product_cards(self, cards_dir: str, card_suffix: str = '_cards_v6.md') -> Dict[str, Dict]:
        """
        Load all product cards and extract SKUs

        Args:
            cards_dir: Path to cards directory (should contain 'product' subdirectory)
            card_suffix: Card file suffix to match (e.g., '_cards_v6.md')

        Returns:
            Dict of {filename: {filename, sku, name, url, filepath}}
        """
        products = {}
        product_dir = os.path.join(cards_dir, 'product')

        if not os.path.exists(product_dir):
            print(f"Warning: Product directory not found: {product_dir}")
            return products

        print(f"Loading product cards from {product_dir}...")

        for filename in os.listdir(product_dir):
            if not filename.endswith(card_suffix):
                continue

            filepath = os.path.join(product_dir, filename)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract SKU from content
                sku_match = re.search(r'SKU:\s*([A-Z0-9-_]+)', content, re.IGNORECASE)
                if not sku_match:
                    continue

                card_sku = sku_match.group(1).strip()

                # Extract product name (various patterns)
                name_match = re.search(r'<!--\s*CARD:[^>]+-->[^#]*##?\s*\*\*([^*]+)\*\*', content)
                if not name_match:
                    name_match = re.search(r'<!--\s*CARD:[^>]+-->[^#]*#\s+([^\n]+)', content)

                product_name = name_match.group(1).strip() if name_match else filename

                # Extract URL (generic pattern)
                url_match = re.search(r'https?://[^\s\)]+', content)
                url = url_match.group(0) if url_match else None

                products[filename] = {
                    'filename': filename,
                    'sku': card_sku,
                    'name': product_name,
                    'url': url,
                    'filepath': filepath
                }

            except Exception as e:
                print(f"Error reading {filename}: {e}")
                continue

        print(f"Loaded {len(products)} product cards")
        return products

    def match_skus_to_products(
        self,
        image_skus: List[str],
        products: Dict[str, Dict]
    ) -> List[Dict]:
        """
        Match SKUs extracted from image to product cards

        Args:
            image_skus: List of SKUs extracted from image filename
            products: Dict of product data from load_product_cards()

        Returns:
            List of matched product dicts
        """
        matched = []

        # Build reverse index: SKU variant → product
        sku_index = defaultdict(list)
        for product_file, product_data in products.items():
            product_sku = product_data['sku']
            variants = self.normalize_sku_for_matching(product_sku)
            for variant in variants:
                sku_index[variant].append(product_data)

        # Match each image SKU
        for image_sku in image_skus:
            variants = self.normalize_sku_for_matching(image_sku)
            for variant in variants:
                if variant in sku_index:
                    for product in sku_index[variant]:
                        if product not in matched:
                            matched.append(product)
                    break  # Stop after first variant match

        return matched

    def build_style_product_mapping(
        self,
        style_folders: Dict[str, Dict],
        products: Dict[str, Dict],
        modelbank_styles: Optional[Dict[str, int]] = None
    ) -> List[Dict]:
        """
        Build complete style → product mapping

        Args:
            style_folders: Output from get_style_folders()
            products: Output from load_product_cards()
            modelbank_styles: Optional dict of {style_name: style_id} from Modelbank

        Returns:
            List of style mappings with matched products
        """
        modelbank_styles = modelbank_styles or {}
        style_mappings = []

        for style_name, folder_info in sorted(style_folders.items()):
            original_file = folder_info['original_file']

            # Extract SKUs from filename
            image_skus = self.extract_skus_from_filename(original_file)

            # Match to products
            matched_products = self.match_skus_to_products(image_skus, products)

            # Get Modelbank style ID
            modelbank_style_id = modelbank_styles.get(style_name)

            style_mapping = {
                'style_name': style_name,
                'modelbank_style_id': modelbank_style_id,
                'original_image': original_file,
                'folder_path': folder_info['folder_path'],
                'full_folder_name': folder_info['full_folder_name'],
                'extracted_skus': image_skus,
                'matched_products_count': len(matched_products),
                'products': []
            }

            for product in matched_products:
                style_mapping['products'].append({
                    'filename': product['filename'],
                    'sku': product['sku'],
                    'name': product['name'],
                    'url': product['url']
                })

            style_mappings.append(style_mapping)

        return style_mappings

    def build_product_to_style_index(self, style_mappings: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Build reverse index: product filename → list of styles

        Args:
            style_mappings: Output from build_style_product_mapping()

        Returns:
            Dict of {product_filename: [{style_name, style_id}]}
        """
        product_index = defaultdict(list)

        for style in style_mappings:
            style_info = {
                'style_name': style['style_name'],
                'style_id': style['modelbank_style_id']
            }

            for product in style['products']:
                product_filename = product['filename']
                if style_info not in product_index[product_filename]:
                    product_index[product_filename].append(style_info)

        return dict(product_index)
