from typing import Dict, List, Set
from datetime import datetime
from collections import defaultdict
from api_client import SolanaAPIClient

class WalletTracker:
    def __init__(self):
        self.api_client = SolanaAPIClient()
        self.tracked_wallets: Dict[str, Dict] = {}
        self.token_buyers: Dict[str, List[Dict]] = defaultdict(list)
        self.flagged_tokens: List[Dict] = []

    def analyze_wallet_pnl(self, wallet_address: str) -> Dict:
        """Analyze wallet using PnL data (includes all positions)"""
        pnl_data = self.api_client.get_wallet_pnl(wallet_address)

        if not pnl_data:
            return {
                'wallet': wallet_address,
                'status': 'no_data',
                'positions': []
            }

        positions = []
        
        # Get open positions (currently holding)
        open_positions = pnl_data.get('openPositions', []) or pnl_data.get('data', {}).get('openPositions', [])
        for pos in open_positions:
            token_address = pos.get('tokenAddress') or pos.get('mint')
            if token_address:
                positions.append({
                    'token_address': token_address,
                    'symbol': pos.get('tokenSymbol', 'UNKNOWN'),
                    'name': pos.get('tokenName', 'Unknown'),
                    'status': 'holding',
                    'balance': float(pos.get('balance', 0) or 0),
                    'pnl': float(pos.get('unrealizedPnL', 0) or 0)
                })

        wallet_data = {
            'wallet': wallet_address,
            'status': 'active' if len(positions) > 0 else 'inactive',
            'positions': positions,
            'last_updated': datetime.now().isoformat()
        }

        return wallet_data

    def scan_trending_tokens(self, num_tokens: int = 10, traders_per_token: int = 10, min_buyers: int = 2) -> List[Dict]:
        """
        Scan trending tokens, get their top traders, find common holdings
        """
        print("\n" + "="*70, flush=True)
        print("SCANNING TRENDING TOKENS FOR TOP TRADER HOLDINGS", flush=True)
        print("="*70, flush=True)
        
        self.token_buyers.clear()
        self.tracked_wallets.clear()
        self.flagged_tokens.clear()
        
        # Get trending tokens
        print(f"\nStep 1: Fetching top {num_tokens} trending tokens...", flush=True)
        trending_tokens = self.api_client.get_trending_tokens(limit=num_tokens)
        
        if not trending_tokens:
            print("❌ No trending tokens found", flush=True)
            return []
        
        print(f"✓ Found {len(trending_tokens)} trending tokens", flush=True)
        
        # For each trending token, get top traders
        print(f"\nStep 2: Getting top traders for each token...", flush=True)
        print("-" * 70, flush=True)
        
        all_traders = {}
        
        for idx, token in enumerate(trending_tokens, 1):
            token_address = token.get('mint') or token.get('address')
            token_symbol = token.get('symbol', 'UNKNOWN')
            
            if not token_address:
                continue
            
            print(f"\n[{idx}/{len(trending_tokens)}] {token_symbol} ({token_address[:8]}...)", flush=True)
            print(f"             Volume 24h: ${token.get('volume_24h', 0):,.0f}", flush=True)
            
            # Get top traders
            traders = self.api_client.get_token_top_traders(token_address, limit=traders_per_token)
            
            if not traders:
                print(f"             No top traders found", flush=True)
                continue
            
            print(f"             ✓ Found {len(traders)} top traders", flush=True)
            
            for trader in traders:
                wallet = trader.get('wallet') or trader.get('address')
                if wallet and wallet not in all_traders:
                    all_traders[wallet] = {
                        'source_token': token_symbol,
                        'pnl': trader.get('pnl', 0) or 0
                    }
        
        print("-" * 70, flush=True)
        print(f"\n✓ Collected {len(all_traders)} unique top traders", flush=True)
        
        # Analyze each trader's positions
        print(f"\nStep 3: Analyzing positions of top traders...", flush=True)
        print("-" * 70, flush=True)
        
        successful_scans = 0
        
        for idx, (wallet_address, trader_info) in enumerate(list(all_traders.items())[:50], 1):
            if idx % 10 == 0 or idx <= 5:
                print(f"[{idx}/50] {wallet_address[:8]}... (from {trader_info['source_token']})", flush=True)
            
            try:
                wallet_data = self.analyze_wallet_pnl(wallet_address)
                
                if wallet_data['status'] == 'active' and len(wallet_data['positions']) > 0:
                    self.tracked_wallets[wallet_address] = wallet_data
                    successful_scans += 1
                    
                    # Track which tokens this trader holds
                    for pos in wallet_data['positions']:
                        if pos['status'] == 'holding':
                            self.token_buyers[pos['token_address']].append({
                                'wallet': wallet_address,
                                'symbol': pos['symbol'],
                                'name': pos['name'],
                                'balance': pos['balance'],
                                'pnl': pos['pnl'],
                                'source_token': trader_info['source_token']
                            })
                    
                    if idx % 10 == 0 or idx <= 5:
                        print(f"             ✓ {len(wallet_data['positions'])} positions", flush=True)
                    
            except Exception as e:
                if idx <= 5:
                    print(f"             ✗ Error: {e}", flush=True)
        
        print("-" * 70, flush=True)
        print(f"\n✓ Successfully analyzed {successful_scans} wallets", flush=True)
        print(f"📊 Found {len(self.token_buyers)} unique tokens", flush=True)
        
        # Find tokens held by multiple traders
        print(f"\nStep 4: Finding tokens held by {min_buyers}+ traders...", flush=True)
        print("-" * 70, flush=True)
        
        for token_address, holders in self.token_buyers.items():
            if len(holders) >= min_buyers:
                token_symbol = holders[0]['symbol']
                token_name = holders[0]['name']
                
                flagged = {
                    'token_address': token_address,
                    'symbol': token_symbol,
                    'name': token_name,
                    'holder_count': len(holders),
                    'holders': holders,
                    'avg_pnl': sum(h['pnl'] for h in holders) / len(holders)
                }
                
                self.flagged_tokens.append(flagged)
                print(f"  ✓ {token_symbol:15} - held by {len(holders)} traders", flush=True)
        
        self.flagged_tokens.sort(key=lambda x: x['holder_count'], reverse=True)
        
        print("-" * 70, flush=True)
        print(f"\n{'='*70}", flush=True)
        print(f"SCAN COMPLETE", flush=True)
        print(f"{'='*70}", flush=True)
        print(f"📊 Analyzed {successful_scans} traders", flush=True)
        print(f"🎯 Found {len(self.flagged_tokens)} tokens held by {min_buyers}+ traders", flush=True)
        print(f"{'='*70}\n", flush=True)
        
        return self.flagged_tokens

    def get_tracked_wallets(self) -> List[Dict]:
        return list(self.tracked_wallets.values())

    def get_flagged_tokens(self) -> List[Dict]:
        return self.flagged_tokens
