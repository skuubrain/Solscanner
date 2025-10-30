import os
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class SolanaAPIClient:
    def __init__(self):
        self.solana_tracker_api_key = os.getenv('SOLANA_TRACKER_API_KEY', '')
        self.helius_api_key = os.getenv('HELIUS_API_KEY', '')
        
        self.solana_tracker_url = "https://data.solanatracker.io"
        self.helius_url = "https://api.helius.xyz/v0"
        
        print(f"API Keys configured - Solana Tracker: {'✓' if self.solana_tracker_api_key else '✗'}, Helius: {'✓' if self.helius_api_key else '✗'}")

    def get_wallet_tokens(self, wallet_address: str) -> Optional[List[Dict]]:
        """Try Solana Tracker first, fallback to Helius if needed"""
        # Try Solana Tracker first
        tokens = self._get_wallet_tokens_solana_tracker(wallet_address)
        if tokens is not None:
            print(f"Got {len(tokens)} tokens from Solana Tracker for {wallet_address[:8]}...")
            return tokens
        
        # Fallback to Helius if Solana Tracker fails
        if self.helius_api_key:
            print(f"Falling back to Helius for {wallet_address[:8]}...")
            tokens = self._get_wallet_tokens_helius(wallet_address)
            if tokens is not None:
                print(f"Got {len(tokens)} tokens from Helius")
                return tokens
        
        print(f"Failed to get tokens for {wallet_address[:8]}...")
        return None

    def _get_wallet_tokens_solana_tracker(self, wallet_address: str) -> Optional[List[Dict]]:
        """Get wallet tokens from Solana Tracker API"""
        try:
            url = f"{self.solana_tracker_url}/wallet/{wallet_address}"
            headers = {'x-api-key': self.solana_tracker_api_key} if self.solana_tracker_api_key else {}
            
            print(f"Fetching wallet data from: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            
            print(f"Solana Tracker wallet API response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                # Handle different response formats
                if isinstance(data, dict):
                    tokens = data.get('tokens', []) or data.get('data', {}).get('tokens', [])
                else:
                    tokens = []
                return tokens
            else:
                print(f"Solana Tracker wallet API error: {response.status_code} - {response.text[:200]}")
                return None
        except Exception as e:
            print(f"Error fetching Solana Tracker wallet data: {e}")
            return None

    def _get_wallet_tokens_helius(self, wallet_address: str) -> Optional[List[Dict]]:
        """Get wallet tokens from Helius API (fallback)"""
        try:
            url = f"{self.helius_url}/addresses/{wallet_address}/balances"
            params = {'api-key': self.helius_api_key}
            response = requests.get(url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                return data.get('tokens', [])
            else:
                print(f"Helius API error: {response.status_code}")
            return None
        except Exception as e:
            print(f"Error fetching Helius data: {e}")
            return None

    def get_trending_tokens(self) -> List[Dict]:
        """Get trending tokens from Solana Tracker"""
        try:
            # Try the trending endpoint first
            url = f"{self.solana_tracker_url}/tokens/trending"
            headers = {'x-api-key': self.solana_tracker_api_key} if self.solana_tracker_api_key else {}
            
            print(f"Fetching trending tokens from: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            
            print(f"Trending API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    tokens = data.get('data', []) or data.get('tokens', [])
                elif isinstance(data, list):
                    tokens = data
                else:
                    tokens = []
                
                print(f"Found {len(tokens)} trending tokens")
                return tokens[:10]
            else:
                print(f"Trending API error: {response.status_code} - {response.text[:300]}")
                # Fallback to search endpoint
                return self._get_tokens_from_search()
                
        except Exception as e:
            print(f"Error fetching trending tokens: {e}")
            return self._get_tokens_from_search()

    def _get_tokens_from_search(self) -> List[Dict]:
        """Fallback method using search endpoint"""
        try:
            url = f"{self.solana_tracker_url}/tokens"
            headers = {'x-api-key': self.solana_tracker_api_key} if self.solana_tracker_api_key else {}
            params = {'limit': 20}
            
            print(f"Falling back to tokens list endpoint")
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    tokens = data.get('data', []) or data.get('tokens', [])
                elif isinstance(data, list):
                    tokens = data
                else:
                    tokens = []
                
                print(f"Found {len(tokens)} tokens from list endpoint")
                return sorted(tokens, key=lambda x: x.get('volume24h', 0) or x.get('liquidityUsd', 0) or 0, reverse=True)[:10]
            else:
                print(f"Tokens list API error: {response.status_code}")
            return []
        except Exception as e:
            print(f"Error in search fallback: {e}")
            return []

    def get_token_holders(self, token_address: str) -> List[Dict]:
        """Get token holders from Solana Tracker"""
        try:
            url = f"{self.solana_tracker_url}/tokens/{token_address}/holders"
            headers = {'x-api-key': self.solana_tracker_api_key} if self.solana_tracker_api_key else {}
            
            print(f"Fetching holders for token: {token_address}")
            response = requests.get(url, headers=headers, timeout=15)

            print(f"Holders API response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    holders = data.get('data', []) or data.get('holders', [])
                elif isinstance(data, list):
                    holders = data
                else:
                    holders = []
                
                print(f"Found {len(holders)} holders")
                return holders[:20]  # Return top 20 holders
            else:
                print(f"Token holders API error: {response.status_code} - {response.text[:200]}")
            return []
        except Exception as e:
            print(f"Error fetching token holders: {e}")
            return []
