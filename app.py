from flask import Flask, render_template, jsonify, request
from solana_tracker import WalletTracker
import os
import sys

app = Flask(__name__)
tracker = WalletTracker()

sys.stdout.flush()

@app.route('/')
def index():
    print("==> Homepage accessed", flush=True)
    return render_template('index.html')

@app.route('/api/wallets', methods=['GET'])
def get_wallets():
    wallets = tracker.get_tracked_wallets()
    return jsonify({
        'wallets': wallets,
        'count': len(wallets)
    })

@app.route('/api/scan', methods=['POST'])
def scan_wallets():
    print("\n" + "="*70, flush=True)
    print("==> API: SCAN ENDPOINT CALLED", flush=True)
    print("="*70, flush=True)
    
    solana_key = os.getenv('SOLANA_TRACKER_API_KEY', '')
    helius_key = os.getenv('HELIUS_API_KEY', '')
    
    print(f"==> SOLANA_TRACKER_API_KEY: {'SET ✓' if solana_key else 'MISSING ✗'}", flush=True)
    print(f"==> HELIUS_API_KEY: {'SET ✓' if helius_key else 'MISSING ✗'}", flush=True)
    
    if not solana_key:
        return jsonify({'error': 'SOLANA_TRACKER_API_KEY not configured'}), 500
    
    if not helius_key:
        return jsonify({'error': 'HELIUS_API_KEY not configured'}), 500
    
    try:
        data = request.get_json() or {}
        num_tokens = data.get('num_tokens', 10)
        traders_per_token = data.get('traders_per_token', 10)
        min_buyers = data.get('min_buyers', 2)
        
        print(f"==> Scan params: {num_tokens} tokens, {traders_per_token} traders each, min {min_buyers} overlap", flush=True)
        
        flagged_tokens = tracker.scan_trending_tokens(
            num_tokens=num_tokens,
            traders_per_token=traders_per_token,
            min_buyers=min_buyers
        )
        
        print(f"==> Scan completed: {len(flagged_tokens)} flagged tokens", flush=True)
        
        return jsonify({
            'flagged_tokens': flagged_tokens,
            'count': len(flagged_tokens),
            'scanned_wallets': len(tracker.get_tracked_wallets())
        })
    except Exception as e:
        print(f"==> ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/tokens/flagged', methods=['GET'])
def get_flagged_tokens():
    tokens = tracker.get_flagged_tokens()
    return jsonify({
        'tokens': tokens,
        'count': len(tokens)
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    solana_key = os.getenv('SOLANA_TRACKER_API_KEY', '')
    helius_key = os.getenv('HELIUS_API_KEY', '')
    
    return jsonify({
        'status': 'healthy',
        'tracked_wallets': len(tracker.get_tracked_wallets()),
        'flagged_tokens': len(tracker.get_flagged_tokens()),
        'api_keys': {
            'solana_tracker': 'configured' if solana_key else 'missing',
            'helius': 'configured' if helius_key else 'missing'
        }
    })

if __name__ == '__main__':
    print("\n" + "="*70, flush=True)
    print("SOLANA TOP TRADER SCANNER", flush=True)
    print("="*70, flush=True)
    
    solana_key = os.getenv('SOLANA_TRACKER_API_KEY', '')
    helius_key = os.getenv('HELIUS_API_KEY', '')
    
    print(f"SOLANA_TRACKER_API_KEY: {'SET ✓' if solana_key else 'MISSING ✗'}", flush=True)
    print(f"HELIUS_API_KEY: {'SET ✓' if helius_key else 'MISSING ✗'}", flush=True)
    print("="*70 + "\n", flush=True)
    
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
