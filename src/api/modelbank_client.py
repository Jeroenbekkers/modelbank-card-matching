#!/usr/bin/env python3
"""
Modelbank API Client
"""

import requests
from typing import Dict, List, Optional


class ModelbankClient:
    """Client for Modelbank API"""

    def __init__(self, api_url: str, auth_token: str, modelbank_token: Optional[str] = None):
        """
        Initialize Modelbank client

        Args:
            api_url: Base API URL (e.g., "https://3dmodelbank.com" for management API)
            auth_token: JWT authentication token (user auth)
            modelbank_token: Optional ModelBank token with supplier_id (for management API)
        """
        self.api_url = api_url.rstrip('/')
        self.auth_token = auth_token
        self.modelbank_token = modelbank_token or auth_token  # Fall back to auth_token if not provided
        self.headers = {
            "Content-Type": "application/json"
        }

        # Determine if using management API or search API
        self.use_management_api = '3dmodelbank.com' in api_url

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
        if self.use_management_api:
            return self._fetch_from_management_api(supplier_id, limit)
        else:
            return self._fetch_from_search_api(supplier_id, limit, offset)

    def _fetch_from_management_api(
        self,
        supplier_id: int,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch products from management API (3dmodelbank.com/manage/products)

        Args:
            supplier_id: Modelbank supplier ID (ignored, comes from modelbank_token)
            limit: Max products to fetch (None = all)

        Returns:
            List of product dicts
        """
        url = f"{self.api_url}/manage/products"

        all_products = []
        total_available = None
        page = 0
        per_page = 48  # Match web UI pagination

        while True:
            params = {
                "token": self.modelbank_token,
                "auth_token": self.auth_token,
                "page": page,
                "per_page": per_page,
                "status": "approved",
                "sort": "desc",
                "order": "created_at"
            }

            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                # Handle Elasticsearch response format
                hits_data = data.get('hits', {})
                hits = hits_data.get('hits', [])
                products = [hit['_source'] for hit in hits]

                # Get total count on first request
                if total_available is None:
                    total_available = hits_data.get('total', 0)
                    print(f"Total products available: {total_available}")

                if not products:
                    break

                all_products.extend(products)
                print(f"Fetched {len(all_products)}/{total_available} products...")

                # Check if we have all products or reached limit
                if limit and len(all_products) >= limit:
                    break

                if len(all_products) >= total_available:
                    break

                page += 1

            except requests.exceptions.RequestException as e:
                print(f"Error fetching products: {e}")
                break

        return all_products

    def _fetch_from_search_api(
        self,
        supplier_id: int,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        Fetch products from search API (mb.floorplanner.com/api/v1/products/search.json)

        Args:
            supplier_id: Modelbank supplier ID
            limit: Max products per request (None = all)
            offset: Starting offset for pagination

        Returns:
            List of product dicts
        """
        url = f"{self.api_url}/products/search.json"
        params = {
            "auth_token": self.auth_token,
            "supplier_id": supplier_id,
            "offset": offset
        }

        if limit:
            params["limit"] = limit

        all_products = []
        total_available = None

        while True:
            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()

                # Handle Elasticsearch response format (hits.hits[]._source)
                hits_data = data.get('hits', {})
                hits = hits_data.get('hits', [])
                products = [hit['_source'] for hit in hits]

                # Get total count on first request
                if total_available is None:
                    total_available = hits_data.get('total', 0)
                    print(f"Total products available: {total_available}")

                if not products:
                    break

                all_products.extend(products)
                print(f"Fetched {len(all_products)}/{total_available} products...")

                # Check if there are more pages
                if limit and len(all_products) >= limit:
                    break

                # Stop if we've fetched all available products
                if len(all_products) >= total_available:
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
        params = {
            "auth_token": self.auth_token
        }

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
