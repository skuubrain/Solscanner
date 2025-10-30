import os
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class SolanaAPIClient:
    def __init__(self):
        self.solana_tracker_api_key = os.getenv('SOLANA_TRACKER_API_KEY', '')
        self.solana_tracker_url = "https://data.solanatracker.io"
        
        print(f"API Key - Solana Tracker: {'✓' if self.solana_tracker_api_key else '✗'}", flush=True)

    def get_trending_tokens(self, limit: int = 10) -> List[Dict]:
        """Get trending tokens sorted by volume"""
        try:
            url = f"{self.solana_tracker_url}/search"
            headers = {'x-api-key': self.solana_tracker_api_key} if self.solana_tracker_api_key else {}
            params = {
                'sortBy': 'volume_24h',
                'sortOrder': 'desc',
                'limit': limit,
                'minVolume_24h': 5000
            }
            
            print(f"Fetching trending tokens...", flush=True)
            response = requests.get(url, headers=headers, params=params, timeout=20)
            
            print(f"Trending tokens API response: {response.status_code}", flush=True)
            
            if response.status_code == 200:
                data = response.json()
                tokens = data.get('data', [])
                print(f"Found {len(tokens)} trending tokens", flush=True)
                return tokens
            else:
                print(f"Trending API error: {response.status_code} - {response.text[:300]}", flush=True)
            return []
                
        except Exception as e:
            print(f"Error fetching trending tokens: {e}", flush=True)
            return []

    def get_token_top_traders(self, token_address: str, limit: int = 20) -> List[Dict]:
        """Get top traders for a specific token"""
        try:
            url = f"{self.solana_tracker_url}/tokens/{token_address}/top-traders"
            headers = {'x-api-key': self.solana_tracker_api_key} if self.solana_tracker_api_key else {}
            
            response = requests.get(url, headers=headers, timeout=20)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    traders = data.get('data', []) or data.get('traders', [])
                elif isinstance(data, list):
                    traders = data
                else:
                    traders = []
                
                return traders[:limit]
            else:
                print(f"Top traders API error for {token_address[:8]}...: {response.status_code}", flush=True)
            return []
        except Exception as e:
            print(f"Error fetching top traders: {e}", flush=True)
            return []

    def get_wallet_pnl(self, wallet_address: str) -> Optional[Dict]:
        """Get wallet PnL data which includes all token positions"""
        try:
            url = f"{self.solana_tracker_url}/wallet/{wallet_address}/pnl"
            headers = {'x-api-key': self.solana_tracker_api_key} if self.solana_tracker_api_key else {}
            
            response = requests.get(url, headers=headers, timeout=20)

            if response.status_code == 200:
                data = response.json()
                return data
            return None
        except Exception as e:
            return None
