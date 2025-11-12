#!/usr/bin/env python3
"""
Modelbank API Client
"""

import requests
from typing import Dict, List, Optional


class ModelbankClient:
    """Client for Modelbank API"""

    def __init__(self, api_url: str, auth_token: str):
        """
        Initialize Modelbank client

        Args:
            api_url: Base API URL (e.g., "https://mb.floorplanner.com/api/v1")
            auth_token: JWT authentication token
        """
        self.api_url = api_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }

    def fetch_products_by_supplier(
        self,
        supplier_id: int,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        Fetch all products for a supplier

        Args:
            supplier_id: Modelbank supplier ID
            limit: Max products per request (None = all)
            offset: Starting offset for pagination

        Returns:
            List of product dicts
        """
        url = f"{self.api_url}/products/search.json"
        params = {
            "supplier_id": supplier_id,
            "offset": offset
        }

        if limit:
            params["limit"] = limit

        all_products = []
        batch_size = 300  # Modelbank typical batch size

        while True:
            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()

                products = data.get('products', [])
                if not products:
                    break

                all_products.extend(products)

                # Check if there are more pages
                if limit and len(all_products) >= limit:
                    break

                if len(products) < batch_size:
                    break

                # Move to next page
                params['offset'] += len(products)

            except requests.exceptions.RequestException as e:
                print(f"Error fetching products: {e}")
                break

        return all_products

    def get_product_by_model(self, model_id: str) -> Optional[Dict]:
        """
        Get single product by model ID

        Args:
            model_id: Model ID (e.g., "xxxx50618d1ed4f46b2fd19c67ec06b3bd00f31b_28")

        Returns:
            Product dict or None
        """
        # Note: Modelbank doesn't have direct model lookup, would need to implement
        # This is a placeholder for potential future API enhancement
        raise NotImplementedError("Modelbank doesn't support direct model lookup yet")

    def fetch_styles(self, branding_id: Optional[int] = None) -> List[Dict]:
        """
        Fetch styles from Floorplanner API

        Args:
            branding_id: Optional branding ID to filter retailer-specific styles

        Returns:
            List of style dicts
        """
        # Use Floorplanner API endpoint for styles
        url = "https://floorplanner.com/api/v2/styles.json"
        params = {}

        if branding_id:
            params["branding_id"] = branding_id

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('styles', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching styles: {e}")
            return []
