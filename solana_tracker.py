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

    def analyze_wallet(self, wallet_address: str) -> Dict:
        """Analyze a wallet's current token holdings"""
        tokens = self.api_client.get_wallet_tokens(wallet_address)

        if not tokens:
            return {
                'wallet': wallet_address,
                'status': 'no_data',
                'tokens': []
            }

        # Filter for SPL tokens with balance
        spl_tokens = []
        for t in tokens:
            mint = t.get('mint')
            amount = float(t.get('amount', 0))
            if mint and amount > 0:
                spl_tokens.append(t)

        wallet_data = {
            'wallet': wallet_address,
            'status': 'active' if len(spl_tokens) > 0 else 'inactive',
            'token_count': len(spl_tokens),
            'tokens': [],
            'last_updated': datetime.now().isoformat()
        }

        for token in spl_tokens:
            mint = token.get('mint')
            amount = float(token.get('amount', 0))
            decimals = int(token.get('decimals', 0))
            
            actual_amount = amount / (10 ** decimals) if decimals > 0 else amount

            token_info = {
                'mint': mint,
                'amount': actual_amount,
                'symbol': token.get('symbol', 'UNKNOWN'),
                'name': token.get('name', 'Unknown Token')
            }
            wallet_data['tokens'].append(token_info)

        return wallet_data

    def scan_trending_tokens(self, num_tokens: int = 10, traders_per_token: int = 10, min_buyers: int = 2) -> List[Dict]:
        """
        Scan trending tokens, get their top traders, and find common holdings
        """
        print("\n" + "="*70, flush=True)
        print("SCANNING TRENDING TOKENS FOR TOP TRADER HOLDINGS", flush=True)
        print("="*70, flush=True)
        
        # Reset tracking
        self.token_buyers.clear()
        self.tracked_wallets.clear()
        self.flagged_tokens.clear()
        
        # Get trending tokens
        print(f"\nStep 1: Fetching top {num_tokens} trending tokens...", flush=True)
        trending_tokens = self.api_client.get_trending_tokens(limit=num_tokens)
        
        if not trending_tokens:
            print("❌ No trending tokens found - check SOLANA_TRACKER_API_KEY", flush=True)
            return []
        
        print(f"✓ Found {len(trending_tokens)} trending tokens", flush=True)
        
        # For each trending token, get top traders
        print(f"\nStep 2: Getting top traders for each trending token...", flush=True)
        print("-" * 70, flush=True)
        
        all_traders = {}  # wallet -> {source_token, pnl, etc}
        
        for idx, token in enumerate(trending_tokens, 1):
            token_address = token.get('mint') or token.get('address')
            token_symbol = token.get('symbol', 'UNKNOWN')
            
            if not token_address:
                continue
            
            print(f"\n[{idx}/{len(trending_tokens)}] {token_symbol} ({token_address[:8]}...)", flush=True)
            print(f"             Volume 24h: ${token.get('volume_24h', 0):,.0f}", flush=True)
            
            # Get top traders for this token
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
                        'source_token_address': token_address,
                        'pnl': trader.get('pnl', 0) or trader.get('totalPnL', 0) or 0
                    }
        
        print("-" * 70, flush=True)
        print(f"\n✓ Collected {len(all_traders)} unique top traders", flush=True)
        
        # Analyze each trader's wallet
        print(f"\nStep 3: Analyzing holdings of {len(all_traders)} traders...", flush=True)
        print("-" * 70, flush=True)
        
        successful_scans = 0
        
        for idx, (wallet_address, trader_info) in enumerate(list(all_traders.items())[:50], 1):  # Limit to 50 to save time
            if idx % 10 == 0 or idx <= 5:
                print(f"[{idx}/50] {wallet_address[:8]}... (from {trader_info['source_token']})", flush=True)
            
            try:
                wallet_data = self.analyze_wallet(wallet_address)
                
                if wallet_data['status'] == 'active' and wallet_data['token_count'] > 0:
                    self.tracked_wallets[wallet_address] = wallet_data
                    successful_scans += 1
                    
                    # Track which tokens this trader holds
                    for token in wallet_data['tokens']:
                        self.token_buyers[token['mint']].append({
                            'wallet': wallet_address,
                            'balance': token['amount'],
                            'source_token': trader_info['source_token'],
                            'trader_pnl': trader_info['pnl']
                        })
                    
                    if idx % 10 == 0 or idx <= 5:
                        print(f"             ✓ {wallet_data['token_count']} tokens", flush=True)
                    
            except Exception as e:
                if idx <= 5:
                    print(f"             ✗ Error: {e}", flush=True)
        
        print("-" * 70, flush=True)
        print(f"\n✓ Successfully analyzed {successful_scans} wallets", flush=True)
        print(f"📊 Found {len(self.token_buyers)} unique tokens across all wallets", flush=True)
        
        # Find tokens held by multiple traders
        print(f"\nStep 4: Finding tokens held by {min_buyers}+ traders...", flush=True)
        print("-" * 70, flush=True)
        
        for token_address, holders in self.token_buyers.items():
            if len(holders) >= min_buyers:
                # Get token info
                token_symbol = holders[0].get('symbol', 'UNKNOWN')
                
                # Find symbol from wallet data
                for wallet_data in self.tracked_wallets.values():
                    for token in wallet_data['tokens']:
                        if token['mint'] == token_address:
                            token_symbol = token['symbol']
                            token_name = token['name']
                            break
                
                flagged = {
                    'token_address': token_address,
                    'symbol': token_symbol,
                    'name': token_name if 'token_name' in locals() else 'Unknown',
                    'holder_count': len(holders),
                    'holders': holders,
                    'avg_balance': sum(h['balance'] for h in holders) / len(holders)
                }
                
                self.flagged_tokens.append(flagged)
                print(f"  ✓ {token_symbol:15} - held by {len(holders)} top traders", flush=True)
        
        # Sort by holder count
        self.flagged_tokens.sort(key=lambda x: x['holder_count'], reverse=True)
        
        print("-" * 70, flush=True)
        print(f"\n{'='*70}", flush=True)
        print(f"SCAN COMPLETE", flush=True)
        print(f"{'='*70}", flush=True)
        print(f"📊 Analyzed {successful_scans} top trader wallets", flush=True)
        print(f"🎯 Found {len(self.flagged_tokens)} tokens held by {min_buyers}+ traders", flush=True)
        print(f"{'='*70}\n", flush=True)
        
        return self.flagged_tokens

    def get_tracked_wallets(self) -> List[Dict]:
        """Get all tracked wallets"""
        return list(self.tracked_wallets.values())

    def get_flagged_tokens(self) -> List[Dict]:
        """Get tokens held by multiple traders"""
        return self.flagged_tokens
