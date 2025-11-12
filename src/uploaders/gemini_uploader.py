#!/usr/bin/env python3
"""
Gemini Uploader - Upload enriched cards to Gemini semantic retrieval
"""

import os
import re
import json
import time
from typing import Dict, List, Optional
from pathlib import Path


class GeminiUploader:
    """Upload Linda cards to Gemini semantic retrieval API"""

    def __init__(self, api_key: str, project_id: str, corpus_id: Optional[str] = None):
        """
        Initialize Gemini uploader

        Args:
            api_key: Gemini API key
            project_id: Google Cloud project ID
            corpus_id: Optional existing corpus ID, will create new if not provided
        """
        self.api_key = api_key
        self.project_id = project_id
        self.corpus_id = corpus_id

        # Import here to avoid dependency if not using Gemini
        try:
            import google.generativeai as genai
            self.genai = genai
            genai.configure(api_key=api_key)
        except ImportError:
            raise ImportError(
                "google-generativeai package required for Gemini upload. "
                "Install with: pip install google-generativeai"
            )

    def parse_linda_card_file(self, file_path: str) -> List[Dict]:
        """
        Parse a single .md file containing Linda AI cards

        Args:
            file_path: Path to markdown file

        Returns:
            List of card dictionaries with metadata and content
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
            return []

        # Regex to find all cards
        card_pattern = re.compile(
            r'<!--\s*CARD:([^\s]+)\s*-->(.*?)(?=<!--\s*CARD:|$)',
            re.DOTALL
        )

        # Regex to extract META JSON block
        meta_pattern = re.compile(
            r'<!--\s*META:\s*(\{[^}]+\})\s*-->',
            re.DOTALL
        )

        parsed_cards = []
        matches = card_pattern.findall(content)

        for card_name, raw_card_content in matches:
            # Extract and parse metadata
            meta_match = meta_pattern.search(raw_card_content)
            metadata = {}
            if meta_match:
                try:
                    meta_json_str = meta_match.group(1).strip()
                    metadata = json.loads(meta_json_str)
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse JSON metadata for card '{card_name}' in {file_path}: {e}")
                    continue

            # Extract clean text content (remove META block)
            clean_content = meta_pattern.sub('', raw_card_content).strip()

            if clean_content:
                parsed_cards.append({
                    "source_file": os.path.basename(file_path),
                    "card_name": card_name.strip(),
                    "metadata": metadata,
                    "content": clean_content
                })

        return parsed_cards

    def process_card_directory(
        self,
        directory: str,
        card_suffix: str = '_cards_v7.md'
    ) -> List[Dict]:
        """
        Process all card files in a directory

        Args:
            directory: Directory containing card files
            card_suffix: Card file suffix to match

        Returns:
            List of all parsed cards
        """
        from glob import glob

        file_pattern = os.path.join(directory, f'*{card_suffix}')
        file_list = glob(file_pattern)

        all_cards = []
        print(f"Found {len(file_list)} files to process...")

        for fpath in file_list:
            print(f"Processing: {os.path.basename(fpath)}")
            cards = self.parse_linda_card_file(fpath)
            all_cards.extend(cards)

        print(f"\nExtracted {len(all_cards)} total cards from {len(file_list)} files")
        return all_cards

    def create_corpus(self, display_name: str, description: str = "") -> str:
        """
        Create a new Gemini corpus

        Args:
            display_name: Corpus display name
            description: Optional corpus description

        Returns:
            Corpus ID
        """
        print(f"Creating Gemini corpus: {display_name}")

        try:
            corpus = self.genai.create_corpus(
                display_name=display_name,
                description=description or f"Product cards for {display_name}"
            )
            self.corpus_id = corpus.name
            print(f"Created corpus: {self.corpus_id}")
            return self.corpus_id
        except Exception as e:
            print(f"Error creating corpus: {e}")
            raise

    def upload_cards(
        self,
        cards: List[Dict],
        batch_size: int = 100,
        rate_limit_delay: float = 1.0
    ) -> Dict:
        """
        Upload cards to Gemini corpus

        Args:
            cards: List of parsed card dictionaries
            batch_size: Number of cards per batch
            rate_limit_delay: Delay in seconds between batches

        Returns:
            Dict with upload statistics
        """
        if not self.corpus_id:
            raise ValueError("corpus_id not set. Create or specify a corpus first.")

        print(f"Uploading {len(cards)} cards to corpus {self.corpus_id}")
        print(f"Batch size: {batch_size}, Rate limit delay: {rate_limit_delay}s")

        uploaded = 0
        failed = 0
        skipped = 0

        # Process in batches
        for i in range(0, len(cards), batch_size):
            batch = cards[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(cards) + batch_size - 1) // batch_size

            print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} cards)...")

            for card in batch:
                try:
                    # Build document metadata
                    doc_metadata = {
                        "source_file": card.get("source_file", "unknown"),
                        "card_name": card.get("card_name", "unknown"),
                        **card.get("metadata", {})
                    }

                    # Create document title
                    card_type = doc_metadata.get("card_type", "card")
                    card_role = doc_metadata.get("card_role", "unknown")
                    sku = doc_metadata.get("sku", "")
                    title = f"{card_type}:{card_role}"
                    if sku:
                        title += f":{sku}"

                    # Upload document
                    self.genai.create_document(
                        corpus_id=self.corpus_id,
                        display_name=title,
                        text=card["content"],
                        metadata=doc_metadata
                    )

                    uploaded += 1

                except Exception as e:
                    print(f"Failed to upload card {card.get('card_name')}: {e}")
                    failed += 1

            # Rate limiting between batches
            if i + batch_size < len(cards):
                time.sleep(rate_limit_delay)

        print(f"\n--- Upload Complete ---")
        print(f"Successfully uploaded: {uploaded}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")

        return {
            "uploaded": uploaded,
            "failed": failed,
            "skipped": skipped,
            "total": len(cards)
        }

    def delete_corpus(self):
        """Delete the corpus"""
        if not self.corpus_id:
            print("No corpus_id set")
            return

        print(f"Deleting corpus: {self.corpus_id}")
        try:
            self.genai.delete_corpus(self.corpus_id)
            print("Corpus deleted successfully")
            self.corpus_id = None
        except Exception as e:
            print(f"Error deleting corpus: {e}")

    def list_documents(self, limit: int = 10) -> List:
        """
        List documents in corpus

        Args:
            limit: Max documents to return

        Returns:
            List of document objects
        """
        if not self.corpus_id:
            print("No corpus_id set")
            return []

        print(f"Listing documents in corpus {self.corpus_id}...")
        try:
            docs = self.genai.list_documents(corpus_id=self.corpus_id, page_size=limit)
            return list(docs)
        except Exception as e:
            print(f"Error listing documents: {e}")
            return []

    def query(self, query_text: str, top_k: int = 5) -> List:
        """
        Query the corpus

        Args:
            query_text: Query string
            top_k: Number of results to return

        Returns:
            List of matching documents
        """
        if not self.corpus_id:
            print("No corpus_id set")
            return []

        print(f"Querying corpus: {query_text}")
        try:
            results = self.genai.query_corpus(
                corpus_id=self.corpus_id,
                query=query_text,
                results_count=top_k
            )
            return results
        except Exception as e:
            print(f"Error querying corpus: {e}")
            return []


def main():
    """Example usage"""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python gemini_uploader.py <api_key> <directory>")
        sys.exit(1)

    api_key = sys.argv[1]
    directory = sys.argv[2]

    # Initialize uploader
    uploader = GeminiUploader(
        api_key=api_key,
        project_id="modelbank-cards"  # You can customize this
    )

    # Create corpus
    corpus_id = uploader.create_corpus(
        display_name="Retailer Product Cards",
        description="Enriched product cards with Modelbank metadata"
    )

    # Process cards
    cards = uploader.process_card_directory(directory)

    # Upload
    if cards:
        results = uploader.upload_cards(cards)
        print(f"\nUpload summary: {json.dumps(results, indent=2)}")


if __name__ == "__main__":
    main()
