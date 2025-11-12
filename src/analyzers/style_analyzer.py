#!/usr/bin/env python3
"""
Style Analyzer - Analyzes style coverage and style-product relationships
"""

from typing import Dict, List
from collections import defaultdict


class StyleAnalyzer:
    """Analyzes style coverage and style-product mappings"""

    def __init__(self):
        """Initialize style analyzer"""
        pass

    def analyze_style_coverage(self, style_mappings: List[Dict]) -> Dict:
        """
        Analyze style coverage from style-product mappings

        Args:
            style_mappings: List of style mapping dicts from StyleMatcher

        Returns:
            Dict with style coverage analysis
        """
        total_styles = len(style_mappings)
        styles_with_matches = sum(1 for s in style_mappings
                                 if s.get('matched_products_count', 0) > 0)
        styles_with_mb_id = sum(1 for s in style_mappings
                               if s.get('modelbank_style_id'))

        total_products = sum(s.get('matched_products_count', 0)
                           for s in style_mappings)

        avg_products = total_products / total_styles if total_styles > 0 else 0

        # Product distribution
        products_per_style = [s.get('matched_products_count', 0)
                             for s in style_mappings]
        products_per_style.sort(reverse=True)

        return {
            'summary': {
                'total_styles': total_styles,
                'styles_with_matches': styles_with_matches,
                'styles_without_matches': total_styles - styles_with_matches,
                'styles_with_modelbank_id': styles_with_mb_id,
                'total_product_matches': total_products,
                'avg_products_per_style': round(avg_products, 1),
                'match_rate': round(styles_with_matches / total_styles * 100, 1) if total_styles > 0 else 0
            },
            'distribution': {
                'max_products_in_style': max(products_per_style) if products_per_style else 0,
                'min_products_in_style': min(p for p in products_per_style if p > 0) if any(p > 0 for p in products_per_style) else 0,
                'median_products': products_per_style[len(products_per_style) // 2] if products_per_style else 0
            }
        }

    def get_top_styles(
        self,
        style_mappings: List[Dict],
        top_n: int = 10
    ) -> List[Dict]:
        """
        Get top N styles by number of matched products

        Args:
            style_mappings: List of style mapping dicts
            top_n: Number of top styles to return

        Returns:
            List of top style dicts
        """
        # Sort by product count
        sorted_styles = sorted(
            style_mappings,
            key=lambda s: s.get('matched_products_count', 0),
            reverse=True
        )

        top_styles = []
        for style in sorted_styles[:top_n]:
            top_styles.append({
                'style_name': style.get('style_name'),
                'modelbank_style_id': style.get('modelbank_style_id'),
                'product_count': style.get('matched_products_count', 0),
                'extracted_skus': style.get('extracted_skus', [])
            })

        return top_styles

    def get_styles_without_matches(self, style_mappings: List[Dict]) -> List[Dict]:
        """
        Get styles that have no product matches

        Args:
            style_mappings: List of style mapping dicts

        Returns:
            List of styles without matches
        """
        no_matches = []

        for style in style_mappings:
            if style.get('matched_products_count', 0) == 0:
                no_matches.append({
                    'style_name': style.get('style_name'),
                    'modelbank_style_id': style.get('modelbank_style_id'),
                    'extracted_skus': style.get('extracted_skus', []),
                    'original_image': style.get('original_image')
                })

        return no_matches

    def analyze_product_style_overlap(self, matches: Dict) -> Dict:
        """
        Analyze which products appear in multiple styles

        Args:
            matches: Match results with style information

        Returns:
            Dict with overlap analysis
        """
        # Build product → styles mapping
        product_styles = defaultdict(list)

        for match in matches.get('matches', []):
            if not match.get('matched'):
                continue

            cardset = match['cardset']
            sku = cardset.get('card_sku')
            name = cardset.get('card_name')
            styles = match.get('styles', [])

            if styles:
                for style in styles:
                    product_styles[sku].append({
                        'sku': sku,
                        'name': name,
                        'style_id': style.get('style_id'),
                        'style_name': style.get('style_name')
                    })

        # Find products in multiple styles
        multi_style_products = {
            sku: styles
            for sku, styles in product_styles.items()
            if len(styles) > 1
        }

        # Calculate statistics
        total_products_with_styles = len(product_styles)
        products_in_multiple = len(multi_style_products)

        return {
            'summary': {
                'total_products_with_styles': total_products_with_styles,
                'products_in_single_style': total_products_with_styles - products_in_multiple,
                'products_in_multiple_styles': products_in_multiple
            },
            'multi_style_products': [
                {
                    'sku': sku,
                    'style_count': len(styles),
                    'styles': [s['style_name'] for s in styles]
                }
                for sku, styles in sorted(
                    multi_style_products.items(),
                    key=lambda x: len(x[1]),
                    reverse=True
                )
            ][:20]  # Top 20
        }

    def find_missing_products_in_styles(
        self,
        style_mappings: List[Dict],
        all_products: Dict[str, Dict]
    ) -> Dict:
        """
        Find products that were extracted from style images but not found in cards

        Args:
            style_mappings: List of style mapping dicts
            all_products: Dict of all product cards

        Returns:
            Dict with missing product analysis
        """
        missing_by_style = []

        for style in style_mappings:
            extracted_skus = style.get('extracted_skus', [])
            matched_products = style.get('products', [])
            matched_skus = {p.get('sku') for p in matched_products}

            # Find SKUs that were extracted but not matched
            missing_skus = [sku for sku in extracted_skus if sku not in matched_skus]

            if missing_skus:
                missing_by_style.append({
                    'style_name': style.get('style_name'),
                    'extracted_skus': extracted_skus,
                    'matched_skus': list(matched_skus),
                    'missing_skus': missing_skus
                })

        total_missing = sum(len(s['missing_skus']) for s in missing_by_style)

        return {
            'summary': {
                'styles_with_missing_products': len(missing_by_style),
                'total_missing_sku_references': total_missing
            },
            'missing_by_style': missing_by_style
        }

    def calculate_style_completeness(self, style_mappings: List[Dict]) -> List[Dict]:
        """
        Calculate completeness score for each style

        Args:
            style_mappings: List of style mapping dicts

        Returns:
            List of styles with completeness scores
        """
        completeness = []

        for style in style_mappings:
            extracted_count = len(style.get('extracted_skus', []))
            matched_count = style.get('matched_products_count', 0)

            if extracted_count == 0:
                score = 0
            else:
                score = matched_count / extracted_count * 100

            completeness.append({
                'style_name': style.get('style_name'),
                'extracted_skus': extracted_count,
                'matched_products': matched_count,
                'completeness_score': round(score, 1),
                'has_modelbank_id': style.get('modelbank_style_id') is not None
            })

        # Sort by completeness score
        completeness.sort(key=lambda s: s['completeness_score'], reverse=True)

        return completeness
