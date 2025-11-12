#!/usr/bin/env python3
"""
Material Matcher
Matches retailer material cards with ModelBank materials
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class MaterialMatcher:
    """Matcher for material cards"""

    def __init__(self, retailer_config: Dict):
        """
        Initialize matcher

        Args:
            retailer_config: Retailer configuration dict
        """
        self.retailer_config = retailer_config
        self.retailer_name = retailer_config['name']

    def load_material_cards(self) -> List[Dict]:
        """
        Load material cards from cards/material/ directory

        Returns:
            List of material card dicts with extracted metadata
        """
        # Build path to material cards
        cards_path = self.retailer_config.get('cards_path') or self.retailer_config.get('card_path')
        if not cards_path:
            raise ValueError("No cards_path or card_path in retailer config")

        # card_path already points to /cards/ directory, so we need cards/material/
        cards_dir = Path(cards_path).parent if Path(cards_path).name == 'product' else Path(cards_path)
        material_dir = cards_dir / 'material'

        if not material_dir.exists():
            print(f"Warning: Material directory not found: {material_dir}")
            return []

        material_cards = []
        card_files = list(material_dir.glob('*.md'))

        print(f"Found {len(card_files)} material card files")

        for card_path in card_files:
            try:
                with open(card_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract material info
                card_data = self._extract_material_info(card_path, content)
                if card_data:
                    material_cards.append(card_data)

            except Exception as e:
                print(f"Error processing {card_path}: {e}")
                continue

        return material_cards

    def _extract_material_info(self, card_path: Path, content: str) -> Optional[Dict]:
        """
        Extract material information from card

        Args:
            card_path: Path to card file
            content: Card file content

        Returns:
            Dict with material info or None
        """
        # Extract item numbers from content
        item_matches = re.findall(r'Item:\s*(\d+)', content, re.IGNORECASE)

        # Extract material name (first bold text)
        name_match = re.search(r'\*\*(.+?)\*\*', content)
        name = name_match.group(1) if name_match else "Unknown"

        # Extract potential ID from name (e.g., "Gray Locks (347)")
        name_id_match = re.search(r'\((\d+)\)', name)
        extracted_ids = []

        if name_id_match:
            extracted_ids.append(name_id_match.group(1))

        # Extract IDs from filename (e.g., "01c6d65e-982416-621-oak")
        filename_ids = re.findall(r'-(\d+)-', card_path.stem)
        # Skip generic sample ID
        filename_ids = [fid for fid in filename_ids if fid != '982416']
        extracted_ids.extend(filename_ids)

        # Extract source URL
        url_match = re.search(r'source_url:\s*(.+)', content)
        source_url = url_match.group(1).strip() if url_match else None

        return {
            'filename': card_path.name,
            'name': name,
            'item_numbers': item_matches,
            'extracted_ids': extracted_ids,
            'source_url': source_url,
            'content': content
        }

    def match_materials(
        self,
        material_cards: List[Dict],
        mb_materials: List[Dict]
    ) -> Tuple[List[Dict], Dict]:
        """
        Match material cards with ModelBank materials

        Args:
            material_cards: List of material card dicts
            mb_materials: List of ModelBank material dicts

        Returns:
            Tuple of (matches list, stats dict)
        """
        # Build ModelBank lookup dicts
        mb_by_sku = {}
        supplier_name = self.retailer_name

        # Filter to only materials for this retailer and build lookup
        for mat in mb_materials:
            if mat.get('supplier_name') == supplier_name:
                sku = mat.get('sku', '')
                if sku:
                    # Add multiple SKU variants for matching
                    for variant in [sku, sku.lower(), sku.lstrip('0'), sku.lstrip('0').lower()]:
                        if variant and variant not in mb_by_sku:
                            mb_by_sku[variant] = mat

        print(f"ModelBank has {len(mb_by_sku)} unique SKU variants for {supplier_name}")

        matches = []
        stats = {
            'total_cards': len(material_cards),
            'matched': 0,
            'unmatched': 0,
            'exact_item': 0,
            'name_extracted': 0,
            'filename_extracted': 0
        }

        for card in material_cards:
            match_info = None
            match_type = None

            # Try exact item number match
            for item in card.get('item_numbers', []):
                for variant in [item, item.lstrip('0')]:
                    if variant in mb_by_sku:
                        match_info = mb_by_sku[variant]
                        match_type = 'exact_item'
                        break
                if match_info:
                    break

            # Try extracted IDs from name or filename
            if not match_info:
                for extracted_id in card.get('extracted_ids', []):
                    for variant in [extracted_id, extracted_id.lstrip('0')]:
                        if variant in mb_by_sku:
                            match_info = mb_by_sku[variant]
                            # Determine if from name or filename
                            name_id_match = re.search(r'\((\d+)\)', card['name'])
                            if name_id_match and extracted_id == name_id_match.group(1):
                                match_type = 'name_extracted'
                            else:
                                match_type = 'filename_extracted'
                            break
                    if match_info:
                        break

            if match_info:
                matches.append({
                    'card_name': card['name'],
                    'card_filename': card['filename'],
                    'card_url': card['source_url'],
                    'item_numbers': card.get('item_numbers', []),
                    'mb_id': match_info['id'],
                    'mb_sku': match_info['sku'],
                    'mb_name': match_info['name'],
                    'mb_kind': match_info['kind'],
                    'match_type': match_type
                })
                stats['matched'] += 1
                stats[match_type] += 1
            else:
                stats['unmatched'] += 1

        stats['match_rate'] = (stats['matched'] / stats['total_cards'] * 100) if stats['total_cards'] > 0 else 0

        return matches, stats

    def generate_report(self, matches: List[Dict], stats: Dict, output_path: str):
        """
        Generate material matching report

        Args:
            matches: List of match dicts
            stats: Stats dict
            output_path: Path to output report file
        """
        import json

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Generate text report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Material Matching Report for {self.retailer_name}\n")
            f.write("=" * 80 + "\n\n")

            # Stats
            f.write("Statistics:\n")
            f.write(f"  Total material cards: {stats['total_cards']}\n")
            f.write(f"  Matched: {stats['matched']} ({stats['match_rate']:.1f}%)\n")
            f.write(f"  Unmatched: {stats['unmatched']}\n\n")

            f.write("Match types:\n")
            f.write(f"  Exact item match: {stats['exact_item']}\n")
            f.write(f"  Name extracted: {stats['name_extracted']}\n")
            f.write(f"  Filename extracted: {stats['filename_extracted']}\n\n")

            # Matches
            f.write("=" * 80 + "\n")
            f.write("Matched Materials:\n")
            f.write("=" * 80 + "\n\n")

            for match in matches:
                f.write(f"Card: {match['card_name']}\n")
                f.write(f"  File: {match['card_filename']}\n")
                if match['card_url']:
                    f.write(f"  URL: {match['card_url']}\n")
                if match['item_numbers']:
                    f.write(f"  Item: {', '.join(match['item_numbers'])}\n")
                f.write(f"  -> ModelBank: {match['mb_name']} (SKU: {match['mb_sku']}, Kind: {match['mb_kind']})\n")
                f.write(f"  Match Type: {match['match_type']}\n")
                f.write(f"  ModelBank ID: {match['mb_id']}\n")
                f.write("\n")

        print(f"\nMaterial matching report saved to: {output_path}")

        # Generate JSON file
        json_path = output_path.replace('.txt', '.json')
        json_data = {
            'retailer': self.retailer_name,
            'material_type': 'materials',
            'total_cards': stats['total_cards'],
            'total_matched': stats['matched'],
            'total_unmatched': stats['unmatched'],
            'match_rate': stats['match_rate'],
            'match_types': {
                'exact_item': stats['exact_item'],
                'name_extracted': stats['name_extracted'],
                'filename_extracted': stats['filename_extracted']
            },
            'matches': matches
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)

        print(f"Material matching JSON saved to: {json_path}")
