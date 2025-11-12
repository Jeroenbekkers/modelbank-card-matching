#!/usr/bin/env python3
"""
Product Matcher - Core matching logic for retailer cards → Modelbank products
"""

import re
from typing import Dict, List, Set, Optional
from collections import defaultdict


class ProductMatcher:
    """Matches retailer product cards to Modelbank products using multiple strategies"""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize matcher with configuration

        Args:
            config: Optional dict with matching parameters:
                - name_similarity_threshold: float (0.0-1.0), default 0.6
                - fuzzy_sku_enabled: bool, default True
                - max_fuzzy_matches_high: int, default 1
                - max_fuzzy_matches_medium: int, default 3
        """
        self.config = config or {}
        self.name_threshold = self.config.get('name_similarity_threshold', 0.6)
        self.fuzzy_sku_enabled = self.config.get('fuzzy_sku_enabled', True)
        self.max_high = self.config.get('max_fuzzy_matches_high', 1)
        self.max_medium = self.config.get('max_fuzzy_matches_medium', 3)

    def normalize_url(self, url: str) -> str:
        """Normalize URL for comparison"""
        if not url:
            return ""

        url = url.lower().strip()

        # Remove protocol
        url = re.sub(r'^https?://', '', url)

        # Remove www.
        url = re.sub(r'^www\.', '', url)

        # Remove trailing slash
        url = url.rstrip('/')

        # Remove query parameters
        url = re.sub(r'\?.*$', '', url)

        # Remove fragments
        url = re.sub(r'#.*$', '', url)

        return url

    def normalize_sku(self, sku: str) -> str:
        """Normalize SKU for exact matching"""
        if not sku:
            return ""

        sku_normalized = sku.upper().strip()

        # Remove BAS- or similar retailer prefixes
        sku_normalized = re.sub(r'^[A-Z]{2,4}-', '', sku_normalized)

        # Remove common separators
        sku_normalized = re.sub(r'[-_\s]', '', sku_normalized)

        return sku_normalized

    def normalize_sku_variants(self, sku: str) -> Set[str]:
        """
        Generate SKU variants for fuzzy matching

        Handles cases like:
        - Card SKU: "2676-WLSECTL-KIT53" (with color/config codes)
        - Product SKU: "2676-LSECT" (base SKU)
        - Match via base: "2676"

        Returns:
            Set of SKU variants to try matching
        """
        if not sku:
            return set()

        variants = set()
        sku_upper = sku.upper().strip()

        # Original
        variants.add(sku_upper)

        # Without separators
        no_sep = re.sub(r'[-_\s]', '', sku_upper)
        variants.add(no_sep)

        # Without BAS- prefix
        without_prefix = re.sub(r'^[A-Z]{2,4}-', '', sku_upper)
        if without_prefix != sku_upper:
            variants.add(without_prefix)
            variants.add(re.sub(r'[-_\s]', '', without_prefix))

        # Extract base (before first dash)
        if '-' in sku_upper:
            base = sku_upper.split('-')[0]
            variants.add(base)

        # Extract base (first two parts)
        parts = re.split(r'[-_]', sku_upper)
        if len(parts) >= 2:
            base_two = f"{parts[0]}-{parts[1]}"
            variants.add(base_two)
            variants.add(f"{parts[0]}{parts[1]}")

        # Extract numeric base (remove trailing letters)
        numeric_base = re.sub(r'[A-Z]+$', '', sku_upper.replace('-', ''))
        if numeric_base and numeric_base != sku_upper:
            variants.add(numeric_base)

        # Remove empty strings
        variants.discard('')

        return variants

    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between product names using word overlap

        Args:
            name1: First product name
            name2: Second product name

        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not name1 or not name2:
            return 0.0

        # Normalize
        name1 = name1.lower().strip()
        name2 = name2.lower().strip()

        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'with', 'of', 'for', 'to', 'from', 'by'}

        # Extract words
        words1 = set(re.findall(r'\w+', name1)) - stop_words
        words2 = set(re.findall(r'\w+', name2)) - stop_words

        if not words1 or not words2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def match_by_url(self, card_url: str, products: List[Dict]) -> List[Dict]:
        """
        Match by URL (highest confidence)

        Args:
            card_url: URL from product card
            products: List of Modelbank products

        Returns:
            List of matched products
        """
        if not card_url:
            return []

        normalized_card_url = self.normalize_url(card_url)
        matches = []

        for product in products:
            product_url = product.get('url', '')
            if product_url:
                normalized_product_url = self.normalize_url(product_url)
                if normalized_card_url == normalized_product_url:
                    matches.append(product)

        return matches

    def match_by_sku_exact(self, card_sku: str, products: List[Dict]) -> List[Dict]:
        """
        Match by exact SKU (high confidence)

        Args:
            card_sku: SKU from product card
            products: List of Modelbank products

        Returns:
            List of matched products
        """
        if not card_sku:
            return []

        normalized_card_sku = self.normalize_sku(card_sku)
        matches = []

        for product in products:
            product_sku = product.get('sku', '')
            if product_sku:
                normalized_product_sku = self.normalize_sku(product_sku)
                if normalized_card_sku == normalized_product_sku:
                    matches.append(product)

        return matches

    def match_by_sku_fuzzy(self, card_sku: str, product_sku_index: Dict[str, List[Dict]]) -> List[Dict]:
        """
        Match by SKU variants (variable confidence)

        Args:
            card_sku: SKU from product card
            product_sku_index: Pre-built index of {variant: [products]}

        Returns:
            List of matched products
        """
        if not self.fuzzy_sku_enabled or not card_sku:
            return []

        variants = self.normalize_sku_variants(card_sku)
        matched_products = set()

        for variant in variants:
            if variant in product_sku_index:
                for product in product_sku_index[variant]:
                    # Store as tuple to make it hashable
                    matched_products.add(
                        (product.get('model'), tuple(product.items()))
                    )

        # Convert back to dicts
        return [dict(items) for _, items in matched_products]

    def match_by_name(self, card_name: str, products: List[Dict]) -> List[Dict]:
        """
        Match by name similarity (variable confidence)

        Args:
            card_name: Product name from card
            products: List of Modelbank products

        Returns:
            List of (product, similarity_score) tuples above threshold
        """
        if not card_name:
            return []

        matches = []

        for product in products:
            product_name = product.get('name', '')
            if product_name:
                similarity = self.calculate_name_similarity(card_name, product_name)
                if similarity >= self.name_threshold:
                    matches.append((product, similarity))

        # Sort by similarity (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches

    def assign_confidence(self, match_method: str, match_count: int, similarity: Optional[float] = None) -> str:
        """
        Assign confidence level based on match method and count

        Args:
            match_method: 'url', 'sku', 'sku_fuzzy', or 'name'
            match_count: Number of products matched
            similarity: For name matching, the similarity score

        Returns:
            'high', 'medium', or 'low'
        """
        if match_method == 'url':
            return 'high'

        if match_method == 'sku':
            return 'high'

        if match_method == 'sku_fuzzy':
            if match_count == self.max_high:
                return 'high'
            elif match_count <= self.max_medium:
                return 'medium'
            else:
                return 'low'

        if match_method == 'name':
            if similarity and similarity > 0.8:
                return 'high'
            elif similarity and similarity > 0.6:
                return 'medium'
            else:
                return 'low'

        return 'low'

    def build_sku_variant_index(self, products: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Build index of SKU variants → products for fast fuzzy matching

        Args:
            products: List of Modelbank products

        Returns:
            Dict mapping each SKU variant to list of products
        """
        index = defaultdict(list)

        for product in products:
            sku = product.get('sku')
            if not sku:
                continue

            variants = self.normalize_sku_variants(sku)
            for variant in variants:
                index[variant].append(product)

        return dict(index)
