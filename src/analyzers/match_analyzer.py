#!/usr/bin/env python3
"""
Match Analyzer - Analyzes product matching results and generates statistics
"""

from typing import Dict, List, Tuple
from collections import defaultdict


class MatchAnalyzer:
    """Analyzes product matching results"""

    def __init__(self):
        """Initialize match analyzer"""
        pass

    def analyze_matches(self, matches: Dict) -> Dict:
        """
        Analyze match results and generate comprehensive statistics

        Args:
            matches: Dict with 'matches' list from matching output

        Returns:
            Dict with analysis results
        """
        total = len(matches.get('matches', []))
        matched = sum(1 for m in matches['matches'] if m.get('matched'))
        unmatched = total - matched

        # Confidence breakdown
        confidence_counts = defaultdict(int)
        for match in matches['matches']:
            if match.get('matched'):
                confidence = match.get('confidence', 'unknown')
                confidence_counts[confidence] += 1

        # Match method breakdown
        method_counts = defaultdict(int)
        for match in matches['matches']:
            if match.get('matched'):
                method = match.get('match_method', 'unknown')
                method_counts[method] += 1

        # Multiple matches analysis
        multi_match_counts = defaultdict(int)
        for match in matches['matches']:
            if match.get('matched'):
                match_count = len(match.get('matches', []))
                multi_match_counts[match_count] += 1

        # Style coverage
        with_styles = sum(1 for m in matches['matches']
                         if m.get('matched') and m.get('styles'))
        without_styles = matched - with_styles

        return {
            'summary': {
                'total_products': total,
                'matched': matched,
                'unmatched': unmatched,
                'match_rate': round(matched / total * 100, 1) if total > 0 else 0
            },
            'confidence': dict(confidence_counts),
            'methods': dict(method_counts),
            'multiple_matches': dict(multi_match_counts),
            'styles': {
                'with_styles': with_styles,
                'without_styles': without_styles,
                'style_coverage': round(with_styles / matched * 100, 1) if matched > 0 else 0
            }
        }

    def find_problematic_matches(self, matches: Dict) -> Dict[str, List[Dict]]:
        """
        Find potentially problematic matches that need review

        Args:
            matches: Dict with 'matches' list

        Returns:
            Dict with categorized problematic matches
        """
        problematic = {
            'low_confidence': [],
            'many_matches': [],
            'no_sku': [],
            'no_url': []
        }

        for match in matches.get('matches', []):
            if not match.get('matched'):
                continue

            cardset = match['cardset']
            confidence = match.get('confidence')
            match_count = len(match.get('matches', []))

            # Low confidence
            if confidence == 'low':
                problematic['low_confidence'].append({
                    'file': cardset.get('file_name'),
                    'sku': cardset.get('card_sku'),
                    'name': cardset.get('card_name'),
                    'match_count': match_count,
                    'method': match.get('match_method')
                })

            # Many matches (4+)
            if match_count >= 4:
                problematic['many_matches'].append({
                    'file': cardset.get('file_name'),
                    'sku': cardset.get('card_sku'),
                    'name': cardset.get('card_name'),
                    'match_count': match_count,
                    'confidence': confidence
                })

            # Missing SKU
            if not cardset.get('card_sku'):
                problematic['no_sku'].append({
                    'file': cardset.get('file_name'),
                    'name': cardset.get('card_name'),
                    'url': cardset.get('card_url')
                })

            # Missing URL
            if not cardset.get('card_url'):
                problematic['no_url'].append({
                    'file': cardset.get('file_name'),
                    'sku': cardset.get('card_sku'),
                    'name': cardset.get('card_name')
                })

        return problematic

    def compare_match_runs(self, old_matches: Dict, new_matches: Dict) -> Dict:
        """
        Compare two match runs to see improvements/regressions

        Args:
            old_matches: Previous match results
            new_matches: New match results

        Returns:
            Dict with comparison results
        """
        old_analysis = self.analyze_matches(old_matches)
        new_analysis = self.analyze_matches(new_matches)

        # Calculate deltas
        old_matched = old_analysis['summary']['matched']
        new_matched = new_analysis['summary']['matched']
        delta_matched = new_matched - old_matched

        old_rate = old_analysis['summary']['match_rate']
        new_rate = new_analysis['summary']['match_rate']
        delta_rate = new_rate - old_rate

        # Confidence changes
        confidence_deltas = {}
        for conf in ['high', 'medium', 'low']:
            old_count = old_analysis['confidence'].get(conf, 0)
            new_count = new_analysis['confidence'].get(conf, 0)
            confidence_deltas[conf] = new_count - old_count

        return {
            'summary': {
                'old_matched': old_matched,
                'new_matched': new_matched,
                'delta_matched': delta_matched,
                'old_rate': old_rate,
                'new_rate': new_rate,
                'delta_rate': round(delta_rate, 1)
            },
            'confidence_changes': confidence_deltas,
            'old_analysis': old_analysis,
            'new_analysis': new_analysis
        }

    def get_unmatched_products(self, matches: Dict) -> List[Dict]:
        """
        Get list of unmatched products for further investigation

        Args:
            matches: Dict with 'matches' list

        Returns:
            List of unmatched product dicts
        """
        unmatched = []

        for match in matches.get('matches', []):
            if not match.get('matched'):
                cardset = match['cardset']
                unmatched.append({
                    'file': cardset.get('file_name'),
                    'sku': cardset.get('card_sku'),
                    'name': cardset.get('card_name'),
                    'url': cardset.get('card_url')
                })

        return unmatched

    def get_match_quality_score(self, matches: Dict) -> Dict:
        """
        Calculate overall match quality score

        Args:
            matches: Dict with 'matches' list

        Returns:
            Dict with quality metrics
        """
        analysis = self.analyze_matches(matches)

        total_matched = analysis['summary']['matched']
        if total_matched == 0:
            return {
                'overall_score': 0,
                'match_rate_score': 0,
                'confidence_score': 0,
                'style_score': 0
            }

        # Match rate score (0-40 points)
        match_rate = analysis['summary']['match_rate']
        match_rate_score = min(40, match_rate * 0.4)

        # Confidence score (0-40 points)
        high_count = analysis['confidence'].get('high', 0)
        medium_count = analysis['confidence'].get('medium', 0)
        low_count = analysis['confidence'].get('low', 0)

        confidence_score = (
            (high_count * 1.0 + medium_count * 0.5 + low_count * 0.2)
            / total_matched * 40
        )

        # Style coverage score (0-20 points)
        style_coverage = analysis['styles']['style_coverage']
        style_score = min(20, style_coverage * 0.2)

        overall_score = match_rate_score + confidence_score + style_score

        return {
            'overall_score': round(overall_score, 1),
            'match_rate_score': round(match_rate_score, 1),
            'confidence_score': round(confidence_score, 1),
            'style_score': round(style_score, 1)
        }
