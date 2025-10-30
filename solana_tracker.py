from typing import Dict, List, Set
from datetime import datetime
from collections import defaultdict
from api_client import SolanaAPIClient

class WalletTracker:
    def __init__(self):
        self.api_client = SolanaAPIClient()
        self.tracked_wallets: Dict[str, Dict] = {}
        self.token_holders: Dict[str, Set[str]] = defaultdict(set)  # token -> set of wallet addresses
        self.flagged_tokens: List[Dict] = []  # tokens held by 2+ top traders

    def analyze_wallet(self, wallet_address: str) -> Dict:
        """Analyze a single wallet and get its SPL token holdings"""
        tokens = self.api_client.get_wallet_tokens(wallet_address)

        if not tokens:
            return {
                'wallet': wallet_address,
                'token_count': 0,
                'tokens': [],
                'status': 'inactive'
            }

        # Filter for SPL tokens with actual balance
        spl_tokens = []
        for t in tokens:
            mint = t.get('mint')
            amount = float(t.get('amount', 0))
            if mint and amount > 0:
                spl_tokens.append(t)

        wallet_data = {
            'wallet': wallet_address,
            'token_count': len(spl_tokens),
            'tokens': [],
            'status': 'active' if len(spl_tokens) > 0 else 'inactive',
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
            
            # Track which wallets hold which tokens
            self.token_holders[mint].add(wallet_address)

        return wallet_data

    def scan_top_traders(self, num_traders: int = 50) -> List[Dict]:
        """
        Main function: Scan top traders and find tokens held by 2+ traders
        """
        print("\n========== SCANNING TOP TRADERS ==========")
        
        # Reset tracking
        self.token_holders.clear()
        self.tracked_wallets.clear()
        self.flagged_tokens.clear()
        
        # Get top traders
        top_traders = self.api_client.get_top_traders(limit=num_traders)
        
        if not top_traders:
            print("⚠ No top traders found - check your SOLANA_TRACKER_API_KEY")
            return []
        
        print(f"\nAnalyzing {len(top_traders)} top traders...")
        
        # Analyze each top trader's wallet
        successful_scans = 0
        for idx, trader in enumerate(top_traders, 1):
            wallet_address = trader.get('wallet') or trader.get('address')
            
            if not wallet_address:
                continue
            
            pnl = trader.get('totalPnl', 0) or trader.get('pnl', 0)
            print(f"\n[{idx}/{len(top_traders)}] Analyzing wallet: {wallet_address[:8]}... (PnL: ${pnl:,.2f})")
            
            try:
                wallet_data = self.analyze_wallet(wallet_address)
                
                if wallet_data['status'] == 'active':
                    self.tracked_wallets[wallet_address] = wallet_data
                    successful_scans += 1
                    print(f"  ✓ Found {wallet_data['token_count']} SPL tokens")
                else:
                    print(f"  - No active tokens")
                    
            except Exception as e:
                print(f"  ✗ Error: {e}")
        
        print(f"\nSuccessfully scanned {successful_scans}/{len(top_traders)} wallets")
        
        # Find tokens held by 2+ traders
        print("\n========== FINDING TOKENS WITH 2+ TRADERS ==========")
        
        for token_mint, holders in self.token_holders.items():
            if len(holders) >= 2:
                # Get token info from one of the holders
                token_info = None
                for holder_address in holders:
                    wallet_data = self.tracked_wallets.get(holder_address)
                    if wallet_data:
                        for token in wallet_data['tokens']:
                            if token['mint'] == token_mint:
                                token_info = token
                                break
                    if token_info:
                        break
                
                flagged = {
                    'mint': token_mint,
                    'symbol': token_info.get('symbol', 'UNKNOWN') if token_info else 'UNKNOWN',
                    'name': token_info.get('name', 'Unknown') if token_info else 'Unknown',
                    'holder_count': len(holders),
                    'holders': list(holders)
                }
                
                self.flagged_tokens.append(flagged)
                print(f"✓ {flagged['symbol']} ({token_mint[:8]}...) - held by {len(holders)} top traders")
        
        # Sort by number of holders (descending)
        self.flagged_tokens.sort(key=lambda x: x['holder_count'], reverse=True)
        
        print(f"\n========== SCAN COMPLETE ==========")
        print(f"Found {len(self.flagged_tokens)} tokens held by 2+ top traders")
        
        return self.flagged_tokens

    def get_tracked_wallets(self) -> List[Dict]:
        """Get all tracked top trader wallets"""
        return list(self.tracked_wallets.values())

    def get_flagged_tokens(self) -> List[Dict]:
        """Get tokens held by 2+ top traders"""
        return self.flagged_tokens
