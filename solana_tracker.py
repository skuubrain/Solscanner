from typing import Dict, List, Set
from datetime import datetime
from api_client import SolanaAPIClient

class WalletTracker:
    def __init__(self):
        self.api_client = SolanaAPIClient()
        self.tracked_wallets: Dict[str, Dict] = {}
        self.flagged_tokens: Set[str] = set()

    def analyze_wallet(self, wallet_address: str) -> Dict:
        """Analyze a wallet and return its token holdings"""
        print(f"\n--- Analyzing wallet: {wallet_address[:8]}... ---")
        
        tokens = self.api_client.get_wallet_tokens(wallet_address)

        if not tokens:
            print(f"No tokens found for wallet {wallet_address[:8]}...")
            return {
                'wallet': wallet_address,
                'token_count': 0,
                'tokens': [],
                'status': 'inactive',
                'meets_criteria': False,
                'recent_transactions': 0
            }

        # Filter for SPL tokens with actual balance
        spl_tokens = [t for t in tokens if t.get('mint') or t.get('address')]
        spl_tokens = [t for t in spl_tokens if float(t.get('amount', 0) or t.get('balance', 0)) > 0]

        print(f"Found {len(spl_tokens)} SPL tokens with balance")

        wallet_data = {
            'wallet': wallet_address,
            'token_count': len(spl_tokens),
            'tokens': [],
            'status': 'active' if len(spl_tokens) > 0 else 'inactive',
            'meets_criteria': len(spl_tokens) >= 2,
            'last_updated': datetime.now().isoformat(),
            'recent_transactions': 0,
            'has_recent_activity': True
        }

        for token in spl_tokens:
            mint = token.get('mint') or token.get('address') or token.get('tokenAddress')
            amount = float(token.get('amount', 0) or token.get('balance', 0) or token.get('uiAmount', 0))
            decimals = int(token.get('decimals', 0) or 0)
            
            # Calculate actual amount
            if decimals > 0 and amount > 1:
                actual_amount = amount / (10 ** decimals)
            else:
                actual_amount = amount

            token_info = {
                'mint': mint,
                'amount': actual_amount,
                'raw_amount': amount,
                'symbol': token.get('symbol', 'UNKNOWN'),
                'name': token.get('name', 'Unknown Token')
            }
            wallet_data['tokens'].append(token_info)

            # Flag tokens from qualifying wallets
            if wallet_data['meets_criteria'] and mint:
                self.flagged_tokens.add(mint)

        print(f"Wallet meets criteria: {wallet_data['meets_criteria']} ({len(spl_tokens)} tokens)")
        return wallet_data

    def track_wallet(self, wallet_address: str) -> Dict:
        """Track a specific wallet"""
        wallet_data = self.analyze_wallet(wallet_address)

        if wallet_data['meets_criteria']:
            if wallet_address in self.tracked_wallets:
                previous_data = self.tracked_wallets[wallet_address]
                wallet_data['position_status'] = self._determine_position_status(
                    previous_data, wallet_data
                )
            else:
                wallet_data['position_status'] = 'holding'

            self.tracked_wallets[wallet_address] = wallet_data
            print(f"✓ Wallet tracked: {wallet_address[:8]}... with {wallet_data['token_count']} tokens")

        return wallet_data

    def _determine_position_status(self, previous: Dict, current: Dict) -> str:
        """Determine if wallet is holding, selling, or sold"""
        prev_tokens = {t['mint']: t['amount'] for t in previous.get('tokens', [])}
        curr_tokens = {t['mint']: t['amount'] for t in current.get('tokens', [])}

        if not curr_tokens:
            return 'sold_all'

        sold_count = 0
        partial_count = 0

        for mint, prev_amount in prev_tokens.items():
            curr_amount = curr_tokens.get(mint, 0)

            if curr_amount == 0:
                sold_count += 1
            elif curr_amount < prev_amount:
                partial_count += 1

        if sold_count == len(prev_tokens):
            return 'sold_all'
        elif sold_count > 0 or partial_count > 0:
            return 'sold_partially'
        else:
            return 'holding'

    def scan_trending_wallets(self) -> List[Dict]:
        """Scan trending tokens and track their holders"""
        print("\n========== STARTING WALLET SCAN ==========")
        
        trending_tokens = self.api_client.get_trending_tokens()
        print(f"\nGot {len(trending_tokens)} trending tokens to scan")
        
        if not trending_tokens:
            print("⚠ No trending tokens found - check your SOLANA_TRACKER_API_KEY")
            return []

        scanned_wallets = []
        scanned_addresses = set()

        # Scan top 5 trending tokens
        for idx, token in enumerate(trending_tokens[:5], 1):
            # Extract token address from different possible fields
            token_address = (
                token.get('address') or 
                token.get('mint') or 
                token.get('poolAddress') or 
                token.get('tokenAddress')
            )
            
            if not token_address:
                print(f"\n[{idx}/5] Skipping token - no address found")
                continue

            token_symbol = token.get('symbol', 'UNKNOWN')
            print(f"\n[{idx}/5] Scanning token: {token_symbol} ({token_address[:8]}...)")
            
            holders = self.api_client.get_token_holders(token_address)
            
            if not holders:
                print(f"  No holders found for {token_symbol}")
                continue
                
            print(f"  Analyzing top {min(len(holders), 10)} holders...")

            # Check top 10 holders
            for holder in holders[:10]:
                wallet_address = (
                    holder.get('owner') or 
                    holder.get('address') or 
                    holder.get('wallet')
                )
                
                if not wallet_address or wallet_address in scanned_addresses:
                    continue
                
                scanned_addresses.add(wallet_address)
                
                try:
                    wallet_data = self.track_wallet(wallet_address)
                    if wallet_data['meets_criteria']:
                        scanned_wallets.append(wallet_data)
                        print(f"    ✓ Added wallet: {wallet_address[:8]}... ({wallet_data['token_count']} tokens)")
                except Exception as e:
                    print(f"    ✗ Error analyzing wallet {wallet_address[:8]}...: {e}")

        print(f"\n========== SCAN COMPLETE ==========")
        print(f"Total qualifying wallets found: {len(scanned_wallets)}")
        print(f"Total wallets now tracked: {len(self.tracked_wallets)}")
        return scanned_wallets

    def get_tracked_wallets(self) -> List[Dict]:
        """Get all tracked wallets"""
        return list(self.tracked_wallets.values())

    def get_flagged_tokens(self) -> List[str]:
        """Get all flagged token addresses"""
        return list(self.flagged_tokens)
