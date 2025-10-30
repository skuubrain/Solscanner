import os
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class SolanaAPIClient:
    def __init__(self):
        self.helius_api_key = os.getenv('HELIUS_API_KEY', '')
        self.alchemy_api_key = os.getenv('ALCHEMY_API_KEY', '')
        self.solana_tracker_api_key = os.getenv('SOLANA_TRACKER_API_KEY', '')
        
        self.helius_url = f"https://api.helius.xyz/v0"
        self.alchemy_url = f"https://solana-mainnet.g.alchemy.com/v2/{self.alchemy_api_key}"
        self.solana_tracker_url = "https://data.solanatracker.io"
    
    def get_wallet_tokens_helius(self, wallet_address: str) -> Optional[List[Dict]]:
        try:
            url = f"{self.helius_url}/addresses/{wallet_address}/balances"
            params = {'api-key': self.helius_api_key}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('tokens', [])
            return None
        except Exception as e:
            print(f"Error fetching Helius data: {e}")
            return None
    
    def get_wallet_transactions_alchemy(self, wallet_address: str, limit: int = 100) -> Optional[List[Dict]]:
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [wallet_address, {"limit": limit}]
            }
            response = requests.post(self.alchemy_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('result', [])
            return None
        except Exception as e:
            print(f"Error fetching Alchemy data: {e}")
            return None
    
    def get_token_info_solana_tracker(self, token_address: str) -> Optional[Dict]:
        try:
            url = f"{self.solana_tracker_url}/tokens/{token_address}"
            headers = {'x-api-key': self.solana_tracker_api_key}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching Solana Tracker data: {e}")
            return None
    
    def get_trending_tokens(self) -> List[Dict]:
        try:
            url = f"{self.solana_tracker_url}/search"
            headers = {'x-api-key': self.solana_tracker_api_key}
            params = {'query': 'SOL', 'limit': 20}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"Search API response status: {response.status_code}")
                if isinstance(data, dict):
                    if 'data' in data:
                        tokens = data['data']
                    elif 'tokens' in data:
                        tokens = data['tokens']
                    else:
                        tokens = []
                elif isinstance(data, list):
                    tokens = data
                else:
                    tokens = []
                
                print(f"Found {len(tokens)} tokens from search")
                return sorted(tokens, key=lambda x: x.get('liquidityUsd', 0) or 0, reverse=True)[:10]
            else:
                print(f"Search API error: {response.status_code} - {response.text[:200] if hasattr(response, 'text') else ''}")
            return []
        except Exception as e:
            print(f"Error fetching trending tokens: {e}")
            return []
    
    def get_token_holders(self, token_address: str) -> List[Dict]:
        try:
            url = f"{self.solana_tracker_url}/holders/{token_address}"
            headers = {'x-api-key': self.solana_tracker_api_key}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'data' in data:
                    return data['data']
                elif isinstance(data, list):
                    return data
                return []
            else:
                print(f"Token holders API error: {response.status_code}")
            return []
        except Exception as e:
            print(f"Error fetching token holders: {e}")
            return []
