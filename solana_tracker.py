from typing import Dict, List, Set
from datetime import datetime
from collections import defaultdict
from api_client import SolanaAPIClient

class WalletTracker:
    def __init__(self):
        self.api_client = SolanaAPIClient()
        self.tracked_wallets: Dict[str, Dict] = {}
        self.token_buyers: Dict[str, List[Dict]] = defaultdict(list)  # token -> list of {wallet, status, pnl}
        self.flagged_tokens: List[Dict] = []

    def analyze_wallet_trades(self, wallet_address: str) -> Dict:
        """Analyze wallet's trading history and positions"""
        pnl_data = self.api_client.get_wallet_pnl(wallet_address)

        if not pnl_data:
            return {
                'wallet': wallet_address,
                'status': 'no_data',
                'positions': []
            }

        # Extract positions (both open and closed)
        positions = []
        
        # Get open positions (still holding)
        open_positions = pnl_data.get('openPositions', []) or pnl_data.get('data', {}).get('openPositions', [])
        for pos in open_positions:
            token_address = pos.get('tokenAddress') or pos.get('mint') or pos.get('address')
            if not token_address:
                continue
                
            position_info = {
                'token_address': token_address,
                'symbol': pos.get('tokenSymbol', 'UNKNOWN'),
                'name': pos.get('tokenName', 'Unknown'),
                'status': 'holding',
                'balance': float(pos.get('balance', 0) or pos.get('currentBalance', 0) or 0),
                'unrealized_pnl': float(pos.get('unrealizedPnL', 0) or pos.get('pnl', 0) or 0),
                'unrealized_pnl_percent': float(pos.get('unrealizedPnLPercent', 0) or 0),
                'avg_buy_price': float(pos.get('avgBuyPrice', 0) or 0),
                'current_price': float(pos.get('currentPrice', 0) or 0)
            }
            positions.append(position_info)
            
            # Track that this wallet bought this token and is still holding
            self.token_buyers[token_address].append({
                'wallet': wallet_address,
                'status': 'holding',
                'pnl': position_info['unrealized_pnl'],
                'pnl_percent': position_info['unrealized_pnl_percent'],
                'balance': position_info['balance']
            })
        
        # Get closed positions (sold partially or completely)
        closed_positions = pnl_data.get('closedPositions', []) or pnl_data.get('data', {}).get('closedPositions', [])
        for pos in closed_positions:
            token_address = pos.get('tokenAddress') or pos.get('mint') or pos.get('address')
            if not token_address:
                continue
                
            position_info = {
                'token_address': token_address,
                'symbol': pos.get('tokenSymbol', 'UNKNOWN'),
                'name': pos.get('tokenName', 'Unknown'),
                'status': 'sold',
                'balance': 0,
                'realized_pnl': float(pos.get('realizedPnL', 0) or pos.get('pnl', 0) or 0),
                'realized_pnl_percent': float(pos.get('realizedPnLPercent', 0) or 0),
                'avg_buy_price': float(pos.get('avgBuyPrice', 0) or 0),
                'avg_sell_price': float(pos.get('avgSellPrice', 0) or 0)
            }
            positions.append(position_info)
            
            # Track that this wallet bought and sold this token
            self.token_buyers[token_address].append({
                'wallet': wallet_address,
                'status': 'sold',
                'pnl': position_info['realized_pnl'],
                'pnl_percent': position_info['realized_pnl_percent'],
                'balance': 0
            })

        wallet_data = {
            'wallet': wallet_address,
            'status': 'active' if len(positions) > 0 else 'inactive',
            'total_positions': len(positions),
            'open_positions': len([p for p in positions if p['status'] == 'holding']),
            'closed_positions': len([p for p in positions if p['status'] == 'sold']),
            'positions': positions,
            'last_updated': datetime.now().isoformat()
        }

        return wallet_data

    def scan_top_traders(self, num_traders: int = 50, min_buyers: int = 2) -> List[Dict]:
        """
        Scan top traders and find tokens that multiple traders bought
        Shows if they're still holding or have sold
        """
        print("\n" + "="*70)
        print("SCANNING TOP TRADERS - TRACKING BUYS & HOLDS")
        print("="*70)
        
        # Reset tracking
        self.token_buyers.clear()
        self.tracked_wallets.clear()
        self.flagged_tokens.clear()
        
        # Get top traders
        print(f"\nStep 1: Fetching top {num_traders} traders...")
        top_traders = self.api_client.get_top_traders(limit=num_traders)
        
        if not top_traders:
            print("❌ No top traders found - check SOLANA_TRACKER_API_KEY")
            return []
        
        print(f"✓ Found {len(top_traders)} top traders")
        
        # Analyze each trader's positions
        print(f"\nStep 2: Analyzing trading history of {len(top_traders)} traders...")
        print("-" * 70)
        
        successful_scans = 0
        
        for idx, trader in enumerate(top_traders, 1):
            wallet_address = trader.get('wallet') or trader.get('address')
            
            if not wallet_address:
                continue
            
            pnl = trader.get('totalPnl', 0) or 0
            
            if idx <= 10 or idx % 10 == 0:
                print(f"[{idx}/{len(top_traders)}] {wallet_address[:8]}... (PnL: ${pnl:,.2f})")
            
            try:
                wallet_data = self.analyze_wallet_trades(wallet_address)
                
                if wallet_data['status'] == 'active':
                    self.tracked_wallets[wallet_address] = wallet_data
                    successful_scans += 1
                    
                    if idx <= 10 or idx % 10 == 0:
                        print(f"             ✓ {wallet_data['open_positions']} holding, {wallet_data['closed_positions']} sold")
                    
            except Exception as e:
                if idx <= 10:
                    print(f"             ✗ Error: {e}")
        
        print("-" * 70)
        print(f"\n✓ Successfully analyzed {successful_scans} wallets")
        print(f"📊 Found {len(self.token_buyers)} unique tokens traded")
        
        # Find tokens bought by multiple traders
        print(f"\nStep 3: Finding tokens bought by {min_buyers}+ traders...")
        print("-" * 70)
        
        for token_address, buyers in self.token_buyers.items():
            if len(buyers) >= min_buyers:
                # Get token info
                token_symbol = buyers[0].get('wallet', 'UNKNOWN')
                token_name = 'Unknown'
                
                # Find symbol and name from positions
                for wallet_data in self.tracked_wallets.values():
                    for pos in wallet_data['positions']:
                        if pos['token_address'] == token_address:
                            token_symbol = pos['symbol']
                            token_name = pos['name']
                            break
                
                # Count how many are holding vs sold
                holders = [b for b in buyers if b['status'] == 'holding']
                sellers = [b for b in buyers if b['status'] == 'sold']
                
                # Calculate average PnL
                avg_pnl = sum(b['pnl'] for b in buyers) / len(buyers) if buyers else 0
                
                flagged = {
                    'token_address': token_address,
                    'symbol': token_symbol,
                    'name': token_name,
                    'total_buyers': len(buyers),
                    'still_holding': len(holders),
                    'sold_out': len(sellers),
                    'avg_pnl': avg_pnl,
                    'buyers': buyers
                }
                
                self.flagged_tokens.append(flagged)
                
                print(f"  ✓ {token_symbol:15} - {len(buyers)} buyers ({len(holders)} holding, {len(sellers)} sold)")
        
        # Sort by total buyers descending
        self.flagged_tokens.sort(key=lambda x: x['total_buyers'], reverse=True)
        
        print("-" * 70)
        print(f"\n{'='*70}")
        print(f"SCAN COMPLETE")
        print(f"{'='*70}")
        print(f"📊 Analyzed {successful_scans} top traders")
        print(f"🎯 Found {len(self.flagged_tokens)} tokens bought by {min_buyers}+ traders")
        print(f"{'='*70}\n")
        
        return self.flagged_tokens

    def get_tracked_wallets(self) -> List[Dict]:
        """Get all tracked wallets"""
        return list(self.tracked_wallets.values())

    def get_flagged_tokens(self) -> List[Dict]:
        """Get tokens bought by multiple traders"""
        return self.flagged_tokens
