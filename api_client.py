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
        
        print(f"API Keys - Solana Tracker: {'✓' if self.solana_tracker_api_key else '✗'}, Helius: {'✓' if self.helius_api_key else '✗'}")

    def get_top_traders(self, limit: int = 50) -> List[Dict]:
        """Get top traders from Solana Tracker"""
        try:
            url = f"{self.solana_tracker_url}/top-traders"
            headers = {'x-api-key': self.solana_tracker_api_key} if self.solana_tracker_api_key else {}
            params = {'page': 1, 'sortBy': 'total', 'onlyRealized': False}
            
            print(f"Fetching top traders...")
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            print(f"Top traders API response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    traders = data.get('data', []) or data.get('traders', [])
                elif isinstance(data, list):
                    traders = data
                else:
                    traders = []
                
                print(f"Found {len(traders)} top traders")
                return traders[:limit]
            else:
                print(f"Top traders API error: {response.status_code} - {response.text[:300]}")
            return []
                
        except Exception as e:
            print(f"Error fetching top traders: {e}")
            return []

    def get_wallet_pnl(self, wallet_address: str) -> Optional[Dict]:
        """Get wallet PnL data including all positions (open and closed)"""
        try:
            url = f"{self.solana_tracker_url}/wallet/{wallet_address}/pnl"
            headers = {'x-api-key': self.solana_tracker_api_key} if self.solana_tracker_api_key else {}
            
            response = requests.get(url, headers=headers, timeout=20)

            if response.status_code == 200:
                data = response.json()
                return data
            else:
                print(f"Wallet PnL API error for {wallet_address[:8]}...: {response.status_code}")
            return None
        except Exception as e:
            print(f"Error fetching wallet PnL: {e}")
            return None

    def get_wallet_tokens(self, wallet_address: str) -> Optional[List[Dict]]:
        """Get current wallet token holdings using Helius (fallback)"""
        if not self.helius_api_key:
            return None
            
        try:
            url = f"{self.helius_url}/addresses/{wallet_address}/balances"
            params = {'api-key': self.helius_api_key}
            response = requests.get(url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                tokens = data.get('tokens', [])
                return tokens
            return None
        except Exception as e:
            print(f"Error fetching wallet tokens: {e}")
            return None
