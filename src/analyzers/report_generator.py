#!/usr/bin/env python3
"""
Report Generator - Generates comprehensive matching and analysis reports
"""

import json
from datetime import datetime
from typing import Dict, Optional
from .match_analyzer import MatchAnalyzer
from .style_analyzer import StyleAnalyzer


class ReportGenerator:
    """Generates comprehensive reports from matching results"""

    def __init__(self):
        """Initialize report generator"""
        self.match_analyzer = MatchAnalyzer()
        self.style_analyzer = StyleAnalyzer()

    def generate_summary_report(
        self,
        matches: Dict,
        style_mappings: Optional[Dict] = None,
        retailer_name: str = "Unknown"
    ) -> str:
        """
        Generate a human-readable summary report

        Args:
            matches: Match results dict
            style_mappings: Optional style mappings dict
            retailer_name: Name of retailer

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"MODELBANK MATCHING REPORT - {retailer_name}")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Match analysis
        analysis = self.match_analyzer.analyze_matches(matches)

        lines.append("MATCH SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Total products: {analysis['summary']['total_products']}")
        lines.append(f"Matched: {analysis['summary']['matched']} ({analysis['summary']['match_rate']}%)")
        lines.append(f"Unmatched: {analysis['summary']['unmatched']}")
        lines.append("")

        # Confidence breakdown
        lines.append("CONFIDENCE BREAKDOWN")
        lines.append("-" * 80)
        for conf in ['high', 'medium', 'low']:
            count = analysis['confidence'].get(conf, 0)
            matched = analysis['summary']['matched']
            pct = round(count / matched * 100, 1) if matched > 0 else 0
            lines.append(f"{conf.capitalize()}: {count} ({pct}%)")
        lines.append("")

        # Match methods
        lines.append("MATCH METHODS")
        lines.append("-" * 80)
        for method, count in sorted(analysis['methods'].items(), key=lambda x: x[1], reverse=True):
            lines.append(f"{method}: {count}")
        lines.append("")

        # Style coverage
        if analysis['styles']['with_styles'] > 0:
            lines.append("STYLE COVERAGE")
            lines.append("-" * 80)
            lines.append(f"Products with styles: {analysis['styles']['with_styles']}")
            lines.append(f"Products without styles: {analysis['styles']['without_styles']}")
            lines.append(f"Style coverage: {analysis['styles']['style_coverage']}%")
            lines.append("")

        # Style analysis (if available)
        if style_mappings:
            style_analysis = self.style_analyzer.analyze_style_coverage(
                style_mappings.get('styles', [])
            )

            lines.append("STYLE ANALYSIS")
            lines.append("-" * 80)
            lines.append(f"Total styles: {style_analysis['summary']['total_styles']}")
            lines.append(f"Styles with matches: {style_analysis['summary']['styles_with_matches']}")
            lines.append(f"Styles with Modelbank ID: {style_analysis['summary']['styles_with_modelbank_id']}")
            lines.append(f"Total product matches: {style_analysis['summary']['total_product_matches']}")
            lines.append(f"Avg products per style: {style_analysis['summary']['avg_products_per_style']}")
            lines.append("")

            # Top styles
            top_styles = self.style_analyzer.get_top_styles(
                style_mappings.get('styles', []),
                top_n=5
            )
            if top_styles:
                lines.append("TOP 5 STYLES BY PRODUCT COUNT")
                lines.append("-" * 80)
                for i, style in enumerate(top_styles, 1):
                    lines.append(f"{i}. {style['style_name']}: {style['product_count']} products")
                lines.append("")

        # Quality score
        quality = self.match_analyzer.get_match_quality_score(matches)
        lines.append("QUALITY SCORE")
        lines.append("-" * 80)
        lines.append(f"Overall: {quality['overall_score']}/100")
        lines.append(f"  Match Rate: {quality['match_rate_score']}/40")
        lines.append(f"  Confidence: {quality['confidence_score']}/40")
        lines.append(f"  Style Coverage: {quality['style_score']}/20")
        lines.append("")

        # Problematic matches
        problematic = self.match_analyzer.find_problematic_matches(matches)
        if any(len(v) > 0 for v in problematic.values()):
            lines.append("ISSUES REQUIRING ATTENTION")
            lines.append("-" * 80)
            for issue_type, issues in problematic.items():
                if len(issues) > 0:
                    lines.append(f"{issue_type.replace('_', ' ').title()}: {len(issues)}")
            lines.append("")

        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)

        return "\n".join(lines)

    def generate_json_report(
        self,
        matches: Dict,
        style_mappings: Optional[Dict] = None,
        retailer_name: str = "Unknown"
    ) -> Dict:
        """
        Generate a structured JSON report

        Args:
            matches: Match results dict
            style_mappings: Optional style mappings dict
            retailer_name: Name of retailer

        Returns:
            Report dict
        """
        report = {
            'metadata': {
                'retailer': retailer_name,
                'generated_at': datetime.now().isoformat(),
                'version': '1.0'
            }
        }

        # Match analysis
        report['match_analysis'] = self.match_analyzer.analyze_matches(matches)

        # Quality score
        report['quality_score'] = self.match_analyzer.get_match_quality_score(matches)

        # Problematic matches
        report['problematic_matches'] = self.match_analyzer.find_problematic_matches(matches)

        # Unmatched products
        report['unmatched_products'] = self.match_analyzer.get_unmatched_products(matches)

        # Style analysis (if available)
        if style_mappings:
            styles_list = style_mappings.get('styles', [])

            report['style_analysis'] = {
                'coverage': self.style_analyzer.analyze_style_coverage(styles_list),
                'top_styles': self.style_analyzer.get_top_styles(styles_list, top_n=10),
                'styles_without_matches': self.style_analyzer.get_styles_without_matches(styles_list),
                'product_overlap': self.style_analyzer.analyze_product_style_overlap(matches),
                'completeness': self.style_analyzer.calculate_style_completeness(styles_list)
            }

        return report

    def save_report(
        self,
        matches: Dict,
        output_path: str,
        style_mappings: Optional[Dict] = None,
        retailer_name: str = "Unknown",
        format: str = "both"
    ):
        """
        Save report to file(s)

        Args:
            matches: Match results dict
            output_path: Base output path (without extension)
            style_mappings: Optional style mappings dict
            retailer_name: Name of retailer
            format: 'text', 'json', or 'both'
        """
        if format in ['text', 'both']:
            text_report = self.generate_summary_report(
                matches,
                style_mappings,
                retailer_name
            )
            with open(f"{output_path}.txt", 'w') as f:
                f.write(text_report)
            print(f"Text report saved to: {output_path}.txt")

        if format in ['json', 'both']:
            json_report = self.generate_json_report(
                matches,
                style_mappings,
                retailer_name
            )
            with open(f"{output_path}.json", 'w') as f:
                json.dump(json_report, f, indent=2)
            print(f"JSON report saved to: {output_path}.json")

    def print_quick_summary(self, matches: Dict):
        """
        Print a quick summary to console

        Args:
            matches: Match results dict
        """
        analysis = self.match_analyzer.analyze_matches(matches)

        print()
        print("=" * 80)
        print("QUICK SUMMARY")
        print("=" * 80)
        print(f"Total: {analysis['summary']['total_products']} products")
        print(f"Matched: {analysis['summary']['matched']} ({analysis['summary']['match_rate']}%)")
        print(f"  High confidence: {analysis['confidence'].get('high', 0)}")
        print(f"  Medium confidence: {analysis['confidence'].get('medium', 0)}")
        print(f"  Low confidence: {analysis['confidence'].get('low', 0)}")
        print("=" * 80)
        print()
