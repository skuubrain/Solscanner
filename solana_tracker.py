from typing import Dict, List, Set
from datetime import datetime
from api_client import SolanaAPIClient

class WalletTracker:
    def __init__(self):
        self.api_client = SolanaAPIClient()
        self.tracked_wallets: Dict[str, Dict] = {}
        self.flagged_tokens: Set[str] = set()
    
    def analyze_wallet(self, wallet_address: str) -> Dict:
        tokens = self.api_client.get_wallet_tokens_helius(wallet_address)
        transactions = self.api_client.get_wallet_transactions_alchemy(wallet_address, limit=50)
        
        if not tokens:
            return {
                'wallet': wallet_address,
                'token_count': 0,
                'tokens': [],
                'status': 'inactive',
                'meets_criteria': False,
                'recent_transactions': len(transactions) if transactions else 0
            }
        
        spl_tokens = [t for t in tokens if t.get('mint') and float(t.get('amount', 0)) > 0]
        
        wallet_data = {
            'wallet': wallet_address,
            'token_count': len(spl_tokens),
            'tokens': [],
            'status': 'active',
            'meets_criteria': len(spl_tokens) >= 2,
            'last_updated': datetime.now().isoformat(),
            'recent_transactions': len(transactions) if transactions else 0,
            'has_recent_activity': bool(transactions and len(transactions) > 0)
        }
        
        for token in spl_tokens:
            mint = token.get('mint')
            amount = float(token.get('amount', 0))
            decimals = int(token.get('decimals', 0))
            actual_amount = amount / (10 ** decimals) if decimals > 0 else amount
            
            token_info = {
                'mint': mint,
                'amount': actual_amount,
                'raw_amount': amount,
                'symbol': token.get('symbol', 'UNKNOWN'),
                'name': token.get('name', 'Unknown Token')
            }
            wallet_data['tokens'].append(token_info)
            
            if wallet_data['meets_criteria'] and mint:
                self.flagged_tokens.add(mint)
        
        return wallet_data
    
    def track_wallet(self, wallet_address: str) -> Dict:
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
        
        return wallet_data
    
    def _determine_position_status(self, previous: Dict, current: Dict) -> str:
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
        trending_tokens = self.api_client.get_trending_tokens()
        scanned_wallets = []
        
        print(f"Starting scan with {len(trending_tokens)} tokens")
        
        for token in trending_tokens[:5]:
            token_address = token.get('mint') or token.get('address') or token.get('poolAddress')
            if not token_address:
                print(f"Skipping token - no address found: {token.keys()}")
                continue
            
            print(f"Scanning holders for token: {token_address}")
            holders = self.api_client.get_token_holders(token_address)
            print(f"Found {len(holders)} holders")
            
            for holder in holders[:10]:
                wallet_address = holder.get('address') or holder.get('owner') or holder.get('wallet')
                if wallet_address and wallet_address not in [w['wallet'] for w in scanned_wallets]:
                    print(f"Analyzing wallet: {wallet_address}")
                    wallet_data = self.track_wallet(wallet_address)
                    if wallet_data['meets_criteria']:
                        scanned_wallets.append(wallet_data)
                        print(f"Added wallet with {wallet_data['token_count']} tokens")
        
        print(f"Scan complete. Found {len(scanned_wallets)} qualifying wallets")
        return scanned_wallets
    
    def get_tracked_wallets(self) -> List[Dict]:
        return list(self.tracked_wallets.values())
    
    def get_flagged_tokens(self) -> List[str]:
        return list(self.flagged_tokens)
